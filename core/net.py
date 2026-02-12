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


def _is_wide_char(cp: int) -> bool:
    """Return True if the Unicode code point occupies 2 terminal columns (CJK/Hangul)."""
    return (
        (0x1100 <= cp <= 0x115F)    # Hangul Jamo
        or (0x2E80 <= cp <= 0x9FFF)  # CJK Radicals..CJK Unified Ideographs
        or (0xAC00 <= cp <= 0xD7AF)  # Hangul Syllables
        or (0xF900 <= cp <= 0xFAFF)  # CJK Compatibility Ideographs
        or (0xFE30 <= cp <= 0xFE4F)  # CJK Compatibility Forms
        or (0xFF01 <= cp <= 0xFF60)  # Fullwidth Forms
        or (0x20000 <= cp <= 0x2FA1F)  # CJK Ext-B..Kangxi supplement
    )


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
        self._line_buf = bytearray()  # server-side line editing buffer

    async def send(self, text: str) -> None:
        """Send text to client."""
        if self.closed:
            return
        try:
            # Telnet requires \r\n line endings; normalize \n → \r\n
            text = text.replace("\r\n", "\n").replace("\n", "\r\n")
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

    def _erase_last_char(self) -> bytes:
        """Remove last UTF-8 character from _line_buf and return erase sequence."""
        if not self._line_buf:
            return b""
        # Find start of last UTF-8 character
        idx = len(self._line_buf) - 1
        while idx > 0 and (self._line_buf[idx] & 0xC0) == 0x80:
            idx -= 1
        removed = bytes(self._line_buf[idx:])
        del self._line_buf[idx:]
        # Determine display width
        try:
            ch = removed.decode("utf-8")
            width = 2 if (len(ch) == 1 and _is_wide_char(ord(ch))) else 1
        except UnicodeDecodeError:
            width = 1
        return b"\b \b" * width

    async def read_loop(self) -> None:
        """Read data from client byte-by-byte, handle server-side echo and line editing."""
        while not self.closed:
            try:
                data = await self.reader.read(4096)
                if not data:
                    self.closed = True
                    break
            except (ConnectionResetError, asyncio.CancelledError):
                self.closed = True
                break

            # Strip Telnet IAC sequences and collect clean bytes
            i = 0
            clean = bytearray()
            while i < len(data):
                if data[i] == IAC and i + 1 < len(data):
                    cmd = data[i + 1]
                    if cmd in (DO, DONT, WILL, WONT) and i + 2 < len(data):
                        opt = data[i + 2]
                        if cmd == DO:
                            if opt in (SGA, ECHO):
                                pass  # Already sent WILL SGA/ECHO
                            else:
                                self.writer.write(bytes([IAC, WONT, opt]))
                        elif cmd == WILL:
                            if opt == NAWS:
                                self.writer.write(bytes([IAC, DO, opt]))
                            else:
                                self.writer.write(bytes([IAC, DONT, opt]))
                        i += 3
                        continue
                    elif cmd == SB:
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

            # Flush IAC responses
            try:
                await self.writer.drain()
            except (ConnectionResetError, BrokenPipeError, OSError):
                self.closed = True
                break

            # Process each clean byte: server-side line editing
            for b in clean:
                if b == 0:
                    continue  # ignore null
                if b in (8, 127):  # BS or DEL
                    if self._line_buf:
                        erase = self._erase_last_char()
                        if self._echo and erase:
                            self.writer.write(erase)
                    # Empty buffer → ignore (prompt protection)
                    continue
                if b == ord("\r"):
                    continue  # wait for \n
                if b == ord("\n"):
                    # Complete line
                    if self._echo:
                        self.writer.write(b"\r\n")
                    line_bytes = bytes(self._line_buf)
                    self._line_buf.clear()
                    try:
                        text = line_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        try:
                            text = line_bytes.decode("euc-kr")
                        except UnicodeDecodeError:
                            text = line_bytes.decode("latin-1")
                    await self._input_queue.put(text)
                    continue
                # Regular byte — append to buffer and echo
                self._line_buf.append(b)
                if self._echo:
                    self.writer.write(bytes([b]))

            # Flush echo output
            try:
                await self.writer.drain()
            except (ConnectionResetError, BrokenPipeError, OSError):
                self.closed = True
                break

    async def set_echo(self, enabled: bool) -> None:
        """Toggle server-side echo (disable for password prompts)."""
        self._echo = enabled

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
            # Negotiate: suppress go-ahead + server-side echo
            writer.write(bytes([IAC, WILL, SGA, IAC, WILL, ECHO]))
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
