"""Breadth-first and depth-first traversal over a directed graph."""

from __future__ import annotations

from collections import deque
from typing import Any

from .common import Graph


def bfs(graph: Graph, source: str) -> dict[str, Any]:
    if source not in graph:
        raise ValueError("source must exist in the graph")
    queue = deque([source])
    visited: list[str] = []
    seen = {source}
    while queue:
        node = queue.popleft()
        visited.append(node)
        for edge in graph[node]:
            if edge.target not in seen:
                seen.add(edge.target)
                queue.append(edge.target)
    return {"source": source, "visited": visited, "unreachable": sorted(set(graph) - seen)}


def dfs(graph: Graph, source: str) -> dict[str, Any]:
    if source not in graph:
        raise ValueError("source must exist in the graph")
    stack = [source]
    visited: list[str] = []
    seen: set[str] = set()
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        visited.append(node)
        stack.extend(edge.target for edge in reversed(graph[node]) if edge.target not in seen)
    return {"source": source, "visited": visited, "unreachable": sorted(set(graph) - seen)}


def connected_components(graph: Graph) -> list[list[str]]:
    undirected: dict[str, set[str]] = {node: set() for node in graph}
    for source, edges in graph.items():
        for edge in edges:
            undirected[source].add(edge.target)
            undirected[edge.target].add(source)
    remaining = set(graph)
    components: list[list[str]] = []
    while remaining:
        root = min(remaining)
        component: list[str] = []
        stack = [root]
        remaining.remove(root)
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in sorted(undirected[node], reverse=True):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        components.append(sorted(component))
    return components
