"""Tests for hot reload manager."""

import sys
import types
import pytest
from core.reload import ReloadManager


class TestReloadManager:
    def test_queue_reload(self):
        mgr = ReloadManager()
        mgr.queue_reload("some.module")
        assert "some.module" in mgr._pending

    def test_no_duplicates(self):
        mgr = ReloadManager()
        mgr.queue_reload("some.module")
        mgr.queue_reload("some.module")
        assert mgr._pending.count("some.module") == 1

    def test_apply_pending_empty(self):
        mgr = ReloadManager()
        result = mgr.apply_pending()
        assert result == []

    def test_apply_pending_loaded_module(self):
        """Reload an actual importable module (core.ansi)."""
        mgr = ReloadManager()
        import core.ansi  # ensure loaded
        mgr.queue_reload("core.ansi")
        result = mgr.apply_pending()
        assert "core.ansi" in result

    def test_apply_pending_not_loaded(self):
        mgr = ReloadManager()
        mgr.queue_reload("nonexistent.module.xyz")
        result = mgr.apply_pending()
        assert result == []  # skipped

    def test_queue_game_reload(self):
        mgr = ReloadManager()
        # Create fake game modules
        mod1 = types.ModuleType("games.test.commands")
        mod2 = types.ModuleType("games.test.combat")
        sys.modules["games.test.commands"] = mod1
        sys.modules["games.test.combat"] = mod2
        try:
            mgr.queue_game_reload("test")
            assert "games.test.commands" in mgr._pending
            assert "games.test.combat" in mgr._pending
        finally:
            del sys.modules["games.test.commands"]
            del sys.modules["games.test.combat"]
