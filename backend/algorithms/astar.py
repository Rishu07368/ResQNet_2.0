"""A* search with an admissible great-circle distance heuristic."""

from __future__ import annotations

import heapq
import math
import time
from typing import Any, Mapping

from .common import Graph, result_path


def haversine_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, first)
    lat2, lon2 = map(math.radians, second)
    delta_lat, delta_lon = lat2 - lat1, lon2 - lon1
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(value))


def astar(
    graph: Graph,
    coordinates: Mapping[str, tuple[float, float]],
    source: str,
    target: str,
    metric: str = "time",
    trace: bool = False,
) -> dict[str, Any]:
    if metric not in ("time", "distance"):
        raise ValueError("metric must be 'time' or 'distance'")
    if source not in graph or target not in graph:
        raise ValueError("source and destination must exist in the graph")
    if any(edge.weight(metric) < 0 for edges in graph.values() for edge in edges):
        raise ValueError("A* requires non-negative edge weights")
    if any(node not in coordinates for node in graph):
        raise ValueError("coordinates are required for every graph location")
    straight_line_ratios: list[float] = []
    maximum_speed = 0.0
    for source_node, edges in graph.items():
        for edge in edges:
            direct_edge = haversine_km(coordinates[source_node], coordinates[edge.target])
            if direct_edge > 0:
                straight_line_ratios.append(edge.distance / direct_edge)
                if edge.time == 0:
                    maximum_speed = math.inf
                elif edge.time > 0:
                    maximum_speed = max(maximum_speed, direct_edge / (edge.time / 60))
    minimum_distance_ratio = min(straight_line_ratios, default=0.0)

    def heuristic(node: str) -> float:
        direct = haversine_km(coordinates[node], coordinates[target])
        return direct * minimum_distance_ratio if metric == "distance" else (direct / maximum_speed * 60 if maximum_speed else 0.0)

    started = time.perf_counter()
    distances = {node: float("inf") for node in graph}
    previous: dict[str, str | None] = {node: None for node in graph}
    distances[source] = 0.0
    queue: list[tuple[float, float, str]] = [(heuristic(source), 0.0, source)]
    visited: list[str] = []
    events: list[dict[str, Any]] = []
    closed: set[str] = set()
    edge_checks = relaxations = iterations = heap_ops = 0
    while queue:
        _, distance, node = heapq.heappop(queue)
        heap_ops += 1
        if distance != distances[node] or node in closed:
            continue
        closed.add(node)
        visited.append(node)
        iterations += 1
        if trace:
            events.append({"type": "node_visited", "node": node, "distance": distance})
        if node == target:
            break
        for edge in graph[node]:
            edge_checks += 1
            candidate = distance + edge.weight(metric)
            if candidate < distances[edge.target]:
                distances[edge.target] = candidate
                previous[edge.target] = node
                relaxations += 1
                heapq.heappush(queue, (candidate + heuristic(edge.target), candidate, edge.target))
                heap_ops += 1
                if trace:
                    events.append({
                        "type": "distance_updated", "node": edge.target,
                        "from": node, "distance": candidate,
                    })
    stats = {
        "algorithm": "astar", "iterations": iterations,
        "edge_checks": edge_checks, "relaxations": relaxations,
        "heap_operations": heap_ops,
        "execution_ms": (time.perf_counter() - started) * 1000,
        "_visited_order": visited,
    }
    result = result_path(source, target, distances, previous, stats)
    if trace:
        result["trace"] = events
    return result
