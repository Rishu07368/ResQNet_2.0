"""Routing, comparisons, trace playback data, and measured benchmarks."""

from __future__ import annotations

import random
import sqlite3
import time
from typing import Any

from backend.algorithms import astar, bellman_ford, dijkstra_array, dijkstra_heap
from backend.algorithms.common import Edge
from backend.database.repository import commit, json_value, persist_run, rows
from backend.services.graph_service import snapshot

ROUTERS = {"dijkstra_heap": dijkstra_heap, "dijkstra_array": dijkstra_array}


def _calculate(
    graph: dict[str, list[Edge]], locations: dict[str, dict[str, Any]],
    source: str, target: str, algorithm: str, metric: str, trace: bool,
) -> dict[str, Any]:
    if algorithm == "astar":
        coordinates = {key: (value["latitude"], value["longitude"]) for key, value in locations.items()}
        result = astar(graph, coordinates, source, target, metric, trace)
    elif algorithm in ROUTERS:
        result = ROUTERS[algorithm](graph, source, target, metric, trace)
    else:
        raise ValueError("algorithm must be dijkstra_heap, dijkstra_array, or astar")
    result["metric"] = metric
    result["reachable"] = bool(result["path"])
    result["segments"] = max(0, len(result["path"]) - 1)
    road_by_pair = {
        (source_id, edge.target): edge
        for source_id, edges in graph.items() for edge in edges
    }
    route_edges = [road_by_pair[(first, second)] for first, second in zip(result["path"], result["path"][1:])]
    result["total_distance_km"] = round(sum(item.distance for item in route_edges), 3) if result["path"] else None
    result["total_travel_minutes"] = round(sum(item.time for item in route_edges), 3) if result["path"] else None
    result["roads"] = [item.road_id for item in route_edges]
    return result


def _alternatives(
    graph: dict[str, list[Edge]], locations: dict[str, dict[str, Any]],
    result: dict[str, Any], source: str, target: str, algorithm: str, metric: str,
) -> list[dict[str, Any]]:
    alternatives: dict[tuple[str, ...], dict[str, Any]] = {}
    for road_id in result["roads"]:
        modified = {
            node: [edge for edge in edges if edge.road_id != road_id]
            for node, edges in graph.items()
        }
        candidate = _calculate(modified, locations, source, target, algorithm, metric, False)
        path_key = tuple(candidate["path"])
        if candidate["reachable"] and path_key != tuple(result["path"]):
            candidate["excluded_road_id"] = road_id
            alternatives[path_key] = candidate
    return sorted(alternatives.values(), key=lambda item: (item["cost"], item["path"]))[:3]


def route(
    db: sqlite3.Connection, source: str, target: str, algorithm: str, metric: str,
    trace: bool = False, include_alternatives: bool = False,
) -> dict[str, Any]:
    locations, _, graph = snapshot(db)
    if source not in locations or target not in locations:
        raise ValueError("Unknown source or destination location")
    result = _calculate(graph, locations, source, target, algorithm, metric, trace)
    if include_alternatives and result["reachable"]:
        result["alternative_routes"] = _alternatives(
            graph, locations, result, source, target, algorithm, metric,
        )
    return result


def _roads(db: sqlite3.Connection) -> list[dict[str, Any]]:
    return rows(db, "SELECT * FROM roads WHERE is_open=1")


def compare(db: sqlite3.Connection, source: str, target: str, metric: str) -> dict[str, Any]:
    locations, _, graph = snapshot(db)
    if source not in locations or target not in locations:
        raise ValueError("Unknown source or destination location")
    results = [
        _calculate(graph, locations, source, target, algorithm, metric, False)
        for algorithm in ("dijkstra_heap", "dijkstra_array", "astar")
    ]
    alternatives = _alternatives(graph, locations, results[0], source, target, "dijkstra_heap", metric) if results[0]["reachable"] else []
    return {"source": source, "destination": target, "metric": metric,
            "results": results, "alternative_routes": alternatives}


