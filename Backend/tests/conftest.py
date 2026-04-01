from __future__ import annotations

from pathlib import Path
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
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "test_store.db"

    auth_routes.auth_store = AuthStoreService(
        db_path=db_path,
        access_token_secret="test-token-secret",
        access_token_minutes=20,
        refresh_token_days=7,
        max_failed_attempts=5,
        lockout_minutes=10,
        attempt_window_minutes=15,
    )
    profiles_routes.profile_store = ProfileStoreService(db_path=db_path)

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

    with TestClient(app) as test_client:
        yield test_client
