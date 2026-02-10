"""Hot reload manager — reload games/ modules at tick boundaries."""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class ReloadManager:
    """Queue and apply module reloads at safe tick boundaries."""

    def __init__(self) -> None:
        self._pending: list[str] = []  # module names to reload

    def queue_reload(self, module_name: str) -> None:
        """Queue a module for reload at next tick boundary."""
        if module_name not in self._pending:
            self._pending.append(module_name)
            log.info("Queued reload: %s", module_name)

    def apply_pending(self) -> list[str]:
        """Apply all queued reloads. Returns list of reloaded modules."""
        reloaded = []
        while self._pending:
            mod_name = self._pending.pop(0)
            try:
                if mod_name in sys.modules:
                    mod = sys.modules[mod_name]
                    importlib.reload(mod)
                    reloaded.append(mod_name)
                    log.info("Reloaded: %s", mod_name)
                else:
                    log.warning("Module not loaded, skipping: %s", mod_name)
            except Exception:
                log.exception("Failed to reload: %s", mod_name)
        return reloaded

    def queue_game_reload(self, game_name: str) -> None:
        """Queue all modules under games/{game_name}/ for reload."""
        prefix = f"games.{game_name}."
        for mod_name in sorted(sys.modules):
            if mod_name.startswith(prefix):
                self.queue_reload(mod_name)
