"""Database-derived command dashboard and educational algorithm reference."""

from __future__ import annotations

import sqlite3
from typing import Any

from backend.database.repository import rows, scalar


def summary(db: sqlite3.Connection) -> dict[str, Any]:
    def count(query: str) -> int:
        return int(scalar(db, query))
    return {
        "locations": count("SELECT COUNT(*) FROM locations"),
        "road_connections": count("SELECT COUNT(*) FROM roads"),
        "open_roads": count("SELECT COUNT(*) FROM roads WHERE is_open=1"),
        "active_incidents": count("SELECT COUNT(*) FROM incidents WHERE status NOT IN ('Resolved','Cancelled')"),
        "available_ambulances": count("SELECT COUNT(*) FROM ambulances WHERE status='available'"),
        "dispatched_ambulances": count("SELECT COUNT(*) FROM ambulances WHERE status!='available'"),
        "hospitals": count("SELECT COUNT(*) FROM hospitals"),
        "available_beds": count("SELECT COALESCE(SUM(total_beds-occupied_beds),0) FROM hospitals WHERE accepting=1"),
        "active_road_blockages": count("SELECT COUNT(*) FROM roads WHERE is_open=0"),
        "shelters": count("SELECT COUNT(*) FROM shelters"),
    }


def overview(db: sqlite3.Connection) -> dict[str, Any]:
    return {
        **summary(db),
        "incidents_by_status": rows(db, "SELECT status,COUNT(*) AS count FROM incidents GROUP BY status ORDER BY status"),
        "activity": rows(db, "SELECT event_type,message,created_at FROM simulation_events ORDER BY id DESC LIMIT 12"),
        "dispatches": rows(db, """SELECT d.id,d.eta_minutes,d.created_at,i.incident_type,
            a.id AS ambulance_id FROM dispatch_records d
            JOIN incidents i ON i.id=d.incident_id JOIN ambulances a ON a.id=d.ambulance_id
            ORDER BY d.id DESC LIMIT 8"""),
    }


def theory() -> dict[str, Any]:
    return {
        "algorithms": [
            {"id": "dijkstra_heap", "name": "Dijkstra (binary heap)", "complexity": "O((V + E) log V)", "feature": "Fastest route and ambulance dispatch", "precondition": "Non-negative weights"},
            {"id": "dijkstra_array", "name": "Dijkstra (array)", "complexity": "O(V^2)", "feature": "Independent shortest-path comparison", "precondition": "Non-negative weights"},
            {"id": "astar", "name": "A* Search", "complexity": "Graph/heuristic dependent; exponential worst case generally", "feature": "Goal-directed route optimization", "precondition": "Admissible geographic lower bound"},
            {"id": "bfs", "name": "BFS", "complexity": "O(V + E)", "feature": "Reachability and connectivity", "precondition": "Unweighted traversal"},
            {"id": "dfs", "name": "DFS", "complexity": "O(V + E)", "feature": "Explore reachable network regions", "precondition": "Unweighted traversal"},
            {"id": "kruskal", "name": "Kruskal", "complexity": "O(E log E)", "feature": "Minimum-cost infrastructure forest", "precondition": "Underlying undirected graph"},
            {"id": "edmonds_karp", "name": "Edmonds-Karp", "complexity": "O(V E^2)", "feature": "Simulated evacuation capacity", "precondition": "Capacity graph; not travel-time weights"},
            {"id": "bellman_ford", "name": "Bellman-Ford", "complexity": "O(V E)", "feature": "Negative-weight and cycle educational sandbox", "precondition": "Never use negative physical road costs"},
        ],
        "benchmark_complexities": {
            "dijkstra_heap": "O((V+E) log V)", "dijkstra_array": "O(V^2)",
            "astar": "Graph/heuristic dependent; exponential worst case generally",
            "bfs": "O(V+E)", "dfs": "O(V+E)", "kruskal": "O(E log E)",
            "edmonds_karp": "O(VE^2)", "bellman_ford": "O(VE)",
        },
    }
