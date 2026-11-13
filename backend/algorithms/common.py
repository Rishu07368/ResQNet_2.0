"""Shared types and route reconstruction helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class Edge:
    target: str
    time: float
    distance: float
    capacity: int
    road_id: int | None = None

    def weight(self, metric: str) -> float:
        if metric not in ("time", "distance"):
            raise ValueError("metric must be 'time' or 'distance'")
        return self.time if metric == "time" else self.distance


Graph = Mapping[str, Sequence[Edge]]


def reconstruct_path(previous: Mapping[str, str | None], source: str, target: str) -> list[str]:
    if source == target:
        return [source]
    if target not in previous or previous[target] is None:
        return []
    path: list[str] = []
    node: str | None = target
    while node is not None:
        path.append(node)
        if node == source:
            return list(reversed(path))
        node = previous.get(node)
    return []


def result_path(
    source: str,
    target: str,
    distances: Mapping[str, float],
    previous: Mapping[str, str | None],
    stats: dict[str, Any],
) -> dict[str, Any]:
    cost = distances.get(target, float("inf"))
    return {
        "source": source,
        "destination": target,
        "path": reconstruct_path(previous, source, target),
        "cost": cost if cost != float("inf") else None,
        "distances": {key: value if value != float("inf") else None for key, value in distances.items()},
        "visited": stats.pop("_visited_order", []),
        "stats": stats,
    }
