"""P0 — async knowledge cycle tasks + API polling."""

import time
from pathlib import Path
from unittest.mock import patch

import pytest


class TestCycleTasks:
    def test_submit_and_complete(self, tmp_path, monkeypatch):
        tasks_dir = tmp_path / "cycle_tasks"
        monkeypatch.setattr("skillos.knowledge.cycle_tasks.TASKS_DIR", tasks_dir)

        mock_result = {
            "session_id": "cycle_task_1",
            "lineage": {"lineage_applied": True},
            "elapsed_s": 0.1,
        }

        with patch(
            "skillos.knowledge.ingest_pipeline.run_full_knowledge_cycle",
            return_value=mock_result,
        ):
            from skillos.knowledge.cycle_tasks import get_cycle_task, submit_cycle_task

            task = submit_cycle_task("x" * 400, "https://task.test/doc", ("k", "u", "m", {}))
            assert task.status == "pending"
            assert task.task_id.startswith("kc_")

            deadline = time.time() + 5
            final = None
            while time.time() < deadline:
                final = get_cycle_task(task.task_id)
                if final and final.status in ("completed", "failed"):
                    break
                time.sleep(0.05)

            assert final is not None
            assert final.status == "completed"
            assert final.result["session_id"] == "cycle_task_1"
            assert (tasks_dir / f"{task.task_id}.json").exists()

    def test_submit_failure(self, tmp_path, monkeypatch):
        tasks_dir = tmp_path / "cycle_tasks"
        monkeypatch.setattr("skillos.knowledge.cycle_tasks.TASKS_DIR", tasks_dir)

        with patch(
            "skillos.knowledge.ingest_pipeline.run_full_knowledge_cycle",
            side_effect=RuntimeError("LLM down"),
        ):
            from skillos.knowledge.cycle_tasks import get_cycle_task, submit_cycle_task

            task = submit_cycle_task("body", "https://fail.test", ("k",))
            deadline = time.time() + 5
            final = None
            while time.time() < deadline:
                final = get_cycle_task(task.task_id)
                if final and final.status == "failed":
                    break
                time.sleep(0.05)

            assert final is not None
            assert final.status == "failed"
            assert "LLM down" in final.error


class TestKnowledgeCycleAPI:
    def test_post_cycle_returns_task_id(self):
        from fastapi.testclient import TestClient

        from skillos.api.server import app

        payload = {
            "content": "y" * 400 + "\nTermX: definition here\n",
            "source_url": "https://api-cycle.test/doc",
        }
        mock_result = {
            "session_id": "api_cycle_1",
            "source_title": "API Doc",
            "digest": {"glossary_terms": 1, "patterns": 0, "sections": 1, "cross_references": 0},
            "lineage": {"total_items": 2, "lineage_applied": True, "edges_created": 0},
            "graph_sync": {"synced": False},
            "affected_skills": [],
            "elapsed_s": 0.5,
        }

        with patch("skillos.config.get_config") as mock_cfg, \
             patch(
                 "skillos.knowledge.ingest_pipeline.run_full_knowledge_cycle",
                 return_value=mock_result,
             ):
            mock_cfg.return_value.to_llm_args.return_value = ("key", "url", "model", {})
            client = TestClient(app)
            resp = client.post("/api/knowledge/cycle", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"].startswith("kc_")
        assert data["status"] in ("pending", "running", "completed")
        assert data["poll_url"] == f"/api/knowledge/cycle/{data['task_id']}"

    def test_get_cycle_status_poll(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient

        from skillos.api.server import app

        tasks_dir = tmp_path / "cycle_tasks"
        monkeypatch.setattr("skillos.knowledge.cycle_tasks.TASKS_DIR", tasks_dir)

        mock_result = {
            "session_id": "api_cycle_poll",
            "lineage": {"lineage_applied": True},
        }

        payload = {"content": "z" * 400, "source_url": "https://poll.test/doc"}

        with patch("skillos.config.get_config") as mock_cfg, \
             patch(
                 "skillos.knowledge.ingest_pipeline.run_full_knowledge_cycle",
                 return_value=mock_result,
             ):
            mock_cfg.return_value.to_llm_args.return_value = ("key", "url", "model", {})
            client = TestClient(app)
            post = client.post("/api/knowledge/cycle", json=payload)
            task_id = post.json()["task_id"]

            deadline = time.time() + 5
            data = None
            while time.time() < deadline:
                resp = client.get(f"/api/knowledge/cycle/{task_id}")
                data = resp.json()
                if data.get("status") == "completed":
                    break
                time.sleep(0.05)

        assert data is not None
        assert data["status"] == "completed"
        assert data["session_id"] == "api_cycle_poll"
        assert data["result"]["lineage"]["lineage_applied"] is True

    def test_get_cycle_not_found(self):
        from fastapi.testclient import TestClient

        from skillos.api.server import app

        client = TestClient(app)
        resp = client.get("/api/knowledge/cycle/kc_nonexistent")
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_found"