def benchmark(db: sqlite3.Connection, size: int, average_degree: int, repetitions: int, seed: int) -> dict[str, Any]:
    if not 25 <= size <= 500:
        raise ValueError("size must be between 25 and 500")
    if not 2 <= average_degree <= min(20, size - 1):
        raise ValueError("average_degree must be between 2 and min(20, size - 1)")
    if not 1 <= repetitions <= 7:
        raise ValueError("repetitions must be between 1 and 7")
    rng = random.Random(seed)
    nodes = [f"V{i:03d}" for i in range(size)]
    graph: dict[str, list[Edge]] = {node: [] for node in nodes}
    edge_pairs: set[tuple[int, int]] = set()
    for index in range(size - 1):
        edge_pairs.add((index, index + 1))
    target_edges = min(size * average_degree // 2, size * (size - 1) // 2)
    while len(edge_pairs) < target_edges:
        start = rng.randrange(size)
        end = rng.randrange(size)
        if start != end:
            edge_pairs.add((min(start, end), max(start, end)))
    undirected: list[dict[str, Any]] = []
    for start, end in sorted(edge_pairs):
        distance = rng.uniform(0.2, 5.0)
        minutes = distance / rng.uniform(20, 70) * 60
        capacity = rng.randint(50, 500)
        graph[nodes[start]].append(Edge(nodes[end], minutes, distance, capacity))
        graph[nodes[end]].append(Edge(nodes[start], minutes, distance, capacity))
        undirected.append({"source": nodes[start], "target": nodes[end], "distance": distance, "time": minutes})
    coordinates = {node: (37.0 + index // 10000 * 0.001, -122.0 + index * 0.0001) for index, node in enumerate(nodes)}
    source, target = nodes[0], nodes[-1]
    algorithms = {
        "dijkstra_heap": lambda: dijkstra_heap(graph, source, target, "time"),
        "dijkstra_array": lambda: dijkstra_array(graph, source, target, "time"),
        "astar": lambda: astar(graph, coordinates, source, target, "time"),
        "bellman_ford": lambda: bellman_ford(
            nodes, [{"source": u, "target": edge.target, "weight": edge.time}
                    for u, edges in graph.items() for edge in edges], source, target
        ),
    }
    summary: dict[str, Any] = {}
    for name, run in algorithms.items():
        run()
        samples: list[float] = []
        latest: dict[str, Any] | None = None
        for _ in range(repetitions):
            started = time.perf_counter()
            latest = run()
            samples.append((time.perf_counter() - started) * 1000)
        ordered = sorted(samples)
        median = ordered[len(ordered) // 2] if len(ordered) % 2 else (ordered[len(ordered)//2 - 1] + ordered[len(ordered)//2]) / 2
        stats = latest.get("stats", {}) if latest else {}
        summary[name] = {
            "median_ms": median, "minimum_ms": min(samples), "samples_ms": samples,
            "edge_checks": stats.get("edge_checks", latest.get("edge_checks", 0) if latest else 0),
            "relaxations": stats.get("relaxations", latest.get("relaxations", 0) if latest else 0),
            "iterations": stats.get("iterations", latest.get("iterations", 0) if latest else 0),
            "visited_nodes": len(latest.get("visited", [])) if latest else 0,
            "heap_operations": stats.get("heap_operations", 0),
        }
    result = {
        "size": size, "average_degree": round(2 * len(edge_pairs) / size, 2),
        "edge_count": 2 * len(edge_pairs), "seed": seed, "repetitions": repetitions,
        "metric": "time", "algorithms": summary,
        "note": "Measured in this Python runtime; timings vary by hardware and graph structure.",
    }
    persist_run(db, "benchmark_runs", ("result_json",), (json_value(result),))
    commit(db)
    return result


def benchmark_growth(
    db: sqlite3.Connection, average_degree: int, repetitions: int, seed: int,
) -> dict[str, Any]:
    sizes = (25, 50, 100, 250, 500)
    measurements = [
        benchmark(db, size, average_degree, repetitions, seed)
        for size in sizes
    ]
    return {
        "growth_results": measurements,
        "average_degree": average_degree,
        "repetitions": repetitions,
        "seed": seed,
        "note": "Each size uses a seeded graph shared by the compared algorithms; results are measured, not theoretical.",
    }


def visualize(db: sqlite3.Connection, body: dict[str, Any]) -> dict[str, Any]:
    algorithm = body.get("algorithm", "dijkstra_heap")
    result = route(db, body.get("source", ""), body.get("destination", ""), algorithm, body.get("metric", "time"), True)
    persist_run(db, "algorithm_runs", ("algorithm", "result_json"), (algorithm, json_value(result)))
    commit(db)
    return result
