"""REST + WebSocket API — FastAPI single-port (8080)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from core.engine import Engine

log = logging.getLogger(__name__)

app = FastAPI(title="GenOS Engine API", version="0.1.0")

# Engine reference — set by start_api()
_engine: Engine | None = None


def get_engine() -> Engine:
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not ready")
    return _engine


# ── REST endpoints ────────────────────────────────────────────────

@app.get("/api/who")
async def api_who() -> JSONResponse:
    """List online players."""
    engine = get_engine()
    players = []
    for name, session in engine.players.items():
        if session.character:
            c = session.character
            players.append({
                "name": c.name,
                "level": c.level,
                "class_id": c.class_id,
                "room_vnum": c.room_vnum,
            })
    return JSONResponse({"players": players, "count": len(players)})


@app.get("/api/stats")
async def api_stats() -> JSONResponse:
    """Server statistics."""
    engine = get_engine()
    return JSONResponse({
        "game": engine.game_name,
        "uptime_ticks": engine._tick,
        "players_online": len(engine.players),
        "connections": len(engine.sessions),
        "rooms_loaded": len(engine.world.rooms),
        "mobs_loaded": len(engine.world.mob_protos),
        "objects_loaded": len(engine.world.item_protos),
        "zones": len(engine.world.zones),
        "commands_registered": len(engine.cmd_handlers),
    })


@app.post("/api/reload")
async def api_reload() -> JSONResponse:
    """Trigger hot reload of game modules."""
    engine = get_engine()
    engine.reload_mgr.queue_game_reload(engine.game_name)
    reloaded = engine.reload_mgr.apply_pending()
    if reloaded:
        engine._plugin.register_commands(engine)
        return JSONResponse({"status": "ok", "reloaded": reloaded})
    return JSONResponse({"status": "ok", "reloaded": []})


@app.get("/api/room/{vnum}")
async def api_room(vnum: int) -> JSONResponse:
    """Get room info by vnum."""
    engine = get_engine()
    room = engine.world.get_room(vnum)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    exits = []
    for ex in room.proto.exits:
        exits.append({
            "direction": ex.direction,
            "to_room": ex.to_room,
        })
    chars = []
    for ch in room.characters:
        chars.append({
            "id": ch.id,
            "name": ch.name,
            "is_npc": ch.is_npc,
            "level": ch.level,
        })
    return JSONResponse({
        "vnum": room.proto.vnum,
        "name": room.proto.name,
        "description": room.proto.description,
        "zone": room.proto.zone_number,
        "sector": room.proto.sector_type,
        "exits": exits,
        "characters": chars,
        "objects": len(room.objects),
    })


# ── WebSocket endpoint ────────────────────────────────────────────

class WebSocketSession:
    """Adapter: WebSocket → TelnetConnection-like interface for Session."""

    def __init__(self, ws: WebSocket, conn_id: int):
        self.ws = ws
        self.id = conn_id
        self.addr = ("ws", 0)
        self.closed = False
        self._input_queue: asyncio.Queue[str] = asyncio.Queue()

    async def send(self, text: str) -> None:
        if self.closed:
            return
        try:
            await self.ws.send_text(text)
        except Exception:
            self.closed = True

    async def send_line(self, text: str) -> None:
        await self.send(text + "\r\n")

    async def get_input(self) -> str:
        return await self._input_queue.get()

    def has_input(self) -> bool:
        return not self._input_queue.empty()

    async def set_echo(self, enabled: bool) -> None:
        pass  # WebSocket doesn't need echo control

    async def close(self) -> None:
        self.closed = True
        try:
            await self.ws.close()
        except Exception:
            pass


_ws_id_counter = 0


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """WebSocket game client endpoint."""
    global _ws_id_counter
    engine = get_engine()

    await ws.accept()
    _ws_id_counter += 1
    ws_conn = WebSocketSession(ws, 100000 + _ws_id_counter)

    log.info("WebSocket connection #%d", ws_conn.id)

    from core.session import Session

    session = Session(ws_conn, engine)

    # Run session in background
    session_task = asyncio.create_task(session.run())

    try:
        while not ws_conn.closed:
            data = await ws.receive_text()
            await ws_conn._input_queue.put(data)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.debug("WebSocket #%d error", ws_conn.id)
    finally:
        ws_conn.closed = True
        session_task.cancel()
        log.info("WebSocket connection #%d closed", ws_conn.id)


# ── Server start/stop ──────────────────────────────────────────────

_server_task: asyncio.Task | None = None


async def start_api(engine: Engine, host: str = "0.0.0.0", port: int = 8080) -> None:
    """Start FastAPI server in background."""
    global _engine, _server_task
    _engine = engine

    import uvicorn

    config = uvicorn.Config(
        app, host=host, port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    _server_task = asyncio.create_task(server.serve())
    log.info("API server starting on %s:%d", host, port)


async def stop_api() -> None:
    """Stop FastAPI server."""
    global _server_task
    if _server_task:
        _server_task.cancel()
        try:
            await _server_task
        except asyncio.CancelledError:
            pass
        _server_task = None
    log.info("API server stopped")
