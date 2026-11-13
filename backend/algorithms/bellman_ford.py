"""Bellman-Ford for the isolated educational weighted-graph sandbox."""

from __future__ import annotations

import time
from typing import Any, Iterable


def bellman_ford(
    nodes: Iterable[str], edges: Iterable[dict[str, Any]], source: str,
    target: str | None = None, trace: bool = False,
) -> dict[str, Any]:
    node_list = list(dict.fromkeys(nodes))
    edge_list = list(edges)
    if source not in node_list or (target is not None and target not in node_list):
        raise ValueError("source and destination must exist in the graph")
    for edge in edge_list:
        if edge["source"] not in node_list or edge["target"] not in node_list:
            raise ValueError("edge references a node outside the graph")
    started = time.perf_counter()
    distance = {node: float("inf") for node in node_list}
    previous: dict[str, str | None] = {node: None for node in node_list}
    distance[source] = 0.0
    iterations = edge_checks = relaxations = 0
    events: list[dict[str, Any]] = [{"type": "node_discovered", "node": source}] if trace else []
    for _ in range(max(0, len(node_list) - 1)):
        changed = False
        iterations += 1
        for edge in edge_list:
            edge_checks += 1
            start, end, weight = edge["source"], edge["target"], float(edge["weight"])
            if trace:
                events.append({"type": "edge_inspected", "from": start, "node": end, "weight": weight})
            if distance[start] != float("inf") and distance[start] + weight < distance[end]:
                distance[end] = distance[start] + weight
                previous[end] = start
                relaxations += 1
                changed = True
                if trace:
                    events.append({"type": "distance_updated", "node": end, "from": start, "distance": distance[end]})
        if not changed:
            break
    cycle_vertex: str | None = None
    for edge in edge_list:
        edge_checks += 1
        start, end, weight = edge["source"], edge["target"], float(edge["weight"])
        if trace:
            events.append({"type": "edge_inspected", "from": start, "node": end, "weight": weight})
        if distance[start] != float("inf") and distance[start] + weight < distance[end]:
            previous[end] = start
            cycle_vertex = end
            break
    cycle: list[str] = []
    if cycle_vertex is not None:
        cursor = cycle_vertex
        for _ in node_list:
            predecessor = previous[cursor]
            if predecessor is None:
                break
            cursor = predecessor
        cycle = [cursor]
        next_node = previous[cursor]
        while next_node is not None and next_node != cursor and len(cycle) <= len(node_list):
            cycle.append(next_node)
            next_node = previous[next_node]
        if next_node == cursor:
            cycle.append(cursor)
            cycle.reverse()
        if trace:
            events.append({"type": "negative_cycle_detected", "path": cycle})
    reachable = set()
    if cycle_vertex is not None:
        reachable.add(cycle_vertex)
        changed = True
        while changed:
            changed = False
            for edge in edge_list:
                if edge["source"] in reachable and edge["target"] not in reachable:
                    reachable.add(edge["target"])
                    changed = True
    for node in reachable:
        distance[node] = float("-inf")
    path: list[str] = []
    if target is not None and distance[target] not in (float("inf"), float("-inf")):
        cursor: str | None = target
        while cursor is not None:
            path.append(cursor)
            if cursor == source:
                path.reverse()
                break
            cursor = previous[cursor]
        else:
            path = []
    result = {
        "source": source,
        "destination": target,
        "distances": {node: (None if value == float("inf") else "-Infinity" if value == float("-inf") else value) for node, value in distance.items()},
        "path": path,
        "negative_cycle": cycle,
        "has_negative_cycle": cycle_vertex is not None,
        "iterations": iterations,
        "edge_checks": edge_checks,
        "relaxations": relaxations,
        "execution_ms": (time.perf_counter() - started) * 1000,
    }
    if trace:
        result["trace"] = events
    return result
