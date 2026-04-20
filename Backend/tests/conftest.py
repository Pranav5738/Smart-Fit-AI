from __future__ import annotations

import os
import importlib
from typing import Iterator

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from routes import auth as auth_routes
from routes import profiles as profiles_routes
from services.auth_store import AuthStoreService
from services.profile_store import ProfileStoreService
from utils.exceptions import SmartFitError


@pytest.fixture()
def client() -> Iterator[TestClient]:
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if not test_database_url:
        pytest.skip("TEST_DATABASE_URL is required to run backend API tests")

    try:
        psycopg = importlib.import_module("psycopg")
        with psycopg.connect(test_database_url, connect_timeout=2):
            pass
    except Exception:
        pytest.skip("TEST_DATABASE_URL is unreachable")

    with psycopg.connect(test_database_url, connect_timeout=2) as connection:
        connection.execute(
            """
            TRUNCATE TABLE
                auth_sessions,
                auth_login_attempts,
                auth_users,
                scans,
                profiles
            """
        )
        connection.commit()

    auth_store = AuthStoreService(
        database_url=test_database_url,
        access_token_secret="test-token-secret",
        access_token_minutes=20,
        refresh_token_days=7,
        max_failed_attempts=5,
        lockout_minutes=10,
        attempt_window_minutes=15,
    )
    profile_store = ProfileStoreService(database_url=test_database_url)
    original_get_auth_store = auth_routes._get_auth_store
    original_get_profile_store = profiles_routes._get_profile_store

    if hasattr(original_get_auth_store, "cache_clear"):
        original_get_auth_store.cache_clear()

    if hasattr(original_get_profile_store, "cache_clear"):
        original_get_profile_store.cache_clear()

    auth_routes._get_auth_store = lambda: auth_store
    profiles_routes._get_profile_store = lambda: profile_store

    app = FastAPI()
    app.include_router(auth_routes.router)
    app.include_router(profiles_routes.router)

    @app.exception_handler(SmartFitError)
    async def smartfit_exception_handler(
        request: Request,
        exc: SmartFitError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
            },
        )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        auth_routes._get_auth_store = original_get_auth_store
        profiles_routes._get_profile_store = original_get_profile_store

        if hasattr(original_get_auth_store, "cache_clear"):
            original_get_auth_store.cache_clear()

        if hasattr(original_get_profile_store, "cache_clear"):
            original_get_profile_store.cache_clear()
