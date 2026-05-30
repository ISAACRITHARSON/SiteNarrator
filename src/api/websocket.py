"""SiteNarrator — WebSocket connection manager.

Handles real-time notifications for:
- PC: draft ready, escalation alerts, aging drafts
- Superintendent: report approved confirmation
- Ops: client Q&A escalations
- Client: chat messages
"""

from __future__ import annotations

from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections by user role and ID."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        """Accept and register a WebSocket connection to a channel."""
        await websocket.accept()
        if channel not in self._connections:
            self._connections[channel] = []
        self._connections[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        """Remove a WebSocket connection from a channel."""
        if channel in self._connections:
            self._connections[channel] = [
                ws for ws in self._connections[channel] if ws != websocket
            ]

    async def send_to_channel(self, channel: str, message: dict[str, Any]):
        """Send a message to all connections on a channel."""
        if channel not in self._connections:
            return
        disconnected = []
        for ws in self._connections[channel]:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws, channel)

    async def broadcast(self, message: dict[str, Any]):
        """Send a message to ALL connected clients."""
        for channel in self._connections:
            await self.send_to_channel(channel, message)


# Singleton instance
manager = ConnectionManager()
