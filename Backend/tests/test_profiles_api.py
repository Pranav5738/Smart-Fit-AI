from __future__ import annotations

from fastapi.testclient import TestClient


def test_profile_crud_endpoints(client: TestClient) -> None:
    create_response = client.post("/profiles/", json={"name": "Primary Profile"})
    assert create_response.status_code == 201

    profile = create_response.json()
    profile_id = profile["id"]
    assert profile["name"] == "Primary Profile"

    list_response = client.get("/profiles/")
    assert list_response.status_code == 200
    listed_profiles = list_response.json()
    assert any(item["id"] == profile_id for item in listed_profiles)

    get_response = client.get(f"/profiles/{profile_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == profile_id

    history_response = client.get(f"/profiles/{profile_id}/history")
    assert history_response.status_code == 200
    assert history_response.json() == []

    trends_response = client.get(f"/profiles/{profile_id}/trends")
    assert trends_response.status_code == 200
    assert trends_response.json()["profile_id"] == profile_id

    delete_response = client.delete(f"/profiles/{profile_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

    missing_profile_response = client.get(f"/profiles/{profile_id}")
    assert missing_profile_response.status_code == 404
    assert missing_profile_response.json()["error_code"] == "PROFILE_NOT_FOUND"
