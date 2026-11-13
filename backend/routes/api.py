"""JSON API endpoints; business logic remains in services."""

from __future__ import annotations

import math

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from backend.algorithms.bellman_ford import bellman_ford
from backend.database.database import get_db
from backend.database.repository import rows, scalar
from backend.data.seed import seed_demo
from backend.services import analytics_service, dispatch_service, evacuation_service
from backend.services import hospital_service, network_service, routing_service

api = Blueprint("api", __name__, url_prefix="/api")
web = Blueprint("web", __name__)


def _body() -> dict:
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ValueError("Request body must be a JSON object")
    return value


def _required(body: dict, *fields: str) -> None:
    missing = [field for field in fields if body.get(field) is None]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")


def _strings(body: dict, *fields: str) -> None:
    for field in fields:
        value = body.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")


@api.get("/health")
def health():
    scalar(get_db(), "SELECT 1")
    return jsonify({"ok": True, "service": "ResQNet", "mode": "simulation"})


@api.get("/dashboard/summary")
def dashboard_summary():
    return jsonify(analytics_service.summary(get_db()))


@api.get("/network")
def get_network():
    return jsonify(network_service.network(get_db()))


@api.get("/roads")
def get_roads():
    return jsonify({"roads": network_service.road_list(get_db())})


@api.get("/ambulances")
def get_ambulances():
    return jsonify({"ambulances": rows(get_db(), """SELECT a.*,l.name AS location_name
        FROM ambulances a JOIN locations l ON l.id=a.location_id ORDER BY a.id""")})


@api.get("/hospitals")
def get_hospitals():
    return jsonify({"hospitals": hospital_service.hospitals(get_db())})


@api.get("/incidents")
def get_incidents():
    return jsonify({"incidents": dispatch_service.incident_list(get_db())})


@api.post("/incidents")
def create_incident():
    body = _body()
    _required(body, "location_id", "incident_type", "severity")
    _strings(body, "location_id", "incident_type", "severity")
    if body["severity"] not in ("Critical", "High", "Medium", "Low"):
        raise ValueError("severity must be Critical, High, Medium, or Low")
    if body.get("required_unit", "ambulance") not in ("ambulance", "fire", "police"):
        raise ValueError("required_unit must be ambulance, fire, or police")
    for field in ("required_specialty", "description"):
        if field in body and body[field] is not None and not isinstance(body[field], str):
            raise ValueError(f"{field} must be a string")
    return jsonify({"incident": dispatch_service.create_incident(get_db(), body)}), 201


@api.post("/incidents/<int:incident_id>/dispatch")
def dispatch_incident(incident_id: int):
    return jsonify(dispatch_service.dispatch(get_db(), incident_id))


@api.post("/incidents/<int:incident_id>/dispatch-options")
def dispatch_options(incident_id: int):
    return jsonify(dispatch_service.dispatch_options(get_db(), incident_id))


@api.patch("/incidents/<int:incident_id>/status")
def update_incident_status(incident_id: int):
    body = _body()
    _required(body, "status")
    _strings(body, "status")
    return jsonify({"incident": dispatch_service.update_status(get_db(), incident_id, body["status"])})


@api.post("/incidents/<int:incident_id>/hospital-recommendations")
def hospital_recommendations(incident_id: int):
    return jsonify(hospital_service.recommend(get_db(), incident_id))


@api.post("/incidents/<int:incident_id>/allocate-hospital")
def allocate_hospital(incident_id: int):
    body = _body()
    _required(body, "hospital_id")
    _strings(body, "hospital_id")
    return jsonify({"allocation": hospital_service.allocate(get_db(), incident_id, body["hospital_id"])})


@api.post("/hospitals/allocate-queue")
def allocate_hospital_queue():
    return jsonify({"heuristic": "Critical, High, Medium, Low; then creation time; greedy ETA/capacity choice",
                    "results": hospital_service.allocate_queue(get_db())})


@api.post("/routes/shortest-path")
def shortest_path():
    body = _body()
    _required(body, "source", "destination")
    _strings(body, "source", "destination")
    if "algorithm" in body:
        _strings(body, "algorithm")
    if "metric" in body:
        _strings(body, "metric")
    result = routing_service.route(get_db(), body["source"], body["destination"],
                                   body.get("algorithm", "dijkstra_heap"), body.get("metric", "time"),
                                   include_alternatives=True)
    return jsonify(result)


@api.post("/routes/compare")
def route_compare():
    body = _body()
    _required(body, "source", "destination")
    _strings(body, "source", "destination")
    if "metric" in body:
        _strings(body, "metric")
    return jsonify(routing_service.compare(get_db(), body["source"], body["destination"], body.get("metric", "time")))


