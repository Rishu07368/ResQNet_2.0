# ResQNet API reference

The API is same-origin under `/api`. JSON failures use:

```json
{"error": true, "code": "VALIDATION_ERROR", "message": "A useful explanation"}
```

Validation errors return 400, missing resources 404, and database conflicts 409. Successful resource creation returns 201.

## Read endpoints

- `GET /health`
- `GET /dashboard/summary`
- `GET /network` — locations, all roads (including closed), ambulances, hospitals, shelters.
- `GET /roads` — road rows with endpoint names.
- `GET /ambulances`
- `GET /hospitals`
- `GET /incidents`
- `GET /algorithms/theory`
- `GET /analytics/overview`

## Operational workflows

Create an incident:

```json
POST /incidents
{
  "location_id": "M17",
  "incident_type": "Traffic collision",
  "severity": "High",
  "required_unit": "ambulance",
  "required_specialty": "trauma",
  "description": "Training scenario"
}
```

`required_unit` may be `ambulance`, `fire`, or `police`. This demo tracks ambulance vehicles only; attempting dispatch for a fire/police unit returns an explicit unavailable-fleet explanation.

Preview available choices with `POST /incidents/<id>/dispatch-options` and `{}`; this does not change state. After operator confirmation, call `POST /incidents/<id>/dispatch` with `{}`. The response includes the selected ambulance, computed route, ETA, and other reachable eligible options. Update status with `PATCH /incidents/<id>/status` and `{"status":"On Scene"}`; supported transitions are Pending → Dispatched → On Scene → Transporting → Resolved, with cancellation from nonterminal states.

Hospital evaluation: `POST /incidents/<id>/hospital-recommendations` with `{}`. Reserve one recommendation with `POST /incidents/<id>/allocate-hospital` and `{"hospital_id":"H-01"}`. Each incident can have one allocation; subsequent recommendation requests return the existing allocation and a duplicate reservation request returns a clear validation error. `POST /hospitals/allocate-queue` schedules active, unallocated incidents by severity then creation time using a greedy reachable-ETA/capacity choice.

## Routing and road management

```json
POST /routes/shortest-path
{"source":"M01","destination":"M36","algorithm":"astar","metric":"time"}
```

Algorithms: `dijkstra_heap`, `dijkstra_array`, `astar`; metrics: `time`, `distance`. `POST /routes/compare` uses the same request shape and runs all three methods. `POST /algorithms/visualize` uses the same shape and adds a trace.

- `POST /network/roads/<id>/close`
- `POST /network/roads/<id>/open`
- `PUT /network/roads/<id>` with any of `distance_km`, `travel_minutes`, `evacuation_capacity`.
- `POST /algorithms/connectivity` with `{"source":"M01","algorithm":"bfs"}` or `dfs`.
- `POST /algorithms/mst` with `{"weight":"distance"}` or `cost`.

## Evacuation and labs

```json
POST /evacuation/simulate
{
  "zones": [{"location_id":"M03","population":120}],
  "shelter_ids": ["S-01","S-02"],
  "shelter_capacities": {"S-01":100}
}
```

Each population must be a positive integer; shelter IDs must exist. The response includes throughput, unserved demand, augmenting paths, utilized roads, and min-cut.

`POST /algorithms/benchmark` accepts integer `size` (25–500), `average_degree` (2–20 and less than graph size), `repetitions` (1–7), and `seed`. Defaults are size 100, degree 4, three repetitions, seed 42. Add `"growth": true` to run a measured curve at sizes 25, 50, 100, 250, and 500 (same seed/degree/repetition count per size).

`POST /algorithms/bellman-ford` accepts `nodes`, `edges` (`source`, `target`, numeric `weight`), `source`, optional `destination`, and optional boolean-like `trace`. It is an isolated educational graph, not the physical network.

`POST /demo/reset` with `{}` restores the deterministic initial dataset.
