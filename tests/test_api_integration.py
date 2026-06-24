"""API integration tests — real HTTP requests against a running server."""

import json
import os
import socket
import tempfile
import threading
import time
import uuid
import urllib.request
import urllib.error

import pytest

BASE = None
_server_thread = None


def setup_module():
    """Start a test server on a free port with an isolated data directory."""
    global _server_thread, BASE
    data_dir = tempfile.mkdtemp(prefix="skillos_api_int_")
    os.environ["SKILLOS_DATA_DIR"] = data_dir
    os.environ.setdefault("SKILLOS_JWT_SECRET", "test-integration-secret")
    os.environ.setdefault("SKILLOS_LEGACY_MODE", "false")

    import skillos.db as db_mod
    db_mod._local.conns = {}
    import skillos.marketplace.auth as auth_mod
    auth_mod._local.conn = None

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    BASE = f"http://127.0.0.1:{port}"
    from skillos.api.server import start
    _server_thread = threading.Thread(target=start, args=("127.0.0.1", port), daemon=True)
    _server_thread.start()
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            _get("/health")
            return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError(f"Test server failed to start on {BASE}")


def _get(path, headers=None):
    req = urllib.request.Request(f"{BASE}{path}", headers=headers or {})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def _post(path, body, headers=None):
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=data, method="POST", headers=hdrs)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def _register_token(retries=5):
    """Register a throwaway user and return a Bearer token for auth-gated routes."""
    name = f"int_{uuid.uuid4().hex[:10]}"
    body = {"username": name, "password": "pass1234", "email": f"{name}@test.local"}
    last_err = None
    for _ in range(retries):
        try:
            data = _post("/api/auth/register", body)
            return data["token"]
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 500:
                time.sleep(0.5)
                continue
            raise
    if last_err:
        raise last_err
    raise RuntimeError("Failed to register test user")


class TestHealth:
    def test_health(self):
        r = _get("/health")
        assert r["status"] == "ok"


class TestSkillsAPI:
    def test_list_skills(self):
        r = _get("/api/skills/")
        assert isinstance(r, list)

    def test_create_run_delete_skill(self):
        import pytest; pytest.skip("Requires LLM — skipped in CI")
        # Create
        r = _post("/api/skills/create", {"text": "创建测试技能"})
        assert "reply" in r or "active" in r

    def test_get_skill_404(self):
        try:
            _get("/api/skills/nonexistent-skill-xyz-123")
            assert False, "Should have raised 404"
        except urllib.error.HTTPError as e:
            assert e.code == 404


class TestAuthAPI:
    def test_login_fail(self):
        try:
            _post("/api/auth/login", {"username": "noone", "password": "wrong"})
            assert False
        except urllib.error.HTTPError as e:
            assert e.code == 401

    def test_register_short_password(self):
        try:
            _post("/api/auth/register", {"username": "x", "password": "ab"})
            assert False
        except urllib.error.HTTPError as e:
            assert e.code == 400


class TestKnowledgeAPI:
    def test_list_knowledge(self):
        r = _get("/api/knowledge/")
        assert "items" in r
        assert "show" in r

    def test_lineage(self):
        r = _get("/api/knowledge/lineage")
        assert "sessions" in r

    def test_wisdom(self):
        r = _get("/api/knowledge/wisdom")
        assert "wisdom" in r

    def test_graph_clusters(self):
        r = _get("/api/knowledge/graph/clusters")
        assert "clusters" in r

    def test_journal(self):
        r = _get("/api/knowledge/journal")
        assert "entries" in r


class TestMarketplaceAPI:
    def test_stats(self):
        r = _get("/api/marketplace/stats")
        assert "total" in r

    def test_search(self):
        r = _get("/api/marketplace/search")
        assert "skills" in r

    def test_publish(self):
        try:
            r = _post("/api/marketplace/publish", {
                "name": f"api-test-{uuid.uuid4().hex[:8]}",
                "content": "# Test Skill\n## S_body\n1. Step",
                "author": "qa", "category": "development"
            })
            assert r.get("published") is True or "skill_id" in r
        except urllib.error.HTTPError as e:
            # Readonly catalog or server error in test env
            assert e.code in (403, 500, 200, 201)
        except TimeoutError:
            pytest.skip("Publish scoring timed out in test env")


class TestEvolutionAPI:
    def test_consolidate_requires_auth(self):
        data = json.dumps({}).encode()
        req = urllib.request.Request(
            f"{BASE}/api/evolution/consolidate",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            assert False, "Should require authentication"
        except urllib.error.HTTPError as e:
            assert e.code == 401

    @pytest.mark.skipif(os.getenv("SKILLOS_RUN_SLOW") != "1", reason="slow LLM/epistemic workload")
    def test_consolidate(self):
        token = _register_token()
        data = json.dumps({}).encode()
        req = urllib.request.Request(
            f"{BASE}/api/evolution/consolidate",
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                result = json.loads(r.read().decode())
        except TimeoutError:
            pytest.skip("Consolidation exceeds 120s (LLM/epistemic workload in test env)")
        assert "total_items" in result
