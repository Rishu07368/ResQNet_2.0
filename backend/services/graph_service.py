"""Load consistent graph snapshots from SQLite."""

from __future__ import annotations

import sqlite3
from typing import Any

from backend.algorithms.common import Edge
from backend.database.repository import rows


def snapshot(db: sqlite3.Connection) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, list[Edge]]]:
    locations = rows(db, "SELECT * FROM locations ORDER BY id")
    roads = rows(db, "SELECT * FROM roads ORDER BY id")
    location_map = {item["id"]: item for item in locations}
    graph: dict[str, list[Edge]] = {item["id"]: [] for item in locations}
    for road in roads:
        if road["is_open"]:
            graph[road["source_id"]].append(Edge(
                target=road["target_id"], time=road["travel_minutes"],
                distance=road["distance_km"], capacity=road["evacuation_capacity"],
                road_id=road["id"],
            ))
    return location_map, roads, graph


def response_network(db: sqlite3.Connection) -> dict[str, Any]:
    locations, roads, _ = snapshot(db)
    ambulances = rows(db, "SELECT id,location_id,status,capabilities FROM ambulances ORDER BY id")
    hospitals = rows(db, "SELECT id,name,location_id,total_beds,occupied_beds,specialties,accepting FROM hospitals ORDER BY id")
    shelters = rows(db, "SELECT id,name,location_id,capacity FROM shelters ORDER BY id")
    for hospital in hospitals:
        hospital["available_beds"] = hospital["total_beds"] - hospital["occupied_beds"]
        hospital["specialties"] = hospital["specialties"].split(",")
    for ambulance in ambulances:
        ambulance["capabilities"] = ambulance["capabilities"].split(",")
    return {
        "locations": list(locations.values()),
        "roads": roads,
        "ambulances": ambulances,
        "hospitals": hospitals,
        "shelters": shelters,
        "directed_road_count": len(roads),
        "open_road_count": sum(1 for road in roads if road["is_open"]),
    }
