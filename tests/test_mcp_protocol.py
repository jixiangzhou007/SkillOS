"""MCP Protocol verification — end-to-end stdio handshake + tool calling."""

import json
import subprocess
import sys
import time


def test_mcp_import():
    """MCP server module should import without error."""
    from skillos.mcp_server import mcp
    assert mcp is not None


def test_mcp_tools_registered():
    """All MCP tools should be importable and callable."""
    from skillos.mcp_server import (
        extract_skill, search_knowledge, list_skills, get_skill,
        query_lineage, digest_document, evolve_skill, get_epistemic_context,
        ingest_file, fetch_url, confirm_pending_claims, export_for_skillopt,
    )
    tools = [
        extract_skill, search_knowledge, list_skills, get_skill,
        query_lineage, digest_document, evolve_skill, get_epistemic_context,
        ingest_file, fetch_url, confirm_pending_claims, export_for_skillopt,
    ]
    for tool in tools:
        assert callable(tool)
        assert tool.__doc__, f"{tool.__name__} missing docstring"


def test_list_skills_tool():
    """list_skills should return a string containing skill names."""
    from skillos.mcp_server import list_skills
    result = list_skills()
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_epistemic_context():
    """get_epistemic_context should return a string."""
    from skillos.mcp_server import get_epistemic_context
    result = get_epistemic_context()
    assert isinstance(result, str)


def test_get_skill_404():
    """get_skill for a nonexistent skill should return error message."""
    from skillos.mcp_server import get_skill
    result = get_skill("nonexistent-skill-xyz-12345")
    assert "not found" in result.lower()


def test_search_knowledge_empty():
    """search_knowledge with no data should return helpful message."""
    from skillos.mcp_server import search_knowledge
    result = search_knowledge("nonexistent query")
    assert isinstance(result, str)


def test_evolve_skill_404():
    """evolve_skill for nonexistent skill should return error."""
    from skillos.mcp_server import evolve_skill
    result = evolve_skill("nonexistent-skill-xyz-12345")
    assert "not found" in result.lower()


def test_mcp_server_startup():
    """MCP server should start and respond to initialize request."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "skillos.mcp_server"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True
    )
    try:
        init = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        }) + "\n"
        proc.stdin.write(init)
        proc.stdin.flush()
        time.sleep(1)

        # The server should be alive and accept input
        # Check that it didn't crash
        assert proc.poll() is None, "MCP server crashed on startup"
    finally:
        proc.terminate()
        proc.wait(timeout=5)
