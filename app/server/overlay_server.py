"""HTTP + WebSocket server for OBS overlay."""

import asyncio
import json
from pathlib import Path
from typing import Set, Optional
import mimetypes

from ..core.events import SubtitleEvent, create_clear_event
from ..core.config import ServerConfig


class OverlayServer:
    """
    HTTP + WebSocket server for OBS Browser Source overlay.

    Endpoints:
    - GET /overlay - Overlay HTML page for OBS
    - GET /control - Control page with toggle button
    - WS  /ws      - WebSocket for real-time subtitle events
    """

    def __init__(
        self,
        config: ServerConfig,
        ui_path: Optional[Path] = None,
    ):
        self.config = config
        self.ui_path = ui_path or Path(__file__).parent.parent / "ui"
        self._clients: Set[asyncio.StreamWriter] = set()
        self._ws_clients: Set = set()
        self._server = None
        self._running = False

    async def start(self) -> None:
        """Start the HTTP/WebSocket server."""
        try:
            from aiohttp import web

            app = web.Application()
            app.router.add_get("/", self._handle_index)
            app.router.add_get("/overlay", self._handle_overlay)
            app.router.add_get("/control", self._handle_control)
            app.router.add_get("/ws", self._handle_websocket)
            app.router.add_static("/static", self.ui_path)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, self.config.host, self.config.port)
            await site.start()
            self._running = True
            print(f"Server running at http://{self.config.host}:{self.config.port}")
            print(f"OBS Browser Source URL: http://{self.config.host}:{self.config.port}/overlay")

        except ImportError:
            raise RuntimeError("aiohttp is required for the server")

    async def stop(self) -> None:
        """Stop the server."""
        self._running = False
        # Close all WebSocket connections
        for ws in list(self._ws_clients):
            await ws.close()
        self._ws_clients.clear()

    async def broadcast(self, event: SubtitleEvent) -> None:
        """Broadcast subtitle event to all connected clients."""
        message = event.to_json()
        disconnected = set()

        for ws in self._ws_clients:
            try:
                await ws.send_str(message)
            except Exception:
                disconnected.add(ws)

        self._ws_clients -= disconnected

    async def broadcast_clear(self) -> None:
        """Broadcast clear event (when toggle off)."""
        await self.broadcast(create_clear_event())

    async def _handle_index(self, request) -> "web.Response":
        """Redirect to overlay."""
        from aiohttp import web
        raise web.HTTPFound("/overlay")

    async def _handle_overlay(self, request) -> "web.Response":
        """Serve overlay HTML."""
        from aiohttp import web
        return await self._serve_file("overlay.html", request)

    async def _handle_control(self, request) -> "web.Response":
        """Serve control page HTML."""
        from aiohttp import web
        return await self._serve_file("control.html", request)

    async def _serve_file(self, filename: str, request) -> "web.Response":
        """Serve a static file from ui_path."""
        from aiohttp import web
        file_path = self.ui_path / filename
        if not file_path.exists():
            raise web.HTTPNotFound()
        content_type, _ = mimetypes.guess_type(str(file_path))
        return web.FileResponse(file_path, headers={
            "Content-Type": content_type or "text/html"
        })

    async def _handle_websocket(self, request) -> "web.WebSocketResponse":
        """Handle WebSocket connection."""
        from aiohttp import web
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self._ws_clients.add(ws)
        print(f"WebSocket client connected ({len(self._ws_clients)} total)")

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    # Handle incoming messages (e.g., toggle commands)
                    await self._handle_ws_message(msg.data, ws)
                elif msg.type == web.WSMsgType.ERROR:
                    print(f"WebSocket error: {ws.exception()}")
        finally:
            self._ws_clients.discard(ws)
            print(f"WebSocket client disconnected ({len(self._ws_clients)} total)")

        return ws

    async def _handle_ws_message(self, data: str, ws) -> None:
        """Handle incoming WebSocket message."""
        try:
            msg = json.loads(data)
            msg_type = msg.get("type")

            if msg_type == "toggle":
                # Emit toggle event (to be handled by main app)
                pass
            elif msg_type == "ping":
                await ws.send_str(json.dumps({"type": "pong"}))

        except json.JSONDecodeError:
            pass

    @property
    def client_count(self) -> int:
        """Number of connected WebSocket clients."""
        return len(self._ws_clients)

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running
