"""SkillOS Configuration — model providers, API keys, app settings.

Hermes-compatible: reads from ~/.hermes/config.yaml first, falls back to .env.
This allows SkillOS to share model credentials with Hermes without duplication.
"""

import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env from SkillOS root
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)

_log = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Unified app configuration with validation."""
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    vision_model: str = "deepseek-v4-flash"
    thinking: str = "disabled"
    reasoning_effort: str = "high"
    extra: dict[str, Any] = field(default_factory=dict)

    # Role-based model selection (Harness-Updating vs Harness-Benefit)
    evolver_model: str = ""
    executor_model: str = ""
    # Background knowledge maintenance (refresher on by default; watcher opt-in)
    enable_periodic_refresh: bool = True
    enable_file_watcher: bool = False
    refresh_interval_hours: float = 24.0
    watcher_poll_interval: float = 3.0

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load from environment with optional Hermes config override.

        Priority: SKILLOS_* env > DEEPSEEK_* env > Hermes config > Ollama local
        """
        # Try Hermes config first
        hermes_config = _load_hermes_config()
        if hermes_config:
            provider = hermes_config.get("model", {}).get("provider", "")
            model_name = hermes_config.get("model", {}).get("name", "")
            if provider and model_name:
                _log.info("Using Hermes model config: %s/%s", provider, model_name)

        # Cloud API key
        api_key = os.getenv("DEEPSEEK_API_KEY") or hermes_config.get("api_key", "")
        if not api_key:
            api_key = os.getenv("HUOSHAN_API_KEY", "")
        if not api_key:
            api_key = "ollama"  # Local mode marker

        # Base URL — support Ollama local
        base_url = os.getenv("SKILLOS_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL", "")
        if not base_url:
            if os.getenv("HUOSHAN_API_KEY") and not os.getenv("DEEPSEEK_API_KEY"):
                base_url = os.getenv("HUOSHAN_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
            elif api_key == "ollama":
                base_url = "http://localhost:11434/v1"
            else:
                base_url = "https://api.deepseek.com"

        # Model — support Ollama local models
        model = os.getenv("SKILLOS_MODEL") or os.getenv("DEEPSEEK_MODEL") or os.getenv("LLM_MODEL", "")
        if not model:
            model = "llama3.2" if api_key == "ollama" else "deepseek-v4-flash"

        def _env_bool(name: str, default: bool = False) -> bool:
            raw = os.getenv(name)
            if raw is None or raw.strip() == "":
                return default
            return raw.strip().lower() in ("1", "true", "yes", "on")

        disable_refresh = _env_bool("SKILLOS_DISABLE_REFRESH")
        refresh_explicit = os.getenv("SKILLOS_ENABLE_REFRESH", "").strip()
        if disable_refresh:
            enable_refresh = False
        elif refresh_explicit:
            enable_refresh = _env_bool("SKILLOS_ENABLE_REFRESH")
        else:
            enable_refresh = True

        return cls(
            api_key=api_key.strip() if api_key and api_key != "ollama" else "ollama",
            base_url=base_url.rstrip("/"),
            model=model,
            vision_model=os.getenv("DEEPSEEK_VISION_MODEL", os.getenv("VISION_MODEL", model)),
            thinking=os.getenv("DEEPSEEK_THINKING", "disabled"),
            reasoning_effort=os.getenv("DEEPSEEK_REASONING_EFFORT", "high"),
            evolver_model=os.getenv("SKILLOS_EVOLVER_MODEL", ""),
            executor_model=os.getenv("SKILLOS_EXECUTOR_MODEL", ""),
            enable_periodic_refresh=enable_refresh,
            enable_file_watcher=_env_bool("SKILLOS_ENABLE_WATCHER"),
            refresh_interval_hours=float(os.getenv("SKILLOS_REFRESH_INTERVAL_HOURS", "24")),
            watcher_poll_interval=float(os.getenv("SKILLOS_WATCHER_INTERVAL", "3")),
        )


    def get_model_for_role(self, role: str = "executor") -> str:
        """Harness-Updating (evolver) can use cheap models. 
        Harness-Benefit (executor) needs capable models."""
        if role == "evolver" and self.evolver_model:
            return self.evolver_model
        if role == "executor" and self.executor_model:
            return self.executor_model
        return self.model

    def validate(self) -> list[str]:
        issues = []
        if not self.api_key:
            issues.append("DEEPSEEK_API_KEY is not set")
        if not self.base_url:
            issues.append("base_url is empty")
        return issues

    def to_llm_args(self) -> tuple[str, str, str, dict]:
        """Convert to legacy (api_key, base_url, model, chat_kwargs) tuple."""
        kwargs = {}
        if self.thinking == "enabled":
            kwargs["extra_body"] = {
                "thinking": {"type": "enabled"},
                "reasoning_effort": self.reasoning_effort,
            }
        else:
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        return (self.api_key, self.base_url, self.model, kwargs)


# ── Singleton ────────────────────────────────────────────────

_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig.from_env()
    return _config


def reset_config() -> None:
    """Clear config singleton (for tests / env reload)."""
    global _config
    _config = None


def _load_hermes_config() -> dict:
    """Load Hermes config if available (shared credentials)."""
    try:
        hermes_yaml = Path.home() / ".hermes" / "config.yaml"
        if hermes_yaml.exists():
            import yaml
            return yaml.safe_load(hermes_yaml.read_text()) or {}
    except Exception:
        pass
    return {}


# Settings keys exposed to UI
SETTING_KEYS = [
    "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL",
    "HUOSHAN_API_KEY", "HUOSHAN_BASE_URL", "HUOSHAN_MODEL",
    "SKILLOS_MODEL", "SKILLOS_EVOLVER_MODEL", "SKILLOS_EXECUTOR_MODEL",
    "DEEPSEEK_THINKING", "DEEPSEEK_REASONING_EFFORT",
]


def get_settings() -> dict[str, str]:
    """Read current config values for settings UI."""
    return {key: os.getenv(key, "") or "" for key in SETTING_KEYS}


_settings_lock = threading.Lock()


def save_settings(values: dict[str, str]) -> None:
    """Write config values back to .env and reload. Thread-safe."""
    with _settings_lock:
        existing: dict[str, str] = {}
        if _env_path.exists():
            for line in _env_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, val = stripped.split("=", 1)
                existing[key.strip()] = val.strip()
        existing.update({k: v for k, v in values.items() if k in SETTING_KEYS})
        lines = [f"{key}={existing.get(key, '')}" for key in SETTING_KEYS]
        _env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        load_dotenv(_env_path, override=True)
        for key, val in existing.items():
            if val:
                os.environ[key] = val
            elif key in os.environ:
                del os.environ[key]
