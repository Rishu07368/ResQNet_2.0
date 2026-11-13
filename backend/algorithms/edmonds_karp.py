"""Edmonds-Karp maximum flow using a residual capacity matrix."""

from __future__ import annotations

from collections import deque
import time
from typing import Any, Iterable


def edmonds_karp(
    nodes: Iterable[str], edges: Iterable[dict[str, Any]], source: str, sink: str
) -> dict[str, Any]:
    node_list = list(dict.fromkeys(nodes))
    if source not in node_list or sink not in node_list or source == sink:
        raise ValueError("source and sink must be distinct nodes in the network")
    started = time.perf_counter()
    residual = {node: {other: 0 for other in node_list} for node in node_list}
    adjacency = {node: set() for node in node_list}
    original: dict[tuple[str, str], int] = {}
    flow: dict[tuple[str, str], int] = {}
    for edge in edges:
        start, end = str(edge["source"]), str(edge["target"])
        capacity = edge["capacity"]
        if (start not in residual or end not in residual or not isinstance(capacity, int)
                or isinstance(capacity, bool) or capacity < 0):
            raise ValueError("flow edges require known nodes and non-negative capacities")
        residual[start][end] += capacity
        adjacency[start].add(end)
        adjacency[end].add(start)
        original[(start, end)] = original.get((start, end), 0) + capacity
        flow[(start, end)] = 0
    adjacency = {node: sorted(neighbors) for node, neighbors in adjacency.items()}
    total_flow = 0
    paths: list[dict[str, Any]] = []
    iterations = edge_checks = 0
    while True:
        iterations += 1
        parent: dict[str, str | None] = {source: None}
        queue = deque([source])
        while queue and sink not in parent:
            node = queue.popleft()
            for neighbor in adjacency[node]:
                edge_checks += 1
                if neighbor not in parent and residual[node][neighbor] > 0:
                    parent[neighbor] = node
                    queue.append(neighbor)
        if sink not in parent:
            break
        path: list[str] = []
        node = sink
        bottleneck: int | None = None
        while node is not None:
            path.append(node)
            previous = parent[node]
            if previous is not None:
                capacity = residual[previous][node]
                bottleneck = capacity if bottleneck is None else min(bottleneck, capacity)
            node = previous
        path.reverse()
        assert bottleneck is not None
        for start, end in zip(path, path[1:]):
            residual[start][end] -= bottleneck
            residual[end][start] += bottleneck
            forward_room = original.get((start, end), 0) - flow.get((start, end), 0)
            forward_amount = min(bottleneck, forward_room)
            if forward_amount:
                flow[(start, end)] = flow.get((start, end), 0) + forward_amount
            reverse_amount = bottleneck - forward_amount
            if reverse_amount:
                flow[(end, start)] = flow.get((end, start), 0) - reverse_amount
        total_flow += bottleneck
        paths.append({"path": path, "bottleneck": bottleneck})
    reachable = {source}
    queue = deque([source])
    while queue:
        node = queue.popleft()
        for neighbor in adjacency[node]:
            edge_checks += 1
            if neighbor not in reachable and residual[node][neighbor] > 0:
                reachable.add(neighbor)
                queue.append(neighbor)
    cut = [
        {"source": start, "target": end, "capacity": capacity}
        for (start, end), capacity in original.items()
        if start in reachable and end not in reachable
    ]
    used = [
        {
            "source": start,
            "target": end,
            "capacity": capacity,
            "flow": flow.get((start, end), 0),
        }
        for (start, end), capacity in original.items()
    ]
    return {
        "maximum_flow": total_flow,
        "augmenting_paths": paths,
        "used_capacities": used,
        "min_cut": {"source_side": sorted(reachable), "sink_side": sorted(set(node_list) - reachable), "edges": cut},
        "stats": {
            "algorithm": "edmonds_karp", "iterations": iterations,
            "edge_checks": edge_checks, "augmentations": len(paths),
            "execution_ms": (time.perf_counter() - started) * 1000,
        },
    }
