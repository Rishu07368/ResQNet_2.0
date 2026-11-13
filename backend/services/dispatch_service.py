"""Ambulance dispatch selection and incident status transitions."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from backend.database.repository import begin, commit, execute, record_event, rollback, row, rows
from backend.services.graph_service import snapshot
from backend.services.routing_service import _calculate


def incident_list(db: sqlite3.Connection) -> list[dict[str, Any]]:
    return rows(db, """SELECT i.*, l.name AS location_name, a.id AS ambulance_label,
        h.name AS hospital_name FROM incidents i JOIN locations l ON l.id=i.location_id
        LEFT JOIN ambulances a ON a.id=i.assigned_ambulance
        LEFT JOIN hospitals h ON h.id=i.hospital_id ORDER BY i.created_at DESC, i.id DESC""")


def create_incident(db: sqlite3.Connection, body: dict[str, Any]) -> dict[str, Any]:
    location = row(db, "SELECT id FROM locations WHERE id=?", (body["location_id"],))
    if location is None:
        raise LookupError("Unknown incident location")
    cursor = execute(db,
        """INSERT INTO incidents(location_id,incident_type,severity,required_unit,required_specialty,description)
           VALUES(?,?,?,?,?,?)""",
        (body["location_id"], body["incident_type"], body["severity"], body.get("required_unit", "ambulance"),
         body.get("required_specialty"), body.get("description", "")),
    )
    record_event(db, "incident", f"{body['severity']} {body['incident_type']} reported at {body['location_id']}")
    commit(db)
    return row(db, "SELECT * FROM incidents WHERE id=?", (cursor.lastrowid,))


def _candidate_ambulances(db: sqlite3.Connection, incident_id: int) -> list[dict[str, Any]]:
    incident = row(db, "SELECT * FROM incidents WHERE id=?", (incident_id,))
    if incident is None:
        raise LookupError("Incident not found")
    if incident["status"] != "Pending":
        raise ValueError("Only pending incidents can be dispatched")
    if incident["required_unit"] != "ambulance":
        raise ValueError(f"No dispatchable {incident['required_unit']} fleet is configured in this simulation")
    locations, _, graph = snapshot(db)
    ambulances = rows(db, "SELECT * FROM ambulances WHERE status='available' AND assigned_incident IS NULL ORDER BY id")
    candidates = []
    for ambulance in ambulances:
        if incident["required_specialty"] and incident["required_specialty"] not in ambulance["capabilities"].split(","):
            continue
        result = _calculate(graph, locations, ambulance["location_id"], incident["location_id"],
                            "dijkstra_heap", "time", False)
        if result["reachable"]:
            candidates.append({"ambulance_id": ambulance["id"], "route": result["path"],
                               "eta_minutes": result["total_travel_minutes"], "distance_km": result["total_distance_km"]})
    candidates.sort(key=lambda item: (item["eta_minutes"], item["ambulance_id"]))
    if not candidates:
        raise ValueError("No suitable available ambulance has a reachable route")
    return candidates


def dispatch_options(db: sqlite3.Connection, incident_id: int) -> dict[str, Any]:
    candidates = _candidate_ambulances(db, incident_id)
    return {"incident_id": incident_id, "selected": candidates[0], "alternatives": candidates[1:]}


def dispatch(db: sqlite3.Connection, incident_id: int) -> dict[str, Any]:
    candidates = _candidate_ambulances(db, incident_id)
    selected = candidates[0]
    begin(db)
    try:
        incident_changed = execute(db,
            """UPDATE incidents SET status='Dispatched', assigned_ambulance=?
               WHERE id=? AND status='Pending' AND assigned_ambulance IS NULL""",
            (selected["ambulance_id"], incident_id),
        ).rowcount
        if incident_changed != 1:
            raise ValueError("Incident changed while dispatch was being confirmed; refresh and retry")
        changed = execute(db,
            """UPDATE ambulances SET status='dispatched', assigned_incident=?
               WHERE id=? AND status='available' AND assigned_incident IS NULL""",
            (incident_id, selected["ambulance_id"]),
        ).rowcount
        if changed != 1:
            raise ValueError("Ambulance became unavailable; retry dispatch")
        execute(db, "INSERT INTO dispatch_records(incident_id,ambulance_id,route_json,eta_minutes) VALUES(?,?,?,?)",
                   (incident_id, selected["ambulance_id"], json.dumps(selected["route"]), selected["eta_minutes"]))
        record_event(db, "dispatch", f"{selected['ambulance_id']} dispatched to incident #{incident_id}")
        commit(db)
    except Exception:
        rollback(db)
        raise
    return {"incident_id": incident_id, "selected": selected, "alternatives": candidates[1:]}


def update_status(db: sqlite3.Connection, incident_id: int, status: str) -> dict[str, Any]:
    incident = row(db, "SELECT * FROM incidents WHERE id=?", (incident_id,))
    if incident is None:
        raise LookupError("Incident not found")
    transitions = {
        "Pending": {"Cancelled"}, "Dispatched": {"On Scene", "Cancelled"},
        "On Scene": {"Transporting", "Resolved", "Cancelled"},
        "Transporting": {"Resolved", "Cancelled"},
    }
    if status not in transitions.get(incident["status"], set()):
        raise ValueError(f"Invalid incident transition: {incident['status']} to {status}")
    begin(db)
    try:
        changed = execute(db, "UPDATE incidents SET status=? WHERE id=? AND status=?",
                          (status, incident_id, incident["status"])).rowcount
        if changed != 1:
            raise ValueError("Incident changed while the status update was being applied; refresh and retry")
        if status in ("Resolved", "Cancelled") and incident["assigned_ambulance"]:
            execute(db, "UPDATE ambulances SET status='available', assigned_incident=NULL WHERE id=?",
                       (incident["assigned_ambulance"],))
        elif status in ("On Scene", "Transporting") and incident["assigned_ambulance"]:
            ambulance_status = "on_scene" if status == "On Scene" else "transporting"
            destination = incident["location_id"]
            if status == "Transporting" and incident["hospital_id"]:
                hospital = row(db, "SELECT location_id FROM hospitals WHERE id=?", (incident["hospital_id"],))
                if hospital:
                    destination = hospital["location_id"]
            updated = execute(db,
                "UPDATE ambulances SET status=?,location_id=? WHERE id=? AND assigned_incident=?",
                (ambulance_status, destination, incident["assigned_ambulance"], incident_id),
            ).rowcount
            if updated != 1:
                raise ValueError("Assigned ambulance state changed; refresh and retry")
        record_event(db, "incident", f"Incident #{incident_id} status changed to {status}")
        commit(db)
    except Exception:
        rollback(db)
        raise
    return row(db, "SELECT * FROM incidents WHERE id=?", (incident_id,))