@api.post("/algorithms/visualize")
def visualize():
    body = _body()
    _required(body, "source", "destination")
    _strings(body, "source", "destination")
    for field in ("algorithm", "metric"):
        if field in body:
            _strings(body, field)
    return jsonify(routing_service.visualize(get_db(), body))


@api.post("/network/roads/<int:road_id>/close")
def close_road(road_id: int):
    return jsonify({"road": network_service.set_road_status(get_db(), road_id, False)})


@api.post("/network/roads/<int:road_id>/open")
def open_road(road_id: int):
    return jsonify({"road": network_service.set_road_status(get_db(), road_id, True)})


@api.put("/network/roads/<int:road_id>")
def update_road(road_id: int):
    return jsonify({"road": network_service.update_road(get_db(), road_id, _body())})


@api.post("/evacuation/simulate")
def evacuation():
    body = _body()
    _required(body, "zones", "shelter_ids")
    if not isinstance(body["zones"], list) or not isinstance(body["shelter_ids"], list):
        raise ValueError("zones and shelter_ids must be arrays")
    capacities = body.get("shelter_capacities", {})
    if not isinstance(capacities, dict):
        raise ValueError("shelter_capacities must be a JSON object")
    if any(not isinstance(item, dict) for item in body["zones"]):
        raise ValueError("each zone must be a JSON object")
    return jsonify(evacuation_service.simulate(
        get_db(), body["zones"], body["shelter_ids"], capacities
    ))


@api.post("/algorithms/benchmark")
def benchmark():
    body = _body()
    for field in ("size", "average_degree", "repetitions", "seed"):
        if field in body and (not isinstance(body[field], int) or isinstance(body[field], bool)):
            raise ValueError(f"{field} must be an integer")
    if "growth" in body and not isinstance(body["growth"], bool):
        raise ValueError("growth must be a boolean")
    if body.get("growth", False):
        return jsonify(routing_service.benchmark_growth(
            get_db(), body.get("average_degree", 4), body.get("repetitions", 3), body.get("seed", 42),
        ))
    return jsonify(routing_service.benchmark(get_db(), body.get("size", 100), body.get("average_degree", 4),
                                             body.get("repetitions", 3), body.get("seed", 42)))


@api.post("/algorithms/connectivity")
def connectivity():
    body = _body()
    _required(body, "source")
    _strings(body, "source")
    if "algorithm" in body:
        _strings(body, "algorithm")
    return jsonify(network_service.connectivity(get_db(), body["source"], body.get("algorithm", "bfs")))


@api.post("/algorithms/mst")
def mst():
    body = _body()
    return jsonify(network_service.infrastructure_plan(get_db(), body.get("weight", "distance")))


@api.post("/algorithms/bellman-ford")
def bellman_ford_demo():
    body = _body()
    _required(body, "nodes", "edges", "source")
    if not isinstance(body["nodes"], list) or not isinstance(body["edges"], list):
        raise ValueError("nodes and edges must be arrays")
    if not body["nodes"] or any(not isinstance(node, str) or not node for node in body["nodes"]):
        raise ValueError("nodes must be a non-empty array of non-empty strings")
    for edge in body["edges"]:
        if (not isinstance(edge, dict) or not isinstance(edge.get("source"), str)
                or not isinstance(edge.get("target"), str)
                or not isinstance(edge.get("weight"), (int, float))
                or isinstance(edge.get("weight"), bool)
                or not math.isfinite(edge.get("weight", float("nan")))):
            raise ValueError("each edge needs string source/target and a numeric weight")
    if not isinstance(body["source"], str) or (body.get("destination") is not None and not isinstance(body["destination"], str)):
        raise ValueError("source and destination must be node names")
    if "trace" in body and not isinstance(body["trace"], bool):
        raise ValueError("trace must be a boolean")
    return jsonify(bellman_ford(
        body["nodes"], body["edges"], body["source"], body.get("destination"), body.get("trace", False)
    ))


@api.get("/algorithms/theory")
def algorithm_theory():
    return jsonify(analytics_service.theory())


@api.get("/analytics/overview")
def analytics_overview():
    return jsonify(analytics_service.overview(get_db()))


@api.post("/demo/reset")
def reset_demo():
    seed_demo(get_db(), reset=True)
    return jsonify({"ok": True, "message": "Deterministic Metroville demo data restored."})


@web.get("/")
def index():
    return send_from_directory(current_app.config["FRONTEND"], "index.html")


@web.get("/<path:filename>")
def frontend_file(filename: str):
    return send_from_directory(current_app.config["FRONTEND"], filename)
