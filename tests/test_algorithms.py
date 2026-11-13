import pytest

from backend.algorithms.astar import astar, haversine_km
from backend.algorithms.bellman_ford import bellman_ford
from backend.algorithms.common import Edge
from backend.algorithms.dijkstra import dijkstra_array, dijkstra_heap
from backend.algorithms.edmonds_karp import edmonds_karp
from backend.algorithms.kruskal import DisjointSet, kruskal
from backend.algorithms.traversal import bfs, connected_components, dfs


def graph(nodes, edges):
    result = {node: [] for node in nodes}
    for source, target, weight in edges:
        result[source].append(Edge(target, weight, weight, 10))
    return result


def test_dijkstra_heap_array_and_reachable_path():
    network = graph("ABCD", [("A", "B", 2), ("A", "C", 5), ("B", "C", 1), ("C", "D", 3), ("B", "D", 8)])
    heap, array = dijkstra_heap(network, "A", "D"), dijkstra_array(network, "A", "D")
    assert heap["path"] == ["A", "B", "C", "D"]
    assert heap["cost"] == array["cost"] == 6
    assert heap["visited"]
    assert heap["stats"]["edge_checks"] > 0


def test_dijkstra_unreachable_single_node_and_negative_rejection():
    disconnected = graph("ABC", [("A", "B", 1)])
    assert dijkstra_heap(disconnected, "A", "C")["path"] == []
    assert dijkstra_array(disconnected, "A", "C")["cost"] is None
    assert dijkstra_heap({"A": []}, "A", "A")["path"] == ["A"]
    negative = graph("AB", [("A", "B", -1)])
    with pytest.raises(ValueError, match="non-negative"):
        dijkstra_heap(negative, "A", "B")
    with pytest.raises(ValueError, match="non-negative"):
        dijkstra_array(negative, "A", "B")


def test_astar_matches_dijkstra_and_uses_lower_bound():
    network = graph("ABCD", [("A", "B", 2), ("A", "C", 5), ("B", "C", 1), ("C", "D", 3)])
    coords = {"A": (37, -122), "B": (37, -121.99), "C": (37.01, -121.99), "D": (37.01, -121.98)}
    for metric in ("time", "distance"):
        result = astar(network, coords, "A", "D", metric)
        assert result["cost"] == dijkstra_heap(network, "A", "D", metric)["cost"]
    direct = haversine_km(coords["A"], coords["D"])
    direct_time_lower_bound = direct / max(edge.distance / (edge.time / 60) for edges in network.values() for edge in edges) * 60
    assert direct <= dijkstra_heap(network, "A", "D", "distance")["cost"]
    assert direct_time_lower_bound <= dijkstra_heap(network, "A", "D", "time")["cost"]


def test_astar_disconnected_and_closed_edge_snapshot():
    network = graph("ABC", [("A", "B", 1)])
    coords = {"A": (0, 0), "B": (0, 0.01), "C": (0, 0.02)}
    assert astar(network, coords, "A", "C")["path"] == []
    assert astar(network, coords, "A", "B")["path"] == ["A", "B"]


def test_bfs_dfs_cycles_disconnected_and_isolated():
    network = graph("ABCDE", [("A", "B", 1), ("B", "C", 1), ("C", "A", 1), ("D", "E", 1)])
    assert bfs(network, "A")["visited"] == ["A", "B", "C"]
    assert set(dfs(network, "A")["visited"]) == {"A", "B", "C"}
    assert bfs(network, "A")["unreachable"] == ["D", "E"]
    assert connected_components(network) == [["A", "B", "C"], ["D", "E"]]
    assert connected_components({"X": [], "Y": []}) == [["X"], ["Y"]]


def test_kruskal_mst_forest_and_disjoint_set():
    edges = [
        {"source": "A", "target": "B", "distance": 1},
        {"source": "B", "target": "A", "distance": 1.5},
        {"source": "B", "target": "C", "distance": 2},
        {"source": "A", "target": "C", "distance": 4},
        {"source": "D", "target": "E", "distance": 3},
    ]
    result = kruskal(["A", "B", "C", "D", "E", "F"], edges)
    assert result["total_weight"] == 6
    assert result["component_count"] == 3
    assert len(result["edges"]) == 3
    dsu = DisjointSet(["a", "b", "c"])
    assert dsu.union("a", "b")
    assert not dsu.union("b", "a")
    assert dsu.union("b", "c")


def test_edmonds_karp_known_flow_23_reverse_residual_and_min_cut():
    edges = [
        ("s", "v1", 16), ("s", "v2", 13), ("v1", "v2", 10), ("v2", "v1", 4),
        ("v1", "v3", 12), ("v3", "v2", 9), ("v2", "v4", 14), ("v4", "v3", 7),
        ("v3", "t", 20), ("v4", "t", 4),
    ]
    result = edmonds_karp(["s", "v1", "v2", "v3", "v4", "t"],
                          [{"source": u, "target": v, "capacity": c} for u, v, c in edges], "s", "t")
    assert result["maximum_flow"] == 23
    assert result["augmenting_paths"]
    assert result["min_cut"]["edges"]
    assert sum(edge["capacity"] for edge in result["min_cut"]["edges"]) == 23
    assert result["stats"]["augmentations"] == len(result["augmenting_paths"])
    assert all(item["flow"] <= item["capacity"] for item in result["used_capacities"])
    assert edmonds_karp(["s", "t"], [{"source": "s", "target": "t", "capacity": 0}], "s", "t")["maximum_flow"] == 0
    assert edmonds_karp(["s", "x", "t"], [{"source": "s", "target": "x", "capacity": 4}], "s", "t")["maximum_flow"] == 0


def test_bellman_ford_negative_edges_cycles_and_early_exit():
    edges = [
        {"source": "s", "target": "a", "weight": 4},
        {"source": "s", "target": "b", "weight": 5},
        {"source": "a", "target": "b", "weight": -2},
        {"source": "b", "target": "c", "weight": 3},
    ]
    result = bellman_ford(["s", "a", "b", "c", "isolated"], edges, "s", "c")
    assert result["distances"]["c"] == 5
    assert result["path"] == ["s", "a", "b", "c"]
    assert not result["has_negative_cycle"]
    assert result["iterations"] < 4
    cyclic = bellman_ford(["s", "a", "b", "t"], [
        {"source": "s", "target": "a", "weight": 1},
        {"source": "a", "target": "b", "weight": -3},
        {"source": "b", "target": "a", "weight": 1},
        {"source": "b", "target": "t", "weight": 2},
    ], "s", "t")
    assert cyclic["has_negative_cycle"]
    assert cyclic["negative_cycle"]
    assert cyclic["distances"]["t"] == "-Infinity"
