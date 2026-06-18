"""Tool Registry — the missing third layer.

Knowledge = WHAT you know    (facts, concepts, heuristics)
Tools     = WHAT you can use  (MCP servers, APIs, functions)  ← this module
Skills    = HOW to do things  (procedures referencing tools)

Skills are operation manuals. Tools are the actual instruments.
A skill says "step 3: search for papers" — but it needs a tool to do it.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_log = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).parent / "knowledge" / "tools.json"


@dataclass
class Tool:
    """A registered, validated tool that skills can use."""

    name: str                      # unique kebab-case name
    description: str               # what it does
    tool_type: str = "builtin"     # builtin | mcp | api | function
    endpoint: str = ""             # MCP server name, API URL, or function path
    parameters: dict[str, Any] = field(default_factory=dict)  # JSON Schema for params
    validated: bool = False        # has been tested and confirmed working
    validation_result: str = ""    # result of last validation
    used_by: list[str] = field(default_factory=list)  # skills that depend on this
    created_at: float = 0.0
    last_validated: float = 0.0


class ToolRegistry:
    """Catalog of available tools — built-in, MCP, and custom."""

    def __init__(self) -> None:
        self.tools: dict[str, Tool] = {}
        self._load()
        self._register_builtins()

    def _load(self) -> None:
        if not REGISTRY_PATH.exists():
            return
        try:
            data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
            for t in data.get("tools", []):
                tool = Tool(
                    name=t["name"], description=t.get("description", ""),
                    tool_type=t.get("type", "builtin"), endpoint=t.get("endpoint", ""),
                    parameters=t.get("parameters", {}), validated=t.get("validated", False),
                    validation_result=t.get("validation_result", ""),
                    used_by=t.get("used_by", []), created_at=t.get("created_at", 0),
                    last_validated=t.get("last_validated", 0),
                )
                self.tools[tool.name] = tool
        except Exception as e:
            _log.warning("Failed to load tool registry: %s", e)

    def save(self) -> None:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "tools": [
                {
                    "name": t.name, "description": t.description,
                    "type": t.tool_type, "endpoint": t.endpoint,
                    "parameters": t.parameters, "validated": t.validated,
                    "validation_result": t.validation_result, "used_by": t.used_by,
                    "created_at": t.created_at, "last_validated": t.last_validated,
                }
                for t in self.tools.values()
            ]
        }
        REGISTRY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _register_builtins(self) -> None:
        """Register built-in tools that come with Skill Distiller."""
        builtins = [
            Tool(
                name="web_search", description="搜索互联网获取信息",
                tool_type="builtin", endpoint="web_search.search",
                parameters={"query": {"type": "string", "description": "搜索关键词"}},
                validated=True, created_at=time.time(),
            ),
            Tool(
                name="web_fetch", description="抓取网页内容",
                tool_type="builtin", endpoint="web_fetch.fetch",
                parameters={"url": {"type": "string", "description": "网页URL"}},
                validated=True, created_at=time.time(),
            ),
            Tool(
                name="read_file", description="读取本地文件内容",
                tool_type="builtin", endpoint="builtins.read_file",
                parameters={"path": {"type": "string", "description": "文件路径"}},
                validated=True, created_at=time.time(),
            ),
            Tool(
                name="skill_executor", description="执行一个已注册的技能",
                tool_type="builtin", endpoint="agent_factory.run_agent",
                parameters={"skill_name": {"type": "string"}, "task": {"type": "string"}},
                validated=True, created_at=time.time(),
            ),
        ]
        for tool in builtins:
            if tool.name not in self.tools:
                self.tools[tool.name] = tool
        self.save()

    # ── CRUD ──────────────────────────────────────────────────

    def register(self, name: str, description: str, tool_type: str = "api",
                 endpoint: str = "", parameters: dict | None = None) -> Tool:
        """Register a new tool."""
        tool = Tool(
            name=name, description=description, tool_type=tool_type,
            endpoint=endpoint, parameters=parameters or {},
            created_at=time.time(),
        )
        self.tools[name] = tool
        self.save()
        return tool

    def get(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def list_tools(self, tool_type: str = "") -> list[Tool]:
        """List tools, optionally filtered by type."""
        tools = list(self.tools.values())
        if tool_type:
            tools = [t for t in tools if t.tool_type == tool_type]
        return sorted(tools, key=lambda t: t.name)

    def delete(self, name: str) -> bool:
        if name in self.tools:
            del self.tools[name]
            self.save()
            return True
        return False

    # ── Validation ────────────────────────────────────────────

    def validate_tool(self, name: str) -> dict:
        """Test a tool to verify it works. Returns validation result."""
        tool = self.tools.get(name)
        if not tool:
            return {"valid": False, "error": f"Tool '{name}' not found"}

        if tool.tool_type == "builtin":
            # Built-in tools are pre-validated
            tool.validated = True
            tool.validation_result = "Built-in tool, pre-validated"
            tool.last_validated = time.time()
            self.save()
            return {"valid": True, "result": "Built-in tool (pre-validated)"}

        # For API/MCP tools, attempt a test call
        try:
            if tool.tool_type == "api" and tool.endpoint:
                import urllib.request
                r = urllib.request.urlopen(tool.endpoint, timeout=5)
                if r.status < 400:
                    tool.validated = True
                    tool.validation_result = f"API reachable: HTTP {r.status}"
                else:
                    tool.validated = False
                    tool.validation_result = f"API returned: HTTP {r.status}"
            else:
                tool.validated = True
                tool.validation_result = "Declared (no automated test)"
        except Exception as e:
            tool.validated = False
            tool.validation_result = f"Validation failed: {e}"

        tool.last_validated = time.time()
        self.save()
        return {"valid": tool.validated, "result": tool.validation_result}

    # ── Skill-tool binding ────────────────────────────────────

    def bind_skill_to_tool(self, skill_name: str, tool_name: str) -> None:
        """Record that a skill depends on a tool."""
        tool = self.tools.get(tool_name)
        if tool and skill_name not in tool.used_by:
            tool.used_by.append(skill_name)
            self.save()

    def get_skills_for_tool(self, tool_name: str) -> list[str]:
        """Which skills use this tool?"""
        tool = self.tools.get(tool_name)
        return tool.used_by if tool else []

    def get_tools_for_skill(self, skill_name: str) -> list[Tool]:
        """What tools does this skill need?"""
        return [t for t in self.tools.values() if skill_name in t.used_by]

    # ── Unified execution interface ────────────────────────────

    def call(self, tool_name: str, params: dict | None = None) -> dict:
        """Unified tool execution. Works for builtin, api, mcp, function types.

        Returns {"success": bool, "result": str, "error": str}
        """
        tool = self.tools.get(tool_name)
        if not tool:
            return {"success": False, "result": "", "error": f"Tool '{tool_name}' not registered"}

        if not tool.validated:
            return {"success": False, "result": "", "error": f"Tool '{tool_name}' is not validated. Run /tools/{tool_name}/validate first"}

        params = params or {}

        try:
            if tool.tool_type == "builtin":
                return self._call_builtin(tool, params)
            elif tool.tool_type == "api":
                return self._call_api(tool, params)
            elif tool.tool_type == "mcp":
                return self._call_mcp(tool, params)
            elif tool.tool_type == "function":
                return self._call_function(tool, params)
            else:
                return {"success": False, "result": "", "error": f"Unknown tool type: {tool.tool_type}"}
        except Exception as e:
            _log.warning("Tool '%s' execution failed: %s", tool_name, e)
            return {"success": False, "result": "", "error": str(e)}

    def _call_builtin(self, tool: Tool, params: dict) -> dict:
        """Execute a built-in tool."""
        if tool.name == "web_search":
            from skillos.utils.web_search import search
            query = params.get("query", "")
            result = search(query)
            return {"success": True, "result": result, "error": ""}

        elif tool.name == "web_fetch":
            from skillos.utils.web_fetch import fetch
            url = params.get("url", "")
            result = fetch(url)
            return {"success": True, "result": result or "", "error": ""}

        elif tool.name == "read_file":
            path = Path(params.get("path", ""))
            if not path.exists():
                return {"success": False, "result": "", "error": f"File not found: {path}"}
            result = path.read_text(encoding="utf-8")
            return {"success": True, "result": result[:5000], "error": ""}

        elif tool.name == "skill_executor":
            skill_name = params.get("skill_name", "")
            task = params.get("task", "")
            if not skill_name:
                return {"success": False, "result": "", "error": "Missing skill_name parameter"}
            from skillos.skills import agent_factory, skill_store
            try:
                skill_doc = skill_store.get_skill_body(skill_store.load_skill(skill_name))
                agent = agent_factory.create_agent(skill_doc, task)
                result = agent_factory.run_agent(agent, task)
                return {"success": True, "result": result or "", "error": ""}
            except Exception as e:
                return {"success": False, "result": "", "error": f"Skill execution failed: {e}"}

        return {"success": False, "result": "", "error": f"Unknown builtin: {tool.name}"}

    def _call_api(self, tool: Tool, params: dict) -> dict:
        """Execute an API-based tool."""
        import urllib.request, json as _json
        url = tool.endpoint
        if not url:
            return {"success": False, "result": "", "error": "No endpoint configured"}
        # Substitute params in URL template
        for k, v in params.items():
            url = url.replace(f"{{{k}}}", str(v))
        try:
            r = urllib.request.urlopen(url, timeout=10)
            result = r.read().decode("utf-8")
            return {"success": True, "result": result[:3000], "error": ""}
        except Exception as e:
            return {"success": False, "result": "", "error": str(e)}

    def _call_mcp(self, tool: Tool, params: dict) -> dict:
        """Execute an MCP tool."""
        # MCP integration: for now, return a clear message
        return {
            "success": False, "result": "",
            "error": f"MCP tool '{tool.name}' requires an MCP client. "
                     f"Server: {tool.endpoint}. Connect via Claude Code or MCP client to use."
        }

    def _call_function(self, tool: Tool, params: dict) -> dict:
        """Execute a Python function tool."""
        # Dynamic function import
        try:
            module_path, func_name = tool.endpoint.rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            result = func(**params)
            return {"success": True, "result": str(result)[:3000], "error": ""}
        except Exception as e:
            return {"success": False, "result": "", "error": str(e)}

    def check_skill_readiness(self, skill_name: str) -> dict:
        """Can this skill actually run? Checks all required tools are available."""
        required = self.get_tools_for_skill(skill_name)
        missing = [t.name for t in required if not t.validated]
        return {
            "ready": len(missing) == 0,
            "total_tools": len(required),
            "validated": len([t for t in required if t.validated]),
            "missing": missing,
        }


# Singleton
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
