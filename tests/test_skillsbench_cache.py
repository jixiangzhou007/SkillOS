"""SkillsBench LLM cache tests."""

from skillos.skillsbench_cache import cache_key, get_cached_response, store_cached_response


def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("SKILLSBENCH_LLM_CACHE", "1")
    import skillos.skillsbench_cache as mod

    monkeypatch.setattr(mod, "CACHE_DIR", tmp_path)
    assert get_cached_response(model="m", system="sys", user="u") is None
    store_cached_response(model="m", system="sys", user="u", text="hello")
    assert get_cached_response(model="m", system="sys", user="u") == "hello"


def test_cache_key_stable():
    a = cache_key(model="m", system="s", user="u")
    b = cache_key(model="m", system="s", user="u")
    assert a == b
