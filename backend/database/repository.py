"""Parameterized persistence operations shared by application services."""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def execute(db: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
    return db.execute(query, params)


def rows(db: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in execute(db, query, params).fetchall()]


def row(db: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    value = execute(db, query, params).fetchone()
    return dict(value) if value is not None else None


def scalar(db: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> Any:
    value = execute(db, query, params).fetchone()
    return value[0] if value is not None else None


def begin(db: sqlite3.Connection) -> None:
    execute(db, "BEGIN IMMEDIATE")


def commit(db: sqlite3.Connection) -> None:
    db.commit()


def rollback(db: sqlite3.Connection) -> None:
    db.rollback()


def record_event(db: sqlite3.Connection, event_type: str, message: str) -> None:
    execute(db, "INSERT INTO simulation_events(event_type, message) VALUES (?, ?)", (event_type, message))


def persist_run(db: sqlite3.Connection, table: str, columns: tuple[str, ...], values: tuple[Any, ...]) -> None:
    allowed = {
        "evacuation_runs": ("result_json", "total_demand", "maximum_flow"),
        "benchmark_runs": ("result_json",),
        "algorithm_runs": ("algorithm", "result_json"),
    }
    if table not in allowed or allowed[table] != columns:
        raise ValueError("unsupported run record")
    names = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    execute(db, f"INSERT INTO {table} ({names}) VALUES ({placeholders})", values)


def json_value(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), allow_nan=False)
