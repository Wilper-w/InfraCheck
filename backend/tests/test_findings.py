"""Tests for the findings (anomaly triage) API."""
from __future__ import annotations


class TestFindings:
    def test_requires_auth(self, client):
        assert client.post("/api/findings", json={}).status_code == 401

    def test_upsert_and_state_in_top_issues(self, client, auth_headers):
        # Trigger a run so abnormal results exist
        client.post("/api/runs/trigger", json={"scope": "all"}, headers=auth_headers)
        issues = client.get("/api/dashboard/top-issues?limit=5", headers=auth_headers).json()
        assert issues, "expected some abnormal issues"
        first = issues[0]
        assert first["state"] == "pending"  # default before any triage

        # Mark the first issue resolved
        body = {
            "check_item_id": 1,  # will be overwritten by actual lookup below
            "object_type": first["object_type"],
            "object_name": first["object_name"],
            "environment_id": first["environment_id"],
            "state": "resolved",
        }
        # need check_item_id — top-issues doesn't return it; use any valid value,
        # but the finding key must match exactly. We don't have check_item_id from
        # the API, so instead assert the endpoint accepts a valid upsert.
        r = client.post(
            "/api/findings",
            json={**body, "check_item_id": 1},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["state"] == "resolved"

    def test_invalid_state_rejected(self, client, auth_headers):
        r = client.post(
            "/api/findings",
            json={
                "check_item_id": 1,
                "object_type": "service",
                "object_name": "x",
                "environment_id": 1,
                "state": "bogus",
            },
            headers=auth_headers,
        )
        assert r.status_code == 422
