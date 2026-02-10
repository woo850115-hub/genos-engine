"""tbaMUD-KR Game Plugin — command registration and game-specific setup."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.engine import Engine


class TbaMudPlugin:
    """tbaMUD-KR game plugin."""

    name = "tbamud"

    def register_commands(self, engine: Engine) -> None:
        """Register tbaMUD-specific commands."""
        from games.tbamud.commands.info import register as reg_info
        from games.tbamud.commands.comm import register as reg_comm
        from games.tbamud.commands.items import register as reg_items
        from games.tbamud.commands.movement import register as reg_move
        from games.tbamud.commands.admin import register as reg_admin

        from games.tbamud.shops import register as reg_shops

        reg_info(engine)
        reg_comm(engine)
        reg_items(engine)
        reg_move(engine)
        reg_shops(engine)
        reg_admin(engine)


def create_plugin() -> TbaMudPlugin:
    return TbaMudPlugin()
