"""
websocket_manager.py - WebSocket connection manager.

Keeps track of all connected browser clients and broadcasts
diagnosis events to all of them whenever a new one arrives.

Simple list of active connections - no Redis, no pub/sub,
just in-memory. Fine for a single-server setup.
"""

import json
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        # List of currently connected WebSocket clients.
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        """Send a diagnosis event to every connected browser tab."""
        message = json.dumps(data)
        # Iterate over a copy in case a client disconnects mid-broadcast.
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


# Single shared instance used by both main.py and consumer.py.
manager = WebSocketManager()