import pytest

from backend.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})
    return app.test_client()


def test_health_dashboard_and_seed_network(client):
    assert client.get("/api/health").json["ok"]
    network = client.get("/api/network").json
    assert len(network["locations"]) == 36
    assert len(network["roads"]) == 120
    assert len(network["hospitals"]) == 6
    summary = client.get("/api/dashboard/summary").json
    assert summary["available_ambulances"] == 8
    assert summary["active_incidents"] == 2


def test_create_dispatch_double_assignment_and_status(client):
    created = client.post("/api/incidents", json={
        "location_id": "M18", "incident_type": "Test call", "severity": "Critical",
        "required_specialty": "trauma", "description": "Training only",
    })
    assert created.status_code == 201
    incident_id = created.json["incident"]["id"]
    options = client.post(f"/api/incidents/{incident_id}/dispatch-options", json={})
    assert options.status_code == 200
    assert options.json["selected"]["ambulance_id"]
    assert client.get("/api/incidents").json["incidents"][0]["status"] == "Pending"
    dispatched = client.post(f"/api/incidents/{incident_id}/dispatch", json={})
    assert dispatched.status_code == 200
    assert dispatched.json["selected"]["ambulance_id"]
    assert client.post(f"/api/incidents/{incident_id}/dispatch", json={}).status_code == 400
    assert client.patch(f"/api/incidents/{incident_id}/status", json={"status": "On Scene"}).status_code == 200
    ambulance = next(unit for unit in client.get("/api/ambulances").json["ambulances"]
                     if unit["id"] == dispatched.json["selected"]["ambulance_id"])
    assert ambulance["status"] == "on_scene"
    assert ambulance["location_id"] == "M18"
    assert client.patch(f"/api/incidents/{incident_id}/status", json={"status": "Transporting"}).status_code == 200
    assert client.patch(f"/api/incidents/{incident_id}/status", json={"status": "Resolved"}).status_code == 200
    ambulance = next(unit for unit in client.get("/api/ambulances").json["ambulances"]
                     if unit["id"] == dispatched.json["selected"]["ambulance_id"])
    assert ambulance["status"] == "available"


def test_route_changes_when_road_closes(client):
    before = client.post("/api/routes/shortest-path", json={
        "source": "M01", "destination": "M06", "algorithm": "dijkstra_heap",
    })
    assert before.status_code == 200
    road_id = before.json["roads"][0]
    assert client.post(f"/api/network/roads/{road_id}/close").status_code == 200
    after = client.post("/api/routes/shortest-path", json={
        "source": "M01", "destination": "M06", "algorithm": "dijkstra_heap",
    })
    assert after.status_code == 200
    assert road_id not in after.json["roads"]
    assert before.json["alternative_routes"]
    assert client.post(f"/api/network/roads/{road_id}/open").status_code == 200


def test_hospital_allocation_and_capacity(client):
    incident = client.post("/api/incidents", json={
        "location_id": "M17", "incident_type": "Trauma drill", "severity": "High",
        "required_specialty": "trauma",
    }).json["incident"]
    recommendation = client.post(f"/api/incidents/{incident['id']}/hospital-recommendations", json={})
    assert recommendation.status_code == 200
    hospital_id = recommendation.json["recommendation"]["hospital_id"]
    assert client.post(f"/api/incidents/{incident['id']}/allocate-hospital",
                       json={"hospital_id": hospital_id}).status_code == 200
    beds_after_first_allocation = next(
        item["occupied_beds"] for item in client.get("/api/hospitals").json["hospitals"]
        if item["id"] == hospital_id
    )
    duplicate = client.post(f"/api/incidents/{incident['id']}/allocate-hospital",
                            json={"hospital_id": hospital_id})
    assert duplicate.status_code == 400
    assert duplicate.json["message"] == "This incident already has a hospital allocation"
    beds_after_duplicate = next(
        item["occupied_beds"] for item in client.get("/api/hospitals").json["hospitals"]
        if item["id"] == hospital_id
    )
    assert beds_after_duplicate == beds_after_first_allocation
    recommendations_again = client.post(
        f"/api/incidents/{incident['id']}/hospital-recommendations", json={},
    )
    assert recommendations_again.status_code == 200
    assert recommendations_again.json["allocation"]["hospital_id"] == hospital_id
    hospital = next(item for item in client.get("/api/hospitals").json["hospitals"] if item["id"] == hospital_id)
    assert hospital["occupied_beds"] >= 1


