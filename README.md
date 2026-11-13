# ResQNet — Metroville Emergency Response Simulation

ResQNet is an offline-friendly academic application for the Analysis and Design of Algorithms (ADSA). It models a fictional city as a weighted, directed road graph and demonstrates how graph algorithms can support emergency-response and evacuation-planning workflows.

> **Simulation only.** ResQNet has no live emergency dispatch, traffic feed, mapping service, or external data connection. Its schematic city map and all operational records are simulated. Do not use it to guide real emergency response or evacuation decisions.

## Problem statement and objectives

Emergency planning combines different graph problems that must not be conflated: route optimization uses travel time or distance, while evacuation uses people-per-period capacities. ResQNet makes both graph models explicit and gives operators an interactive way to inspect algorithm decisions and their measured statistics.

Objectives:

- Represent Metroville locations and directed roads using a persistent SQLite graph.
- Calculate and compare fastest or shortest routes using two independent Dijkstra variants and admissible A*.
- Demonstrate traversals, minimum spanning forests, maximum flow, and negative-weight shortest paths.
- Exercise simulated incident creation, ambulance dispatch, status updates, hospital ranking, road closures, and bed reservations.
- Benchmark real Python executions on seeded graphs, separate from theoretical complexity.
- Keep algorithms pure, persistence centralized, and the interface usable without keys or paid services.

## Features

- **Command overview:** database-derived network, incident, ambulance, bed, and road-blockage counts; recent persisted activity.
- **Interactive map:** SVG nodes, directed road arrows, blocked road styling, route highlights, selection, and zoom controls. It renders the graph returned by Flask; it does not calculate routes.
- **Dispatch center:** create incidents, rank suitable reachable available ambulances by ETA, persist assignments and dispatch route, progress incident status, and release units on completion/cancellation.
- **Route optimizer:** Dijkstra heap, Dijkstra array, or A* for distance/time; same-snapshot comparison and route statistics.
- **Hospital allocation:** reject unavailable, full, unreachable, or specialty-incompatible hospitals; rank by ETA and available-bed tie-break; reserve beds transactionally. The optional queue workflow processes Critical → High → Medium → Low, then creation order, with greedy per-incident choices (not a globally optimal allocation).
- **Evacuation planner:** Edmonds–Karp over population demand, directed road capacities, and shelter intake; includes augmenting paths, road utilization, unserved demand, and min-cut.
- **Algorithm lab:** replay route traces forward/backward or animate them; BFS/DFS and Bellman–Ford educational scenarios are included.
- **Benchmarking:** seeded graph generation, warm-up, repeated measured executions, median/minimum time, algorithm counters, and SVG charts for repeated samples or a 25–500 vertex growth sweep. Tracing is disabled during timing; measured growth and asymptotic theory are clearly distinguished.
- **Network manager:** persistently close/reopen and modify individual directed roads; analyze reachability and plan a Kruskal minimum spanning forest.
- **Analytics and theory:** database-derived dispatch and incident aggregates, and algorithm/application complexity reference.
- **Reset demo data:** restores the reproducible initial network and removes prior simulation changes and records.

## Technology

- Python 3.10+, Flask, SQLite, Gunicorn
- HTML5, CSS3, vanilla ES modules, SVG
- Pytest and Flask test client
- No NetworkX, graph-algorithm library, frontend build step, external API key, or network map dependency

## Architecture

The application follows a downward dependency flow:

1. `backend/algorithms/` contains independent graph algorithms and shared edge types. Algorithms accept in-memory input and do not access SQLite.
2. `backend/services/` loads graph snapshots, coordinates algorithm calls, and applies domain rules.
3. `backend/database/` owns SQLite connections, schema, and parameterized repository helpers.
4. `backend/routes/api.py` validates HTTP input, calls services, and serializes JSON.
5. `frontend/` consumes the JSON API. `map.js` draws the returned graph and backend paths without inventing route logic.

### Directory layout

```text
backend/
  algorithms/     astar.py, bellman_ford.py, common.py, dijkstra.py,
                  edmonds_karp.py, kruskal.py, traversal.py
  data/           seed.py
  database/       database.py, repository.py
  routes/         api.py
  services/       analytics_service.py, dispatch_service.py, evacuation_service.py,
                  graph_service.py, hospital_service.py, network_service.py,
                  routing_service.py
  app.py
frontend/
  index.html
  css/style.css
  js/api.js, app.js, map.js
tests/
docs/
run.py
requirements.txt
Procfile
render.yaml
```

## Graph and deterministic seed

`G = (V, E)`:

- `locations` are vertices with stable IDs, type, and normalized geographic coordinates.
- Every `roads` row is one directed edge with independent `distance_km`, `travel_minutes`, `evacuation_capacity`, open/closed state, and infrastructure cost.
- Bidirectional streets have two reciprocal rows. Closing a direction does not silently close its reciprocal.
- Routing and connectivity snapshots omit closed roads. The visual network still shows them as blocked.
- Flow uses only `evacuation_capacity`; it does not treat travel time/distance as capacity.
- Seed generation is deterministic: 36 locations, a 6×6 connected street grid with 120 directed roads, eight ambulance units, six hospitals, six shelters, and two pending training incidents.

The database is created and seeded on first app startup. `RESQNET_DATABASE` changes the SQLite file location.

## Algorithms

