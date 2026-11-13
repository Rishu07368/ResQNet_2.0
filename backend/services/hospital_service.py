"""Hospital suitability ranking and transactional bed reservation."""

from __future__ import annotations

import sqlite3
from typing import Any

from backend.database.repository import begin, commit, execute, record_event, rollback, row, rows
from backend.services.routing_service import _calculate, route
from backend.services.graph_service import snapshot


def hospitals(db: sqlite3.Connection) -> list[dict[str, Any]]:
    result = rows(db, "SELECT * FROM hospitals ORDER BY id")
    for hospital in result:
        hospital["available_beds"] = hospital["total_beds"] - hospital["occupied_beds"]
        hospital["specialties"] = hospital["specialties"].split(",")
    return result


def recommend(db: sqlite3.Connection, incident_id: int) -> dict[str, Any]:
    incident = row(db, "SELECT * FROM incidents WHERE id=?", (incident_id,))
    if incident is None:
        raise LookupError("Incident not found")
    allocation = row(db, """SELECT h.id AS hospital_id, h.name, h.location_id,
        ha.created_at, ha.beds_reserved
        FROM incidents i
        LEFT JOIN hospital_allocations ha ON ha.incident_id=i.id
        JOIN hospitals h ON h.id=COALESCE(ha.hospital_id, i.hospital_id)
        WHERE i.id=? AND (ha.id IS NOT NULL OR i.hospital_id IS NOT NULL)""", (incident_id,))
    if allocation is not None:
        return {
            "incident_id": incident_id,
            "recommendation": None,
            "alternatives": [],
            "rejected": [],
            "allocation": allocation,
        }
    ranked = []
    rejected = []
    locations, _, graph = snapshot(db)
    for hospital in hospitals(db):
        if not hospital["accepting"]:
            rejected.append({"hospital_id": hospital["id"], "reason": "not accepting"})
            continue
        if hospital["available_beds"] < 1:
            rejected.append({"hospital_id": hospital["id"], "reason": "no available beds"})
            continue
        specialty = incident["required_specialty"]
        if specialty and specialty not in hospital["specialties"]:
            rejected.append({"hospital_id": hospital["id"], "reason": f"missing {specialty} specialty"})
            continue
        result = _calculate(graph, locations, incident["location_id"], hospital["location_id"],
                            "dijkstra_heap", "time", False)
        if not result["reachable"]:
            rejected.append({"hospital_id": hospital["id"], "reason": "unreachable by open roads"})
            continue
        ranked.append({
            "hospital_id": hospital["id"], "name": hospital["name"],
            "location_id": hospital["location_id"], "available_beds": hospital["available_beds"],
            "eta_minutes": result["total_travel_minutes"], "route": result["path"],
        })
    ranked.sort(key=lambda value: (value["eta_minutes"], -value["available_beds"], value["hospital_id"]))
    return {"incident_id": incident_id, "recommendation": ranked[0] if ranked else None,
            "alternatives": ranked[1:], "rejected": rejected}


def allocate(db: sqlite3.Connection, incident_id: int, hospital_id: str) -> dict[str, Any]:
    if row(db, "SELECT id FROM incidents WHERE id=?", (incident_id,)) is None:
        raise LookupError("Incident not found")
    if _has_allocation(db, incident_id):
        raise ValueError("This incident already has a hospital allocation")
    options = recommend(db, incident_id)
    selected = next((item for item in ([options["recommendation"]] if options["recommendation"] else []) + options["alternatives"]
                     if item["hospital_id"] == hospital_id), None)
    if selected is None:
        raise ValueError("Hospital is not suitable, available, or reachable for this incident")
    begin(db)
    try:
        if _has_allocation(db, incident_id):
            raise ValueError("This incident already has a hospital allocation")
        changed = execute(db, "UPDATE hospitals SET occupied_beds=occupied_beds+1 WHERE id=? AND accepting=1 AND occupied_beds<total_beds",
                             (hospital_id,)).rowcount
        if changed != 1:
            raise ValueError("Hospital capacity changed; refresh recommendations")
        execute(db, "INSERT INTO hospital_allocations(incident_id,hospital_id) VALUES(?,?)", (incident_id, hospital_id))
        execute(db, "UPDATE incidents SET hospital_id=? WHERE id=?", (hospital_id, incident_id))
        record_event(db, "hospital", f"Incident #{incident_id} allocated to {selected['name']}")
        commit(db)
    except sqlite3.IntegrityError as error:
        rollback(db)
        if _has_allocation(db, incident_id):
            raise ValueError("This incident already has a hospital allocation") from error
        raise
    except Exception:
        rollback(db)
        raise
    return selected


def _has_allocation(db: sqlite3.Connection, incident_id: int) -> bool:
    return row(db, """SELECT i.id FROM incidents i
        LEFT JOIN hospital_allocations ha ON ha.incident_id=i.id
        WHERE i.id=? AND (i.hospital_id IS NOT NULL OR ha.id IS NOT NULL)""",
        (incident_id,)) is not None


def allocate_queue(db: sqlite3.Connection) -> list[dict[str, Any]]:
    pending = rows(db, """SELECT id,severity FROM incidents
        WHERE status NOT IN ('Resolved','Cancelled') AND hospital_id IS NULL
        AND NOT EXISTS (
            SELECT 1 FROM hospital_allocations ha WHERE ha.incident_id=incidents.id
        )
        ORDER BY CASE severity WHEN 'Critical' THEN 0 WHEN 'High' THEN 1
        WHEN 'Medium' THEN 2 ELSE 3 END, created_at, id""")
    outcomes = []
    for incident in pending:
        options = recommend(db, incident["id"])
        if options["recommendation"] is None:
            outcomes.append({"incident_id": incident["id"], "status": "unallocated",
                             "reason": "No suitable, available, reachable hospital"})
            continue
        selected = allocate(db, incident["id"], options["recommendation"]["hospital_id"])
        outcomes.append({"incident_id": incident["id"], "status": "allocated",
                         "hospital_id": selected["hospital_id"], "hospital_name": selected["name"]})
    return outcomes