def test_existing_allocation_is_detected_from_either_record(client):
    incident = client.post("/api/incidents", json={
        "location_id": "M17", "incident_type": "Legacy allocation", "severity": "High",
    }).json["incident"]
    recommendation = client.post(
        f"/api/incidents/{incident['id']}/hospital-recommendations", json={},
    ).json["recommendation"]
    assert client.post(f"/api/incidents/{incident['id']}/allocate-hospital",
                       json={"hospital_id": recommendation["hospital_id"]}).status_code == 200
    with client.application.app_context():
        from backend.database.database import get_db

        get_db().execute("UPDATE incidents SET hospital_id=NULL WHERE id=?", (incident["id"],))
        get_db().commit()
    existing = client.post(
        f"/api/incidents/{incident['id']}/hospital-recommendations", json={},
    )
    assert existing.status_code == 200
    assert existing.json["allocation"]["hospital_id"] == recommendation["hospital_id"]
    assert existing.json["recommendation"] is None
    queue = client.post("/api/hospitals/allocate-queue", json={})
    assert incident["id"] not in [item["incident_id"] for item in queue.json["results"]]


def test_evacuation_mst_connectivity_and_benchmark(client):
    result = client.post("/api/evacuation/simulate", json={
        "zones": [{"location_id": "M03", "population": 120}, {"location_id": "M15", "population": 80}],
        "shelter_ids": ["S-01", "S-02"],
    })
    assert result.status_code == 200
    assert result.json["maximum_flow"] <= result.json["total_demand"]
    assert result.json["unserved_demand"] == result.json["total_demand"] - result.json["maximum_flow"]
    assert client.post("/api/algorithms/mst", json={"weight": "distance"}).json["component_count"] == 1
    assert client.post("/api/algorithms/connectivity", json={"source": "M01", "algorithm": "bfs"}).status_code == 200
    benchmark = client.post("/api/algorithms/benchmark", json={
        "size": 25, "average_degree": 2, "repetitions": 1, "seed": 7,
    })
    assert benchmark.status_code == 200
    assert benchmark.json["algorithms"]["dijkstra_heap"]["median_ms"] >= 0
    growth = client.post("/api/algorithms/benchmark", json={
        "growth": True, "average_degree": 2, "repetitions": 1, "seed": 7,
    })
    assert growth.status_code == 200
    assert [item["size"] for item in growth.json["growth_results"]] == [25, 50, 100, 250, 500]


def test_evacuation_capacity_override_and_priority_queue(client):
    limited = client.post("/api/evacuation/simulate", json={
        "zones": [{"location_id": "M03", "population": 300}],
        "shelter_ids": ["S-01"],
        "shelter_capacities": {"S-01": 10},
    })
    assert limited.status_code == 200
    assert limited.json["maximum_flow"] == 10
    assert client.post("/api/evacuation/simulate", json={
        "zones": [{"location_id": "M03", "population": 3}],
        "shelter_ids": ["S-01"],
        "shelter_capacities": {"S-01": -1},
    }).status_code == 400
    client.post("/api/incidents", json={
        "location_id": "M18", "incident_type": "Low priority drill", "severity": "Low",
    })
    critical = client.post("/api/incidents", json={
        "location_id": "M18", "incident_type": "Critical priority drill", "severity": "Critical",
    }).json["incident"]["id"]
    queued = client.post("/api/hospitals/allocate-queue", json={})
    assert queued.status_code == 200
    assert queued.json["results"][0]["incident_id"] == critical


def test_validation_and_demo_reset(client):
    assert client.post("/api/incidents", json={"location_id": "unknown"}).status_code == 400
    assert client.post("/api/routes/shortest-path", json={"source": "M01"}).status_code == 400
    assert client.post("/api/routes/shortest-path", json={"source": [], "destination": "M01"}).status_code == 400
    assert client.post("/api/network/roads/9999/close").status_code == 404
    assert client.post("/api/algorithms/bellman-ford", json={
        "nodes": ["A"], "edges": [{"source": "A", "target": "B"}], "source": "A",
    }).status_code == 400
    fire = client.post("/api/incidents", json={
        "location_id": "M13", "incident_type": "Fire drill", "severity": "High", "required_unit": "fire",
    })
    assert fire.status_code == 201
    assert client.post(f"/api/incidents/{fire.json['incident']['id']}/dispatch", json={}).json["code"] == "VALIDATION_ERROR"
    assert client.post("/api/demo/reset", json={}).status_code == 200
    assert client.get("/api/dashboard/summary").json["active_incidents"] == 2
