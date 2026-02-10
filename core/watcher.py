"""Dev-mode file watcher — auto-detect changes in games/ and queue reloads."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.reload import ReloadManager

log = logging.getLogger(__name__)


async def start_watcher(games_dir: Path, reload_mgr: ReloadManager) -> asyncio.Task:
    """Start watchfiles-based auto-reload for the games/ directory."""
    try:
        from watchfiles import awatch
    except ImportError:
        log.warning("watchfiles not installed — hot reload disabled")
        return asyncio.create_task(asyncio.sleep(0))

    async def _watch() -> None:
        log.info("File watcher started for %s", games_dir)
        async for changes in awatch(games_dir):
            for change_type, path_str in changes:
                path = Path(path_str)
                if path.suffix != ".py":
                    continue
                # Convert file path to module name
                # games/tbamud/commands/movement.py → games.tbamud.commands.movement
                try:
                    rel = path.relative_to(games_dir.parent)
                    mod_name = str(rel).replace("/", ".").removesuffix(".py")
                    if mod_name.endswith(".__init__"):
                        mod_name = mod_name.removesuffix(".__init__")
                    reload_mgr.queue_reload(mod_name)
                    log.debug("Change detected: %s → %s", path, mod_name)
                except ValueError:
                    pass

    task = asyncio.create_task(_watch())
    return task
