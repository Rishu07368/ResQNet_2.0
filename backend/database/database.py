"""SQLite connection lifecycle and schema initialization."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS locations (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
    latitude REAL NOT NULL, longitude REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS roads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES locations(id),
    target_id TEXT NOT NULL REFERENCES locations(id),
    distance_km REAL NOT NULL CHECK(distance_km > 0),
    travel_minutes REAL NOT NULL CHECK(travel_minutes > 0),
    evacuation_capacity INTEGER NOT NULL CHECK(evacuation_capacity >= 0),
    is_open INTEGER NOT NULL DEFAULT 1 CHECK(is_open IN (0,1)),
    infrastructure_cost REAL NOT NULL DEFAULT 1,
    UNIQUE(source_id, target_id)
);
CREATE INDEX IF NOT EXISTS idx_roads_source ON roads(source_id, is_open);
CREATE TABLE IF NOT EXISTS ambulances (
    id TEXT PRIMARY KEY, location_id TEXT NOT NULL REFERENCES locations(id),
    status TEXT NOT NULL CHECK(status IN ('available','dispatched','on_scene','transporting')),
    capabilities TEXT NOT NULL DEFAULT 'general', assigned_incident INTEGER
);
CREATE TABLE IF NOT EXISTS hospitals (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, location_id TEXT NOT NULL REFERENCES locations(id),
    total_beds INTEGER NOT NULL CHECK(total_beds >= 0),
    occupied_beds INTEGER NOT NULL CHECK(occupied_beds >= 0 AND occupied_beds <= total_beds),
    specialties TEXT NOT NULL, accepting INTEGER NOT NULL DEFAULT 1 CHECK(accepting IN (0,1))
);
CREATE TABLE IF NOT EXISTS shelters (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, location_id TEXT NOT NULL REFERENCES locations(id),
    capacity INTEGER NOT NULL CHECK(capacity >= 0)
);
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT, location_id TEXT NOT NULL REFERENCES locations(id),
    incident_type TEXT NOT NULL, severity TEXT NOT NULL CHECK(severity IN ('Critical','High','Medium','Low')),
    required_unit TEXT NOT NULL DEFAULT 'ambulance', required_specialty TEXT,
    description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'Pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assigned_ambulance TEXT REFERENCES ambulances(id), hospital_id TEXT REFERENCES hospitals(id)
);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status, created_at);
CREATE TABLE IF NOT EXISTS dispatch_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id INTEGER NOT NULL REFERENCES incidents(id),
    ambulance_id TEXT NOT NULL REFERENCES ambulances(id), route_json TEXT NOT NULL,
    eta_minutes REAL NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS hospital_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id INTEGER NOT NULL REFERENCES incidents(id),
    hospital_id TEXT NOT NULL REFERENCES hospitals(id), beds_reserved INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(incident_id)
);
CREATE TABLE IF NOT EXISTS evacuation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, result_json TEXT NOT NULL,
    total_demand INTEGER NOT NULL, maximum_flow INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS benchmark_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, result_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS algorithm_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, algorithm TEXT NOT NULL,
    result_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS simulation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL,
    message TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = current_app.config["DATABASE"]
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        g.db = connection
    return g.db


def close_db(_error: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    connection = get_db()
    connection.executescript(SCHEMA)
    connection.commit()


def database_path() -> str:
    return os.environ.get("RESQNET_DATABASE", str(Path(__file__).resolve().parents[2] / "resqnet.db"))
