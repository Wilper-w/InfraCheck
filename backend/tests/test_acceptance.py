"""Acceptance tests covering CONTRACT §4 + execution engine (CONTRACT §6)."""
from __future__ import annotations


# ---------------- auth (CONTRACT §4 /auth) ----------------
class TestAuth:
    def test_login_returns_token_and_account(self, client):
        resp = client.post("/api/auth/login", json={"account": "zhangsan"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["account"] == "zhangsan"
        assert isinstance(data["token"], str) and len(data["token"]) > 0

    def test_login_empty_account_rejected(self, client):
        resp = client.post("/api/auth/login", json={"account": "  "})
        assert resp.status_code == 400

    def test_unauthorized_access_returns_401(self, client):
        # no Authorization header at all
        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 401
        assert resp.json()["detail"]

    def test_invalid_token_returns_401(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
        assert resp.status_code == 401

    def test_me_with_valid_token(self, client, auth_headers):
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["account"] == "zhangsan"


# ---------------- seed data (CONTRACT §5) ----------------
class TestSeed:
    def test_five_environments_seeded(self, client, auth_headers):
        resp = client.get("/api/environments", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        flavors = {e["os_flavor"] for e in data["items"]}
        assert "ubuntu" in flavors and "centos" in flavors

    def test_nodes_seeded(self, client, auth_headers):
        # env-01 should have 4 nodes
        resp = client.get("/api/environments/1/nodes", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 4

    def test_services_seeded(self, client, auth_headers):
        resp = client.get("/api/environments/1/services", headers=auth_headers)
        assert resp.status_code == 200
        names = {s["name"] for s in resp.json()["items"]}
        assert {"nginx", "keepalived", "mysql", "haproxy"} <= names

    def test_check_items_seeded(self, client, auth_headers):
        resp = client.get("/api/check-items", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 4

    def test_clusters_namespaces_pods_seeded(self, client, auth_headers):
        # env-01 clusters
        resp = client.get("/api/environments/1/clusters", headers=auth_headers)
        assert resp.json()["total"] >= 1
        cluster_id = resp.json()["items"][0]["id"]
        ns_resp = client.get(f"/api/clusters/{cluster_id}/namespaces", headers=auth_headers)
        assert ns_resp.json()["total"] >= 1
        ns_id = ns_resp.json()["items"][0]["id"]
        pod_resp = client.get(f"/api/namespaces/{ns_id}/pods", headers=auth_headers)
        assert pod_resp.json()["total"] >= 1


# ---------------- pagination (CONTRACT §2) ----------------
class TestPagination:
    def test_list_returns_pagination_shape(self, client, auth_headers):
        resp = client.get("/api/environments?page=1&page_size=3", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {"items", "total", "page", "page_size"}
        assert data["page"] == 1
        assert data["page_size"] == 3
        assert len(data["items"]) <= 3

    def test_second_page(self, client, auth_headers):
        resp = client.get("/api/environments?page=2&page_size=3", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["page"] == 2


# ---------------- run trigger + execution engine (CONTRACT §6) ----------------
class TestRunExecution:
    def test_trigger_dryrun_run_finishes(self, client, auth_headers):
        resp = client.post("/api/runs/trigger", json={"scope": "all"}, headers=auth_headers)
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]
        assert isinstance(run_id, int)

        detail = client.get(f"/api/runs/{run_id}", headers=auth_headers).json()
        assert detail["status"] == "finished"
        assert detail["trigger"] == "manual"
        assert detail["triggered_by"] == "zhangsan"

    def test_results_cover_four_states(self, client, auth_headers):
        # trigger a run, then verify all four statuses appear in results
        run_id = client.post(
            "/api/runs/trigger", json={"scope": "all"}, headers=auth_headers
        ).json()["run_id"]

        all_results = []
        for page in range(1, 20):
            resp = client.get(
                f"/api/runs/{run_id}/results?page={page}&page_size=200", headers=auth_headers
            )
            data = resp.json()
            all_results.extend(data["items"])
            if len(all_results) >= data["total"] or not data["items"]:
                break

        statuses = {r["status"] for r in all_results}
        assert {"normal", "abnormal", "unreachable", "failed"} <= statuses, (
            f"missing states; got {statuses}"
        )

    def test_results_have_evidence(self, client, auth_headers):
        run_id = client.post(
            "/api/runs/trigger", json={"scope": "all"}, headers=auth_headers
        ).json()["run_id"]
        resp = client.get(f"/api/runs/{run_id}/results?page=1&page_size=5", headers=auth_headers)
        for item in resp.json()["items"]:
            assert item["evidence"], "evidence must not be empty"

    def test_results_filter_by_status(self, client, auth_headers):
        run_id = client.post(
            "/api/runs/trigger", json={"scope": "all"}, headers=auth_headers
        ).json()["run_id"]
        resp = client.get(
            f"/api/runs/{run_id}/results?status=abnormal&page=1&page_size=50",
            headers=auth_headers,
        )
        for item in resp.json()["items"]:
            assert item["status"] == "abnormal"

    def test_trigger_scope_environment(self, client, auth_headers):
        resp = client.post(
            "/api/runs/trigger",
            json={"scope": "environment", "environment_id": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_trigger_missing_env_id_rejected(self, client, auth_headers):
        resp = client.post(
            "/api/runs/trigger", json={"scope": "environment"}, headers=auth_headers
        )
        assert resp.status_code == 400


# ---------------- reports (CONTRACT §4 /reports) ----------------
class TestReports:
    def test_report_generated_after_run(self, client, auth_headers):
        run_id = client.post(
            "/api/runs/trigger", json={"scope": "all"}, headers=auth_headers
        ).json()["run_id"]

        reports = client.get("/api/reports", headers=auth_headers).json()["items"]
        assert reports, "at least one report should exist"
        report = next((r for r in reports if r["run_id"] == run_id), None)
        assert report is not None, "report for the run should exist"

        html = client.get(f"/api/reports/{report['id']}/html", headers=auth_headers)
        assert html.status_code == 200
        assert "<html" in html.text.lower() or "<!doctype" in html.text.lower()
        assert str(run_id) in html.text

        md = client.get(f"/api/reports/{report['id']}/markdown", headers=auth_headers)
        assert md.status_code == 200
        assert "InfraCheck" in md.text
        assert "巡检报告" in md.text


# ---------------- audit (CONTRACT §4 /audit, §6) ----------------
class TestAudit:
    def test_audit_records_trigger_and_report(self, client, auth_headers):
        client.post("/api/runs/trigger", json={"scope": "all"}, headers=auth_headers)
        resp = client.get("/api/audit", headers=auth_headers)
        assert resp.status_code == 200
        actions = {a["action"] for a in resp.json()["items"]}
        assert "run.trigger" in actions
        assert "report.generate" in actions

    def test_audit_actor_from_jwt(self, client, auth_headers):
        client.post("/api/runs/trigger", json={"scope": "all"}, headers=auth_headers)
        resp = client.get("/api/audit?actor=zhangsan", headers=auth_headers)
        for item in resp.json()["items"]:
            assert item["actor"] == "zhangsan"


# ---------------- dashboard (CONTRACT §4 /dashboard) ----------------
class TestDashboard:
    def test_summary_shape(self, client, auth_headers):
        # trigger a run first so summary has data
        client.post("/api/runs/trigger", json={"scope": "all"}, headers=auth_headers)
        resp = client.get("/api/dashboard/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) >= {
            "generated_at", "total", "normal", "abnormal", "unreachable", "failed", "environments"
        }
        assert data["total"] > 0
        assert len(data["environments"]) == 5

    def test_trend(self, client, auth_headers):
        resp = client.get("/api/dashboard/trend?days=7", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["series"]) == 7
        assert set(data["series"][0].keys()) == {"date", "normal", "abnormal", "unreachable", "failed"}


# ---------------- environment summary (CONTRACT §4) ----------------
class TestEnvironmentSummary:
    def test_summary_after_run(self, client, auth_headers):
        client.post("/api/runs/trigger", json={"scope": "all"}, headers=auth_headers)
        resp = client.get("/api/environments/1/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {
            "environment_id", "environment_name", "os_flavor", "total", "normal",
            "abnormal", "unreachable", "failed",
        }
        assert data["environment_id"] == 1

    def test_summary_empty_returns_zeros(self, client, auth_headers):
        # a brand new environment with no run results → all zeros
        create = client.post(
            "/api/environments",
            json={"name": "env-empty", "os_flavor": "ubuntu", "description": "test"},
            headers=auth_headers,
        )
        env_id = create.json()["id"]
        resp = client.get(f"/api/environments/{env_id}/summary", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 0
        assert data["normal"] == 0


# ---------------- check item CRUD (CONTRACT §4) ----------------
class TestCheckItems:
    def test_toggle(self, client, auth_headers):
        items = client.get("/api/check-items", headers=auth_headers).json()["items"]
        item_id = items[0]["id"]
        before = items[0]["enabled"]
        resp = client.post(f"/api/check-items/{item_id}/toggle", headers=auth_headers)
        assert resp.json()["enabled"] == (not before)

    def test_filter_by_target_type(self, client, auth_headers):
        resp = client.get("/api/check-items?target_type=pod", headers=auth_headers)
        for item in resp.json()["items"]:
            assert item["target_type"] == "pod"
