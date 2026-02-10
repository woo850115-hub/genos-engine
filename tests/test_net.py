"""Tests for network layer — Telnet IAC handling, TelnetConnection."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.net import TelnetConnection, IAC, DO, WILL, SGA, SE, SB


class TestTelnetConnection:
    @pytest.fixture
    def mock_conn(self):
        reader = AsyncMock(spec=asyncio.StreamReader)
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.get_extra_info = MagicMock(return_value=("127.0.0.1", 12345))
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        return TelnetConnection(reader, writer, 1)

    def test_init(self, mock_conn):
        assert mock_conn.id == 1
        assert mock_conn.closed is False
        assert mock_conn.addr == ("127.0.0.1", 12345)

    @pytest.mark.asyncio
    async def test_send(self, mock_conn):
        await mock_conn.send("hello")
        mock_conn.writer.write.assert_called_once_with(b"hello")

    @pytest.mark.asyncio
    async def test_send_line(self, mock_conn):
        await mock_conn.send_line("hello")
        mock_conn.writer.write.assert_called_once_with(b"hello\r\n")

    @pytest.mark.asyncio
    async def test_send_closed(self, mock_conn):
        mock_conn.closed = True
        await mock_conn.send("hello")
        mock_conn.writer.write.assert_not_called()

    @pytest.mark.asyncio
    async def test_close(self, mock_conn):
        await mock_conn.close()
        assert mock_conn.closed is True

    @pytest.mark.asyncio
    async def test_input_queue(self, mock_conn):
        await mock_conn._input_queue.put("test command")
        assert mock_conn.has_input() is True
        result = await mock_conn.get_input()
        assert result == "test command"
        assert mock_conn.has_input() is False

    @pytest.mark.asyncio
    async def test_set_echo_off(self, mock_conn):
        """Disabling echo sends IAC WILL ECHO."""
        await mock_conn.set_echo(False)
        mock_conn.writer.write.assert_called_with(bytes([IAC, WILL, 1]))

    @pytest.mark.asyncio
    async def test_set_echo_on(self, mock_conn):
        """Re-enabling echo sends IAC WONT ECHO."""
        mock_conn._echo = False
        await mock_conn.set_echo(True)
        mock_conn.writer.write.assert_called_with(bytes([IAC, 252, 1]))
