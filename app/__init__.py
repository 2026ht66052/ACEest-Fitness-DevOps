"""ACEest Fitness & Gym — Flask application factory.

The Tkinter desktop application (``legacy/Aceestver-*.py``) has been refactored
into a twelve-factor web service:

* ``app.core``   — pure business rules, fully unit tested
* ``app.db``     — SQLite persistence (same schema as the desktop versions)
* ``app.api``    — JSON API consumed by the CI smoke tests
* ``app.web``    — server-rendered UI replacing the Tkinter window
"""

from __future__ import annotations

import logging
import os

from flask import Flask, jsonify

from . import api, db, web
from .config import Config, TestConfig

__version__ = os.environ.get("APP_VERSION", "3.2.4")


def create_app(config_object: type[Config] | None = None, **overrides) -> Flask:
    """Build and configure a Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(config_object or Config)
    app.config.update(overrides)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    db.init_app(app)
    app.register_blueprint(api.bp)
    app.register_blueprint(web.bp)

    with app.app_context():
        db.init_db()

    @app.get("/health")
    def health():
        """Liveness probe — the process is up."""
        return jsonify({"status": "ok", "version": app.config["APP_VERSION"]})

    @app.get("/ready")
    def ready():
        """Readiness probe — the process can reach its database."""
        try:
            db.query("SELECT 1")
        except Exception as exc:  # pragma: no cover - defensive
            return jsonify({"status": "unavailable", "reason": str(exc)}), 503
        return jsonify({"status": "ready", "version": app.config["APP_VERSION"]})

    @app.get("/version")
    def version():
        """Version and deployment track, used to verify traffic splits."""
        return jsonify(
            {
                "app": "aceest-fitness",
                "version": app.config["APP_VERSION"],
                "track": app.config["APP_TRACK"],
                "instance": app.config["INSTANCE"],
            }
        )

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def server_error(_error):  # pragma: no cover - defensive
        return jsonify({"error": "internal server error"}), 500

    @app.after_request
    def add_track_headers(response):
        response.headers["X-App-Version"] = app.config["APP_VERSION"]
        response.headers["X-App-Track"] = app.config["APP_TRACK"]
        return response

    return app


def create_test_app(**overrides) -> Flask:
    """Convenience factory used by the pytest fixtures."""
    return create_app(TestConfig, **overrides)
