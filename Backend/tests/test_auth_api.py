from __future__ import annotations

from fastapi.testclient import TestClient


def _register_payload() -> dict:
    return {
        "name": "Smart Fit User",
        "email": "user@example.com",
        "password": "StrongPass1!",
        "height_cm": 173.2,
        "weight_kg": 70.5,
    }


def test_register_returns_user_and_tokens(client: TestClient) -> None:
    response = client.post("/auth/register", json=_register_payload())

    assert response.status_code == 201
    payload = response.json()

    assert payload["user"]["email"] == "user@example.com"
    assert payload["tokens"]["token_type"] == "bearer"
    assert payload["tokens"]["access_token"]
    assert payload["tokens"]["refresh_token"]


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    client.post("/auth/register", json=_register_payload())
    duplicate_response = client.post("/auth/register", json=_register_payload())

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error_code"] == "AUTH_EMAIL_EXISTS"


def test_signin_locks_after_repeated_failures(client: TestClient) -> None:
    client.post("/auth/register", json=_register_payload())

    last_response = None
    for _ in range(5):
        last_response = client.post(
            "/auth/signin",
            json={"email": "user@example.com", "password": "wrong-password"},
        )

    assert last_response is not None
    assert last_response.status_code == 429
    assert last_response.json()["error_code"] == "AUTH_LOCKED"


def test_refresh_and_signout_flow(client: TestClient) -> None:
    register_response = client.post("/auth/register", json=_register_payload())
    initial_payload = register_response.json()
    initial_refresh_token = initial_payload["tokens"]["refresh_token"]

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": initial_refresh_token},
    )
    assert refresh_response.status_code == 200

    refreshed_payload = refresh_response.json()
    rotated_refresh_token = refreshed_payload["tokens"]["refresh_token"]
    assert rotated_refresh_token != initial_refresh_token

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {refreshed_payload['tokens']['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "user@example.com"

    signout_response = client.post(
        "/auth/signout",
        json={"refresh_token": rotated_refresh_token},
    )
    assert signout_response.status_code == 200
    assert signout_response.json()["status"] == "signed_out"

    refresh_after_signout = client.post(
        "/auth/refresh",
        json={"refresh_token": rotated_refresh_token},
    )
    assert refresh_after_signout.status_code == 401
