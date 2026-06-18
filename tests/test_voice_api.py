"""Voice transcribe API tests."""


import base64

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SKILLOS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SKILLOS_LEGACY_MODE", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    import skillos.db as db_mod
    db_mod._local.conns = {}
    from skillos.api.server import app
    return TestClient(app)


class TestVoiceTranscribe:
    def test_returns_501_without_openai_key(self, client):
        r = client.post(
            "/voice/transcribe",
            json={"audio": base64.b64encode(b"RIFF").decode()},
        )
        assert r.status_code == 501
        assert "语音识别" in r.json()["detail"]
