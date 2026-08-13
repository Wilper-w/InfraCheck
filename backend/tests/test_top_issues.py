"""Tests for the dashboard top-issues endpoint."""
from __future__ import annotations


class TestTopIssues:
    def test_requires_auth(self, client):
        assert client.get("/api/dashboard/top-issues").status_code == 401

    def test_returns_issues_after_run(self, client, auth_headers):
        # Trigger a run first so results exist
        r = client.post("/api/runs/trigger", json={"scope": "all"}, headers=auth_headers)
        assert r.status_code == 200

        r2 = client.get("/api/dashboard/top-issues?limit=5", headers=auth_headers)
        assert r2.status_code == 200
        issues = r2.json()
        assert isinstance(issues, list)
        assert len(issues) <= 5
        if issues:
            issue = issues[0]
            assert issue["status"] in ("abnormal", "unreachable", "failed")
            assert "object_name" in issue
            assert "environment_name" in issue
            assert "evidence" in issue
            assert "captured_at" in issue

    def test_limit_validation(self, client, auth_headers):
        r = client.get("/api/dashboard/top-issues?limit=0", headers=auth_headers)
        assert r.status_code == 422
