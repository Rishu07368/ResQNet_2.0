# ResQNet architecture

## Request and computation flow

```text
HTML/CSS/ES modules
        │ JSON over same-origin HTTP
        ▼
Flask routes (validation / status codes / JSON only)
        ▼
Domain services (dispatch, routing, hospitals, network, evacuation, analytics)
        ├─────────────► Pure algorithms (no I/O)
        ▼
SQLite repository / connection layer
        ▼
Persisted Metroville graph and simulation records
```

The Flask application factory initializes the schema and deterministic seed. `get_db()` creates one SQLite connection per Flask application context, enables foreign keys and a busy timeout, and the teardown hook closes it. Services share the request connection. SQLite writes that alter multiple records use explicit transactions.

## Graph model

`locations.id` is a stable vertex identifier. `roads` is an edge table with one row per direction and independent positive distance/time and non-negative evacuation capacity. `is_open=0` persists closure state. Routing and traversal use an open-road snapshot; network visualization receives open and closed rows so blocked streets remain visible. A road closure therefore changes actual subsequent algorithm results, not just styling.

The map uses the same `locations`/`roads` payload returned by `/api/network`. It overlays route node/road IDs returned from a backend calculation. SVG coordinates are only a schematic projection of seeded latitude/longitude.

## Persistence and transaction boundaries

- Incident creation validates the location and writes an event.
- Dispatch computes routes for currently eligible units, then uses `BEGIN IMMEDIATE` and a conditional update (`available` and unassigned) before recording the incident assignment and route. A stale selection fails rather than double-assigning.
- Status completion/cancellation releases an assigned ambulance and records activity transactionally.
- Hospital reservation rechecks acceptance and bed availability while updating occupied beds and incident allocation in one transaction.
- Evacuation and benchmark inputs/outputs are serialized into run-history tables.
- Demo reset deletes dependent records before their referenced entities and reseeds the same fixed scenario.

All database queries are centralized in repository helpers or service SQL using bound parameters. Schema identifiers used in the limited run-history insertion helper are whitelisted.

## Module boundaries

- `backend/algorithms/`: Dijkstra heap/array, A*, BFS/DFS, Kruskal/DSU, Edmonds–Karp, Bellman–Ford.
- `backend/services/`: service orchestration and domain rules; route calculations use one loaded open-road graph for each call.
- `backend/database/`: connection/schema and reusable repository helpers.
- `backend/data/`: deterministic city fixtures.
- `backend/routes/`: Flask request/response translation.
- `frontend/js/api.js`: common JSON/error handling.
- `frontend/js/map.js`: SVG rendering, node selection, highlights, and zoom.
- `frontend/js/app.js`: page navigation and workflow wiring.

## Runtime configuration

`RESQNET_DATABASE` chooses the SQLite file (default `resqnet.db` at the project root). `HOST`, `PORT`, and `DEBUG` configure the local runner. Render uses the provided persistent disk path and Gunicorn entry point.