| Algorithm | Complexity | ResQNet use |
|---|---:|---|
| Dijkstra, binary heap | `O((V + E) log V)` | Route optimizer and ambulance ETA |
| Dijkstra, array selection | `O(V²)` | Independent route comparison |
| A* | Graph/heuristic dependent; exponential worst case generally | Goal-directed route search with a geographic admissible lower bound |
| BFS | `O(V + E)` | Reachability and traversal |
| DFS | `O(V + E)` | Reachability and traversal |
| Kruskal + DSU | `O(E log E)` | Minimum spanning tree/forest over reciprocal-road-deduplicated graph |
| Edmonds–Karp | `O(VE²)` | Capacity-limited simulated evacuation |
| Bellman–Ford | `O(VE)` | Isolated educational negative-weight/cycle sandbox only |

Dijkstra rejects negative costs. A* uses great-circle coordinates and derives globally safe lower bounds from edge distance/geometry and observed geometric speed; this preserves admissibility when editable road lengths differ from straight-line distance. The default positive physical road data does not use Bellman–Ford's negative weights. The Bellman–Ford demo accepts a separate user-supplied educational graph and is never applied to road time/distance.

See [docs/algorithms.md](docs/algorithms.md) for implementation details and returned statistics.

## Database schema

The SQLite schema includes `locations`, `roads`, `ambulances`, `hospitals`, `shelters`, `incidents`, `dispatch_records`, `hospital_allocations`, `evacuation_runs`, `benchmark_runs`, `algorithm_runs`, and `simulation_events`. Foreign keys, indexes, field checks, parameterized SQL, and transactions protect important updates. Dispatch uses a conditional availability update; hospital reservation checks capacity in the same transaction.

## API

All JSON errors use `{"error": true, "code": "...", "message": "..."}`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health and simulation-mode status |
| GET | `/api/dashboard/summary` | Database-derived KPIs |
| GET | `/api/network`, `/api/roads` | Current graph, facilities, and road administration records |
| GET | `/api/ambulances`, `/api/hospitals`, `/api/incidents` | Operational records |
| POST | `/api/incidents` | Create an incident |
| POST | `/api/incidents/<id>/dispatch` | Select and persist the lowest-ETA suitable ambulance |
| PATCH | `/api/incidents/<id>/status` | Advance/cancel incident and release unit when terminal |
| POST | `/api/incidents/<id>/hospital-recommendations` | Rank suitable reachable hospitals |
| POST | `/api/incidents/<id>/allocate-hospital` | Reserve capacity for a hospital |
| POST | `/api/hospitals/allocate-queue` | Greedy severity/time ordered allocation |
| POST | `/api/routes/shortest-path`, `/api/routes/compare` | Route calculation and same-snapshot comparison |
| POST | `/api/network/roads/<id>/close`, `/open` | Road state changes |
| PUT | `/api/network/roads/<id>` | Update distance, time, or evacuation capacity |
| POST | `/api/evacuation/simulate` | Capacity-based maximum flow |
| POST | `/api/algorithms/visualize` | Shortest-path execution trace |
| POST | `/api/algorithms/connectivity`, `/mst`, `/bellman-ford` | Traversal, spanning forest, and educational graph lab |
| POST | `/api/algorithms/benchmark` | Seeded measured algorithm comparison |
| GET | `/api/algorithms/theory`, `/api/analytics/overview` | Complexity reference and analytics |
| POST | `/api/demo/reset` | Restore deterministic demo data |

Detailed request/response examples are in [docs/api.md](docs/api.md).

## Local setup (Windows PowerShell)

From the project directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest -q
python run.py
```

Open <http://127.0.0.1:5000>. To choose a database path for the current PowerShell session:

```powershell
$env:RESQNET_DATABASE = "C:\resqnet-data\metroville.db"
python run.py
```

The app binds to `127.0.0.1:5000` by default. Configure `HOST`, `PORT`, and `DEBUG` as environment variables for local use. Do not enable debug mode on a public service.

## Tests

Run `python -m pytest -q` from the project root. Tests cover algorithm results and preconditions plus Flask workflows: seeded data, incident creation/dispatch, double-dispatch rejection, road closure route changes, hospital allocation, evacuation, MST/connectivity, benchmark execution, validation, and demo reset. They do not assert wall-clock timing thresholds.

## Render deployment

The repository includes a `Procfile` and `render.yaml`. The Render Blueprint configures a persistent disk at `/var/data` and sets `RESQNET_DATABASE=/var/data/resqnet.db`; this is important because SQLite on Render's ordinary ephemeral filesystem can be lost on redeploy/restart. Review the disk size/cost and deployment region in `render.yaml` before creating the service.

For manual deployment, create a Python web service from the repository:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 run:app`
- Add a persistent disk mounted at `/var/data`.
- Set `RESQNET_DATABASE` to `/var/data/resqnet.db`.
- Keep `DEBUG` unset/false. Flask reads Render's `PORT` via Gunicorn; local `run.py` also honors `PORT`.

The project is prepared for deployment, but no external GitHub repository or Render service was created from this workspace.

## Limitations and future enhancements

- The city is a schematic grid, not a street-accurate or navigable map.
- There is no live dispatch integration, GPS tracking, traffic, weather, authentication, or multi-user authorization.
- Dispatch models ambulances; fire/police facilities are represented as network locations, not staffed vehicle fleets. Incidents requiring those units receive an explicit unavailable-fleet response.
- Hospital queue assignment is greedy by severity/time and ETA/capacity, not globally optimal.
- Evacuation throughput is a theoretical max-flow result for configured demand/capacity, not a safety guarantee.
- SQLite is suitable for the single-service academic simulation; high-volume concurrent production use should move to a server database.
- Future work could add richer scenario authoring, time-varying capacities, authentication/audit permissions, and a separately validated production-grade routing/evacuation model.
