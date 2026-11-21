"""Regression guard: no API route may be reachable without a valid login."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("psycopg2")
pytest.importorskip("jose")
pytest.importorskip("passlib")

from fastapi.routing import APIRoute

from app.core.security import get_current_user
from app.main import app

PUBLIC_PATHS = {
    "/",
    "/health",
    "/api/auth/login",
}


def _uses_login(dependant):
    for sub in dependant.dependencies:
        if sub.call is get_current_user or _uses_login(sub):
            return True
    return False


def test_every_api_route_requires_login():
    unprotected = [
        f"{sorted(route.methods)} {route.path}"
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path not in PUBLIC_PATHS
        and not _uses_login(route.dependant)
    ]

    assert unprotected == []
