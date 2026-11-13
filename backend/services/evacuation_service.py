"""Capacity-constrained evacuation simulation using Edmonds-Karp."""

from __future__ import annotations

import sqlite3
from typing import Any

from backend.algorithms.edmonds_karp import edmonds_karp
from backend.database.repository import commit, json_value, persist_run, rows
from backend.services.graph_service import snapshot


def simulate(
    db: sqlite3.Connection, zones: list[dict[str, Any]], shelter_ids: list[str],
    shelter_capacities: dict[str, int] | None = None,
) -> dict[str, Any]:
    if not zones or not shelter_ids:
        raise ValueError("Select at least one evacuation zone and one shelter")
    locations, roads, _ = snapshot(db)
    shelters = {shelter["id"]: shelter for shelter in rows(db, "SELECT * FROM shelters")}
    if (any(not isinstance(item, str) or not item for item in shelter_ids)
            or len(set(shelter_ids)) != len(shelter_ids)
            or any(item not in shelters for item in shelter_ids)):
        raise ValueError("One or more selected shelters do not exist")
    shelter_capacities = shelter_capacities or {}
    if any(key not in shelter_ids for key in shelter_capacities):
        raise ValueError("Capacity overrides can only be supplied for selected shelters")
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0
           for value in shelter_capacities.values()):
        raise ValueError("Shelter capacity overrides must be non-negative integers")
    demand: dict[str, int] = {}
    for zone in zones:
        if not isinstance(zone, dict):
            raise ValueError("Each evacuation zone must be an object")
        location, population = zone.get("location_id"), zone.get("population")
        if (not isinstance(location, str) or location not in locations
                or not isinstance(population, int) or isinstance(population, bool) or population <= 0):
            raise ValueError("Each zone requires a known location and positive integer population")
        demand[location] = demand.get(location, 0) + population
    source, sink = "__EVAC_SOURCE__", "__EVAC_SINK__"
    nodes = list(locations) + [source, sink]
    edges = [{"source": road["source_id"], "target": road["target_id"], "capacity": road["evacuation_capacity"]}
             for road in roads if road["is_open"]]
    edges.extend({"source": source, "target": location, "capacity": population} for location, population in demand.items())
    for shelter_id in shelter_ids:
        shelter = shelters[shelter_id]
        edges.append({"source": shelter["location_id"], "target": sink,
                      "capacity": shelter_capacities.get(shelter_id, shelter["capacity"])})
    result = edmonds_karp(nodes, edges, source, sink)
    total = sum(demand.values())
    used = [edge for edge in result["used_capacities"]
            if not edge["source"].startswith("__") and not edge["target"].startswith("__")]
    result.update({
        "total_demand": total, "unserved_demand": total - result["maximum_flow"],
        "selected_shelters": shelter_ids, "used_road_capacities": used,
        "shelter_capacities": {shelter_id: shelter_capacities.get(shelter_id, shelters[shelter_id]["capacity"])
                               for shelter_id in shelter_ids},
        "disclaimer": "Simulated throughput for this configured period; not a real-world safety guarantee.",
    })
    persist_run(db, "evacuation_runs", ("result_json", "total_demand", "maximum_flow"),
                (json_value(result), total, result["maximum_flow"]))
    commit(db)
    return result
