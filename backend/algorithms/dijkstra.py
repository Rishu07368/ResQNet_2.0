"""Binary-heap and array-selection Dijkstra implementations."""

from __future__ import annotations

import heapq
import time
from typing import Any

from .common import Graph, result_path


def _validate(graph: Graph, metric: str) -> None:
    if metric not in ("time", "distance"):
        raise ValueError("metric must be 'time' or 'distance'")
    if any(edge.weight(metric) < 0 for edges in graph.values() for edge in edges):
        raise ValueError("Dijkstra requires non-negative edge weights")


def dijkstra_heap(
    graph: Graph, source: str, target: str, metric: str = "time", trace: bool = False
) -> dict[str, Any]:
    _validate(graph, metric)
    if source not in graph or target not in graph:
        raise ValueError("source and destination must exist in the graph")
    started = time.perf_counter()
    distances = {node: float("inf") for node in graph}
    previous: dict[str, str | None] = {node: None for node in graph}
    distances[source] = 0.0
    queue: list[tuple[float, str]] = [(0.0, source)]
    visited: list[str] = []
    events: list[dict[str, Any]] = []
    edge_checks = relaxations = iterations = heap_ops = 0
    while queue:
        distance, node = heapq.heappop(queue)
        heap_ops += 1
        if distance != distances[node]:
            continue
        iterations += 1
        visited.append(node)
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
                heapq.heappush(queue, (candidate, edge.target))
                heap_ops += 1
                if trace:
                    events.append({
                        "type": "distance_updated", "node": edge.target,
                        "from": node, "distance": candidate,
                    })
    stats = {
        "algorithm": "dijkstra_heap", "iterations": iterations,
        "edge_checks": edge_checks, "relaxations": relaxations,
        "heap_operations": heap_ops,
        "execution_ms": (time.perf_counter() - started) * 1000,
        "_visited_order": visited,
    }
    result = result_path(source, target, distances, previous, stats)
    if trace:
        result["trace"] = events
    return result


def dijkstra_array(
    graph: Graph, source: str, target: str, metric: str = "time", trace: bool = False
) -> dict[str, Any]:
    _validate(graph, metric)
    if source not in graph or target not in graph:
        raise ValueError("source and destination must exist in the graph")
    started = time.perf_counter()
    distances = {node: float("inf") for node in graph}
    previous: dict[str, str | None] = {node: None for node in graph}
    unvisited = set(graph)
    distances[source] = 0.0
    visited: list[str] = []
    events: list[dict[str, Any]] = []
    edge_checks = relaxations = iterations = 0
    while unvisited:
        node = min(unvisited, key=lambda item: (distances[item], item))
        if distances[node] == float("inf"):
            break
        unvisited.remove(node)
        iterations += 1
        visited.append(node)
        if trace:
            events.append({"type": "node_visited", "node": node, "distance": distances[node]})
        if node == target:
            break
        for edge in graph[node]:
            edge_checks += 1
            candidate = distances[node] + edge.weight(metric)
            if candidate < distances[edge.target]:
                distances[edge.target] = candidate
                previous[edge.target] = node
                relaxations += 1
                if trace:
                    events.append({
                        "type": "distance_updated", "node": edge.target,
                        "from": node, "distance": candidate,
                    })
    stats = {
        "algorithm": "dijkstra_array", "iterations": iterations,
        "edge_checks": edge_checks, "relaxations": relaxations,
        "heap_operations": 0,
        "execution_ms": (time.perf_counter() - started) * 1000,
        "_visited_order": visited,
    }
    result = result_path(source, target, distances, previous, stats)
    if trace:
        result["trace"] = events
    return result
