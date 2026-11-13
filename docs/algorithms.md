# Algorithms and application mapping

All graph algorithms are implemented in ordinary Python and accept in-memory graphs. No algorithm imports or queries SQLite. Routing weights are chosen explicitly; distance and travel time are never silently substituted.

| Implementation | Worst-case time | Space | Application |
|---|---:|---:|---|
| Binary-heap Dijkstra | `O((V+E) log V)` | `O(V+E)` | Fastest/shortest route and ambulance ETA |
| Array Dijkstra | `O(V²)` | `O(V+E)` | Independent implementation and benchmark comparison |
| A* | Heuristic/graph dependent; exponential worst case generally | `O(V+E)` | Goal-directed route optimization |
| BFS | `O(V+E)` | `O(V)` | Reachability and closure analysis |
| Iterative DFS | `O(V+E)` | `O(V)` | Reachability and network exploration |
| Kruskal with DSU | `O(E log E)` | `O(V+E)` | Minimum-distance/cost infrastructure forest |
| Edmonds–Karp | `O(VE²)` | `O(V²)` in the residual-matrix implementation | Evacuation capacity |
| Bellman–Ford | `O(VE)` | `O(V+E)` | Negative-weight and reachable negative-cycle lesson |

## Shortest paths

Dijkstra's two variants reject negative selected weights, stop at the target, reconstruct a complete path, and return a null cost for an unreachable target. Statistics include edge checks, successful relaxations, iterations, visited-node order, elapsed milliseconds, and heap operations (zero for the array implementation).

A* uses `f(n) = g(n) + h(n)`. Great-circle distance is computed with Haversine. To remain admissible if editable road distance is below straight-line distance, the distance heuristic scales the direct great-circle estimate by the minimum observed road-distance/geographic-distance ratio. For time, it divides direct distance by the maximum observed straight-line speed over directed open roads. These global lower bounds do not overestimate supported route costs. A zero lower bound is used if geometry cannot support a positive estimate.

Route traces emit node visits and successful distance updates. The visualizer replays the backend event list and keeps tracing out of benchmarks.

## Traversals and connectivity

BFS and DFS operate on open directed edges and return their traversal order and unreachable locations from the selected root. The reported component list uses an explicitly undirected view so reciprocal road pairs describe the physical network's connected regions. A component of one vertex is reported as isolated.

## Infrastructure forest

Kruskal deduplicates reciprocal directed road records by unordered endpoint pair, keeps the least selected weight for each pair, sorts edges, and uses path-compressed union-by-size DSU. It returns selected and excluded edges, total weight, and all components. A disconnected graph yields a minimum spanning forest, not a misleading spanning tree.

## Evacuation flow

The flow graph uses a super-source, zone demand capacities, open directed road evacuation capacities, shelter intake capacities, and a super-sink. Edmonds–Karp repeatedly performs BFS on residual capacity, augments by the path bottleneck, and returns augmenting paths plus a residual reachable-set min-cut. Road travel time is not used. Reported maximum flow and unserved demand are simulated people per configured period and are not safety guidance.

## Bellman–Ford sandbox

Bellman–Ford supports negative educational weights, stops early when an iteration makes no update, and detects/reconstructs a reachable negative cycle. Nodes affected downstream are reported with `-Infinity`. This graph is supplied separately and never modifies Metroville's physical road weights.

## Benchmark methodology

The benchmark generator uses a repeatable random seed, one graph shared by all methods, and a chain to keep the graph connected. Each method receives a warm-up call, then repeated measured calls; medians and minima are calculated from wall-clock measurements. Counters are algorithm-generated. Tracing is disabled. Results vary with hardware, Python runtime, seed, density, and graph shape; an observed timing is not a complexity proof.
