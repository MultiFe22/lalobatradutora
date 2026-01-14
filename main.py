#!/usr/bin/env python3
"""
Loba - Live OBS Subtitle Application

Main entry point for the EN -> PT live subtitles for OBS.
"""

import asyncio
import signal
import sys
from pathlib import Path

from app.core import AppConfig, load_config, TranslateMode, create_clear_event
from app.server import OverlayServer


class LobaApp:
    """Main application orchestrator."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.mode = TranslateMode()
        self.server = OverlayServer(config.server)
        self._running = False

        # Set up mode change callback
        self.mode.set_callback(self._on_mode_change)

    async def start(self) -> None:
        """Start the application."""
        print("Starting Loba - Live Subtitles for OBS")
        print(f"Server will run at http://{self.config.server.host}:{self.config.server.port}")

        self._running = True

        # Start the overlay server
        await self.server.start()

        # Keep running until stopped
        while self._running:
            await asyncio.sleep(0.1)

    async def stop(self) -> None:
        """Stop the application."""
        print("\nShutting down...")
        self._running = False
        await self.server.stop()

    def _on_mode_change(self, state) -> None:
        """Handle mode state changes."""
        if not state.value == "on":
            # Broadcast clear when turned off
            asyncio.create_task(self.server.broadcast_clear())


async def main():
    """Main entry point."""
    config = load_config()
    app = LobaApp(config)

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def signal_handler():
        asyncio.create_task(app.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await app.start()
    except KeyboardInterrupt:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
