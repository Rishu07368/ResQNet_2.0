"""Road administration and connectivity/infrastructure planning."""

from __future__ import annotations

import sqlite3
import math
from typing import Any

from backend.algorithms import bfs, connected_components, dfs, kruskal
from backend.database.repository import commit, execute, record_event, row, rows
from backend.services.graph_service import response_network, snapshot


def set_road_status(db: sqlite3.Connection, road_id: int, is_open: bool) -> dict[str, Any]:
    road = row(db, "SELECT * FROM roads WHERE id=?", (road_id,))
    if road is None:
        raise LookupError("Road not found")
    execute(db, "UPDATE roads SET is_open=? WHERE id=?", (int(is_open), road_id))
    record_event(db, "road", f"Road {road_id} {'reopened' if is_open else 'closed'}")
    commit(db)
    return row(db, "SELECT * FROM roads WHERE id=?", (road_id,))


def update_road(db: sqlite3.Connection, road_id: int, body: dict[str, Any]) -> dict[str, Any]:
    if row(db, "SELECT id FROM roads WHERE id=?", (road_id,)) is None:
        raise LookupError("Road not found")
    fields = {
        "distance_km": body.get("distance_km"),
        "travel_minutes": body.get("travel_minutes"),
        "evacuation_capacity": body.get("evacuation_capacity"),
    }
    if all(value is None for value in fields.values()):
        raise ValueError("Provide at least one road attribute to update")
    for key in ("distance_km", "travel_minutes"):
        if fields[key] is not None and (isinstance(fields[key], bool) or not isinstance(fields[key], (int, float)) or not math.isfinite(fields[key]) or fields[key] <= 0):
            raise ValueError(f"{key} must be a positive number")
    if fields["evacuation_capacity"] is not None and (not isinstance(fields["evacuation_capacity"], int) or fields["evacuation_capacity"] < 0):
        raise ValueError("evacuation_capacity must be a non-negative integer")
    assignments = ", ".join(f"{key}=?" for key, value in fields.items() if value is not None)
    values = tuple(value for value in fields.values() if value is not None) + (road_id,)
    execute(db, f"UPDATE roads SET {assignments} WHERE id=?", values)
    record_event(db, "road", f"Road {road_id} attributes updated")
    commit(db)
    return row(db, "SELECT * FROM roads WHERE id=?", (road_id,))


def connectivity(db: sqlite3.Connection, source: str, algorithm: str) -> dict[str, Any]:
    locations, _, graph = snapshot(db)
    if source not in locations:
        raise ValueError("Unknown starting location")
    if algorithm == "bfs":
        result = bfs(graph, source)
    elif algorithm == "dfs":
        result = dfs(graph, source)
    else:
        raise ValueError("algorithm must be bfs or dfs")
    components = connected_components(graph)
    result.update({
        "algorithm": algorithm, "components": components,
        "isolated_locations": [component[0] for component in components if len(component) == 1],
        "component_count": len(components),
    })
    return result


def infrastructure_plan(db: sqlite3.Connection, weight: str = "distance") -> dict[str, Any]:
    locations, roads, _ = snapshot(db)
    return kruskal(
        locations,
        [{"source": road["source_id"], "target": road["target_id"],
          "distance": road["distance_km"], "cost": road["infrastructure_cost"]}
         for road in roads if road["is_open"]],
        weight,
    )


def network(db: sqlite3.Connection) -> dict[str, Any]:
    return response_network(db)


def road_list(db: sqlite3.Connection) -> list[dict[str, Any]]:
    return rows(db, """SELECT r.*, s.name AS source_name, t.name AS target_name
        FROM roads r JOIN locations s ON s.id=r.source_id
        JOIN locations t ON t.id=r.target_id ORDER BY r.id""")
