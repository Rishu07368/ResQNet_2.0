"""Flask application factory and API error handling."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, jsonify

from backend.database.database import close_db, database_path, get_db, init_db
from backend.data.seed import seed_demo
from backend.routes.api import api, web


def create_app(test_config: dict | None = None) -> Flask:
    project_root = Path(__file__).resolve().parents[1]
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=database_path(),
        FRONTEND=str(project_root / "frontend"),
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)
    app.teardown_appcontext(close_db)
    app.register_blueprint(api)
    app.register_blueprint(web)

    @app.errorhandler(ValueError)
    def handle_value_error(error: ValueError):
        return jsonify({"error": True, "code": "VALIDATION_ERROR", "message": str(error)}), 400

    @app.errorhandler(LookupError)
    def handle_lookup_error(error: LookupError):
        return jsonify({"error": True, "code": "NOT_FOUND", "message": str(error)}), 404

    @app.errorhandler(sqlite3.IntegrityError)
    def handle_integrity_error(error: sqlite3.IntegrityError):
        return jsonify({"error": True, "code": "CONFLICT", "message": str(error)}), 409

    @app.errorhandler(404)
    def handle_not_found(_error):
        return jsonify({"error": True, "code": "NOT_FOUND", "message": "Resource not found"}), 404

    with app.app_context():
        init_db()
        seed_demo(get_db())
    return app


app = create_app()
