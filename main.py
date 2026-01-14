#!/usr/bin/env python3
"""
Loba - Live OBS Subtitle Application

Main entry point for the EN -> PT live subtitles for OBS.
Phase 1: Local transcription only (English captions).
"""

import asyncio
import signal
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from app.core import AppConfig, load_config, TranslateMode, ModeState
from app.core.events import create_final_event, create_clear_event
from app.core.segmenter import Segmenter, AudioSegment
from app.adapters.audio_mic import MicrophoneCapture
from app.adapters.whisper_runner import WhisperRunner
from app.adapters.translator import PassthroughTranslator
from app.server import OverlayServer


class LobaApp:
    """Main application orchestrator."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.mode = TranslateMode()

        # Components
        self.server = OverlayServer(config.server)
        self.mic = MicrophoneCapture(
            sample_rate=config.audio.sample_rate,
            channels=config.audio.channels,
            chunk_duration_ms=config.audio.chunk_duration_ms,
        )
        self.segmenter = Segmenter(config.segmenter)
        self.whisper = WhisperRunner(config.whisper)
        self.translator = PassthroughTranslator()  # Phase 1: no translation

        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._loop: asyncio.AbstractEventLoop | None = None

        # Set up callbacks
        self.mode.set_callback(self._on_mode_change)
        self.mic.set_callback(self._on_audio_chunk)

    async def start(self) -> None:
        """Start the application."""
        print("=" * 50)
        print("Loba - Live Subtitles for OBS")
        print("=" * 50)

        # Check whisper availability
        if not self.whisper.is_available():
            print(f"\nERROR: Whisper not available!")
            print(f"  Binary: {self.whisper.binary_path} (exists: {self.whisper.binary_path.exists()})")
            print(f"  Model: {self.whisper.model_path} (exists: {self.whisper.model_path.exists()})")
            return

        print(f"\nWhisper: {self.whisper.binary_path}")
        print(f"Model: {self.whisper.model_path}")
        print(f"Server: http://{self.config.server.host}:{self.config.server.port}")
        print(f"\nOBS Browser Source URL:")
        print(f"  http://{self.config.server.host}:{self.config.server.port}/overlay")
        print(f"\nControl Panel:")
        print(f"  http://{self.config.server.host}:{self.config.server.port}/control")
        print("\n" + "=" * 50)

        self._running = True
        self._loop = asyncio.get_running_loop()

        # Start server
        await self.server.start()

        # List available microphones
        devices = self.mic.list_devices()
        if devices:
            print("\nAvailable microphones:")
            for d in devices:
                print(f"  [{d.index}] {d.name}")
            print()

        # Start microphone capture (uses default device)
        try:
            self.mic.start()
            print("Microphone capture started")
            print("Speak to see transcriptions in the overlay!")
            print("Press Ctrl+C to stop\n")
        except Exception as e:
            print(f"Failed to start microphone: {e}")
            print("Make sure sounddevice is installed: pip install sounddevice")
            return

        # Enable translation mode by default for Phase 1
        self.mode.turn_on()

        # Main loop
        while self._running:
            await asyncio.sleep(0.1)

    async def stop(self) -> None:
        """Stop the application."""
        print("\nShutting down...")
        self._running = False

        # Stop microphone
        self.mic.stop()

        # Finalize any pending segment
        segment = self.segmenter.force_finalize()
        if segment:
            await self._process_segment(segment)

        # Stop server
        await self.server.stop()

        # Shutdown executor
        self._executor.shutdown(wait=False)

        print("Goodbye!")

    def _on_mode_change(self, state: ModeState) -> None:
        """Handle mode state changes."""
        print(f"Mode changed to: {state.value}")
        if state == ModeState.OFF:
            # Clear overlay when turned off
            if self._loop:
                self._loop.call_soon_threadsafe(
                    self._loop.create_task, self.server.broadcast_clear()
                )
            # Reset segmenter
            self.segmenter.reset()

    def _on_audio_chunk(self, audio_data: bytes) -> None:
        """Handle incoming audio chunk from microphone."""
        if not self.mode.enabled or not self._loop:
            return

        # Process through segmenter (includes VAD)
        segment = self.segmenter.process_chunk(audio_data)

        if segment:
            # Process segment in background (thread-safe)
            self._loop.call_soon_threadsafe(
                self._loop.create_task, self._process_segment(segment)
            )

    async def _process_segment(self, segment: AudioSegment) -> None:
        """Process a finalized audio segment."""
        if not segment.data:
            return

        duration_s = len(segment.data) / (self.config.audio.sample_rate * 2)
        print(f"Processing segment ({duration_s:.1f}s)...")

        try:
            # Run whisper in thread pool to avoid blocking
            result = await asyncio.get_running_loop().run_in_executor(
                self._executor,
                self.whisper.transcribe,
                segment.data,
                self.config.audio.sample_rate,
            )

            text = result.text.strip()

            if text:
                # Phase 1: No translation, just pass through
                translated = self.translator.translate(text)
                print(f"  > {translated.translated_text}")

                # Broadcast to overlay
                event = create_final_event(translated.translated_text, language="en")
                await self.server.broadcast(event)
            else:
                print("  (no speech detected)")

        except Exception as e:
            print(f"  Error: {e}")


async def main():
    """Main entry point."""
    # Use paths relative to script location
    script_dir = Path(__file__).parent.absolute()

    config = load_config()
    # Update paths to be absolute
    config.whisper.binary_path = script_dir / config.whisper.binary_path
    config.whisper.model_path = script_dir / config.whisper.model_path

    app = LobaApp(config)

    # Handle shutdown signals
    loop = asyncio.get_running_loop()

    def signal_handler():
        loop.create_task(app.stop())

    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

    try:
        await app.start()
    except KeyboardInterrupt:
        await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
