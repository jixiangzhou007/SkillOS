"""Tests for config and LLM client modules."""

from skillos.config import AppConfig


def test_config_from_env():
    """Config should load without crashing even if .env is missing keys."""
    cfg = AppConfig.from_env()
    assert hasattr(cfg, "api_key")
    assert hasattr(cfg, "model")
    assert isinstance(cfg.validate(), list)


def test_config_to_llm_args():
    """Legacy tuple format should be backward-compatible."""
    cfg = AppConfig(api_key="sk-test", base_url="https://test.com", model="test-model")
    args = cfg.to_llm_args()
    assert len(args) == 4
    assert args[0] == "sk-test"
    assert args[2] == "test-model"


def test_config_singleton():
    """get_config() should return the same instance."""
    from skillos.config import get_config
    c1 = get_config()
    c2 = get_config()
    assert c1 is c2
