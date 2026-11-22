"""Application configuration, driven entirely by environment variables."""

from __future__ import annotations

import os


class Config:
    """Base configuration."""

    #: Semantic version of the running application.  Injected at image build
    #: time (``--build-arg APP_VERSION``) and surfaced on ``/version`` so that
    #: blue-green / canary / A-B traffic can be verified from outside the cluster.
    APP_VERSION = os.environ.get("APP_VERSION", "3.2.4")

    #: Deployment colour or track (blue, green, stable, canary, shadow, a, b).
    #: Used by the deployment-strategy demos.
    APP_TRACK = os.environ.get("APP_TRACK", "stable")

    #: Pod name, so a response can be traced back to a replica.
    INSTANCE = os.environ.get("HOSTNAME", "local")

    DATABASE = os.environ.get("DATABASE_PATH", "/data/aceest_fitness.db")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    JSON_SORT_KEYS = False
    TESTING = False


class TestConfig(Config):
    """Configuration used by the pytest suite."""

    TESTING = True
    DATABASE = ":memory:"
    SECRET_KEY = "test-secret"
