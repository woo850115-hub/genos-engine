"""Network layer — Telnet server with asyncio."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine

log = logging.getLogger(__name__)

# Telnet IAC commands
IAC = 255
DONT = 254
DO = 253
WONT = 252
WILL = 251
SB = 250
SE = 240
ECHO = 1
SGA = 3  # Suppress Go-Ahead
NAWS = 31  # Negotiate About Window Size
CHARSET = 42


class TelnetConnection:
    """A single Telnet client connection."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        conn_id: int,
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.id = conn_id
        self.addr = writer.get_extra_info("peername")
        self.closed = False
        self._input_queue: asyncio.Queue[str] = asyncio.Queue()
        self._echo = True

    async def send(self, text: str) -> None:
        """Send text to client."""
        if self.closed:
            return
        try:
            self.writer.write(text.encode("utf-8"))
            await self.writer.drain()
        except (ConnectionResetError, BrokenPipeError, OSError):
            self.closed = True

    async def send_line(self, text: str) -> None:
        await self.send(text + "\r\n")

    async def get_input(self) -> str:
        """Get next input line (blocks until available)."""
        return await self._input_queue.get()

    def has_input(self) -> bool:
        return not self._input_queue.empty()

    async def read_loop(self) -> None:
        """Read data from client, strip IAC, queue lines."""
        buf = b""
        while not self.closed:
            try:
                data = await self.reader.read(4096)
                if not data:
                    self.closed = True
                    break
            except (ConnectionResetError, asyncio.CancelledError):
                self.closed = True
                break

            # Strip Telnet IAC sequences
            i = 0
            clean = bytearray()
            while i < len(data):
                if data[i] == IAC and i + 1 < len(data):
                    cmd = data[i + 1]
                    if cmd in (DO, DONT, WILL, WONT) and i + 2 < len(data):
                        i += 3
                        continue
                    elif cmd == SB:
                        # Skip to SE
                        end = data.find(bytes([IAC, SE]), i)
                        if end != -1:
                            i = end + 2
                        else:
                            i = len(data)
                        continue
                    elif cmd == IAC:
                        clean.append(IAC)
                        i += 2
                        continue
                    else:
                        i += 2
                        continue
                clean.append(data[i])
                i += 1

            buf += bytes(clean)

            # Process complete lines
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.rstrip(b"\r")
                try:
                    text = line.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        text = line.decode("euc-kr")
                    except UnicodeDecodeError:
                        text = line.decode("latin-1")
                await self._input_queue.put(text)

    async def set_echo(self, enabled: bool) -> None:
        """Toggle Telnet echo (for password prompts)."""
        if enabled and not self._echo:
            self.writer.write(bytes([IAC, WONT, ECHO]))
            await self.writer.drain()
            self._echo = True
        elif not enabled and self._echo:
            self.writer.write(bytes([IAC, WILL, ECHO]))
            await self.writer.drain()
            self._echo = False

    async def close(self) -> None:
        self.closed = True
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except (OSError, ConnectionError):
            pass


OnConnectCallback = Callable[[TelnetConnection], Coroutine[Any, Any, None]]


class TelnetServer:
    """Async Telnet server."""

    def __init__(self, host: str, port: int, on_connect: OnConnectCallback) -> None:
        self.host = host
        self.port = port
        self._on_connect = on_connect
        self._server: asyncio.Server | None = None
        self._next_id = 0
        self._connections: dict[int, TelnetConnection] = {}

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port,
        )
        log.info("Telnet server listening on %s:%d", self.host, self.port)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        for conn in list(self._connections.values()):
            await conn.close()
        self._connections.clear()
        log.info("Telnet server stopped")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self._next_id += 1
        conn = TelnetConnection(reader, writer, self._next_id)
        self._connections[conn.id] = conn
        addr = conn.addr
        log.info("New connection #%d from %s", conn.id, addr)

        try:
            # Negotiate: suppress go-ahead, request charset
            writer.write(bytes([IAC, WILL, SGA]))
            await writer.drain()

            # Start read loop in background
            read_task = asyncio.create_task(conn.read_loop())

            # Hand off to session manager
            await self._on_connect(conn)

            # Wait for read loop to finish
            await read_task
        except Exception:
            log.exception("Error handling connection #%d", conn.id)
        finally:
            self._connections.pop(conn.id, None)
            await conn.close()
            log.info("Connection #%d from %s closed", conn.id, addr)

    @property
    def connection_count(self) -> int:
        return len(self._connections)
