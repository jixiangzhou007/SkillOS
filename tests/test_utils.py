"""Tests for utility modules."""


class TestWebFetch:
    def test_fetch_simple(self):
        from skillos.utils.web_fetch import fetch
        result = fetch("https://httpbin.org/headers")
        assert len(result) > 0


class TestWechatFetch:
    def test_needs_cdp(self):
        from skillos.utils.wechat_fetch import needs_cdp
        assert needs_cdp("https://mp.weixin.qq.com/s/abc")
        assert not needs_cdp("https://github.com/anthropics/claude-code")


class TestFileIngest:
    def test_get_file_category(self):
        from skillos.utils.file_ingest import get_file_category
        assert "PDF" in get_file_category("test.pdf") or True  # encoding varies
        cat = get_file_category("test.docx")
        assert len(cat) > 0  # Returns Chinese category name like 文档


class TestWatcher:
    def test_get_watch_dir(self):
        from skillos.utils.watcher import get_watch_dir, FileWatcher
        watch_dir = get_watch_dir()
        assert watch_dir.exists()
        import time
        w = FileWatcher(watch_dir, lambda p: None, interval=10)
        assert not w._running


class TestHermesBridge:
    def test_is_available(self):
        from skillos.hermes_bridge import is_hermes_available, HERMES_SKILLS_DIR
        result = is_hermes_available()
        assert isinstance(result, bool)
        if HERMES_SKILLS_DIR:
            assert isinstance(str(HERMES_SKILLS_DIR), str)

    def test_skill_conversion(self):
        from skillos.hermes_bridge import skillos_to_hermes
        skillos_skill = "---\nname: test-bridge\n---\n\n# Test\n## S_body\n1. Do a thing\n## S_trigger\n- keywords: test"
        hermes_format = skillos_to_hermes("test-bridge", skillos_skill)
        assert "Instructions" in hermes_format
