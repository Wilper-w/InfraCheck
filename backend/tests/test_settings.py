"""Tests for the auto-inspection scheduler (time-point) settings API."""
from __future__ import annotations


class TestAutoInspection:
    def test_get_requires_auth(self, client):
        assert client.get("/api/settings/auto-inspection").status_code == 401

    def test_get_returns_state(self, client, auth_headers):
        r = client.get("/api/settings/auto-inspection", headers=auth_headers)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["enabled"], bool)
        assert isinstance(d["schedules"], list)
        assert isinstance(d["next_run_times"], list)
        assert "last_scheduled_run_at" in d

    def test_add_multiple_time_points(self, client, auth_headers):
        body = {
            "enabled": True,
            "schedules": [{"time": "08:00", "days": []}, {"time": "22:00", "days": []}],
        }
        r = client.put("/api/settings/auto-inspection", json=body, headers=auth_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["enabled"] is True
        assert [s["time"] for s in d["schedules"]] == ["08:00", "22:00"]
        assert len(d["next_run_times"]) == 2

        ar = client.get("/api/audit?page_size=50", headers=auth_headers)
        assert any(x["action"] == "scheduler.update" for x in ar.json()["items"])

    def test_invalid_time_rejected(self, client, auth_headers):
        r = client.put(
            "/api/settings/auto-inspection",
            json={"schedules": [{"time": "99:00", "days": []}]},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_invalid_days_rejected(self, client, auth_headers):
        r = client.put(
            "/api/settings/auto-inspection",
            json={"schedules": [{"time": "08:00", "days": [9]}]},
            headers=auth_headers,
        )
        assert r.status_code == 422
