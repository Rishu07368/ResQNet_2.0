"""Kruskal minimum spanning forest with a disjoint-set data structure."""

from __future__ import annotations

from typing import Any, Iterable


class DisjointSet:
    def __init__(self, items: Iterable[str]) -> None:
        self.parent = {item: item for item in items}
        self.size = {item: 1 for item in self.parent}

    def find(self, item: str) -> str:
        if item not in self.parent:
            raise KeyError(item)
        while item != self.parent[item]:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first: str, second: str) -> bool:
        root_a, root_b = self.find(first), self.find(second)
        if root_a == root_b:
            return False
        if self.size[root_a] < self.size[root_b]:
            root_a, root_b = root_b, root_a
        self.parent[root_b] = root_a
        self.size[root_a] += self.size[root_b]
        return True


def kruskal(nodes: Iterable[str], edges: Iterable[dict[str, Any]], weight: str = "distance") -> dict[str, Any]:
    if weight not in ("distance", "cost"):
        raise ValueError("weight must be 'distance' or 'cost'")
    node_list = list(dict.fromkeys(nodes))
    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for edge in edges:
        first, second = sorted((str(edge["source"]), str(edge["target"])))
        key = (first, second)
        value = float(edge.get(weight, edge.get("distance", 0)))
        if first == second or value < 0:
            continue
        if key not in deduplicated or value < float(deduplicated[key].get(weight, deduplicated[key].get("distance", 0))):
            deduplicated[key] = {**edge, "source": first, "target": second, "weight": value}
    candidates = sorted(deduplicated.values(), key=lambda item: (item["weight"], item["source"], item["target"]))
    dsu = DisjointSet(node_list)
    selected: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    total = 0.0
    for edge in candidates:
        if edge["source"] not in dsu.parent or edge["target"] not in dsu.parent:
            raise ValueError("edge references a node outside the requested network")
        if dsu.union(edge["source"], edge["target"]):
            selected.append(edge)
            total += edge["weight"]
        else:
            excluded.append(edge)
    components: dict[str, list[str]] = {}
    for node in node_list:
        components.setdefault(dsu.find(node), []).append(node)
    return {
        "edges": selected,
        "excluded_edges": excluded,
        "total_weight": total,
        "components": [sorted(component) for component in components.values()],
        "component_count": len(components),
    }
