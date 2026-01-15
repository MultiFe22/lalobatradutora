#!/usr/bin/env python3
"""
Loba - Live OBS Subtitle Application

Main entry point for the EN -> PT live subtitles for OBS.
Phase 3: Toggle mode with F11 global hotkey.
"""

import asyncio
import signal
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from app.core import AppConfig, load_config, TranslateMode, ModeState, HotkeyHandler
from app.core.events import create_final_event
from app.core.segmenter import Segmenter, AudioSegment
from app.adapters.audio_mic import MicrophoneCapture
from app.adapters.whisper_runner import WhisperRunner
from app.adapters.translator import M2M100Translator, CTranslate2Translator
from app.server import OverlayServer
from app.ui.settings_window import SettingsWindow, SettingsValues


class LobaApp:
    """Main application orchestrator."""

    def __init__(self, config: AppConfig, script_dir: Path):
        self.config = config
        self.mode = TranslateMode()
        self._script_dir = script_dir

        # Components
        self.server = OverlayServer(
            config.server,
            overlay_config=config.overlay,
        )
        self.mic = MicrophoneCapture(
            sample_rate=config.audio.sample_rate,
            channels=config.audio.channels,
            chunk_duration_ms=config.audio.chunk_duration_ms,
        )
        self.segmenter = Segmenter(config.segmenter)
        self.whisper = WhisperRunner(config.whisper)
        self.translator: CTranslate2Translator | None = None  # Lazy loaded

        # Translation model paths
        self._model_paths = {
            "marian": script_dir / "models" / "opus-mt-en-pt-ct2",
            "m2m100": script_dir / "models" / "m2m100-en-pt-br-ct2",
        }
        self._current_model: str = "none"
        self._available_models: list[str] = self._detect_available_models()

        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._loop: asyncio.AbstractEventLoop | None = None

        # Hotkey handler for F11 toggle
        self.hotkey = HotkeyHandler()

        # Settings window (created on start)
        self.settings_window: SettingsWindow | None = None

        # Set up callbacks
        self.mode.set_callback(self._on_mode_change)
        self.mic.set_callback(self._on_audio_chunk)
        self.hotkey.set_callback(self._on_hotkey_toggle)

    def _detect_available_models(self) -> list[str]:
        """Detect which translation models are available."""
        available = []
        for name, path in self._model_paths.items():
            if path.exists():
                available.append(name)
        available.append("none")  # Always allow disabling translation
        return available

    def set_translator(self, model_name: str) -> None:
        """Set the active translation model."""
        if model_name == "none":
            self.translator = None
            self._current_model = "none"
            print("[Settings] Translation disabled")
        elif model_name == "marian" and self._model_paths["marian"].exists():
            self.translator = CTranslate2Translator(model_path=str(self._model_paths["marian"]))
            self._current_model = "marian"
            print("[Settings] Switched to MarianMT (European Portuguese)")
        elif model_name == "m2m100" and self._model_paths["m2m100"].exists():
            self.translator = M2M100Translator(model_path=str(self._model_paths["m2m100"]))
            self._current_model = "m2m100"
            print("[Settings] Switched to M2M100 (Brazilian Portuguese)")

    def _on_settings_changed(self, values: SettingsValues) -> None:
        """Handle settings changes from the UI."""
        # Update overlay config
        self.config.overlay.subtitle_ttl_s = values.subtitle_ttl_s
        self.config.overlay.max_lines = values.max_lines

        # Update segmenter config
        self.config.segmenter.silence_threshold_ms = values.silence_threshold_ms

        # Update server's overlay config reference
        self.server.overlay_config = self.config.overlay

        # Switch translation model if changed
        if values.translation_model != self._current_model:
            self.set_translator(values.translation_model)
            # Pre-load the new model in background
            if self.translator and self._loop:
                self._loop.call_soon_threadsafe(
                    self._loop.create_task, self._preload_translator()
                )

    async def _preload_translator(self) -> None:
        """Pre-load the translator model in background."""
        if self.translator:
            print("Loading translation model...")
            await asyncio.get_running_loop().run_in_executor(
                self._executor,
                self.translator.load,
            )
            print("Translation model ready!")

    def _on_quit_requested(self) -> None:
        """Handle quit request from settings window."""
        if self._loop:
            self._loop.call_soon_threadsafe(
                self._loop.create_task, self.stop()
            )

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

        # Check translator availability
        if self.translator and not self.translator.is_available():
            print(f"\nERROR: Translation model not available!")
            print(f"  Path: {self.translator.model_path}")
            return

        print(f"\nWhisper: {self.whisper.binary_path}")
        print(f"Model: {self.whisper.model_path}")
        if self.translator:
            print(f"Translator: {self.translator.model_path}")
        print(f"Server: http://{self.config.server.host}:{self.config.server.port}")
        print(f"\nOBS Browser Source URL:")
        print(f"  http://{self.config.server.host}:{self.config.server.port}/overlay")
        print(f"\nControl Panel:")
        print(f"  http://{self.config.server.host}:{self.config.server.port}/control")
        print("\n" + "=" * 50)

        self._running = True
        self._loop = asyncio.get_running_loop()

        # Pre-load translation model for instant ready
        if self.translator:
            print("\nPre-loading translation model...")
            await asyncio.get_running_loop().run_in_executor(
                self._executor,
                self.translator.load,
            )
            print("Translation model ready!")

        # Start server
        await self.server.start()

        # Start hotkey listener
        self.hotkey.start()

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
        except Exception as e:
            print(f"Failed to start microphone: {e}")
            print("Make sure sounddevice is installed: pip install sounddevice")
            return

        # Start with translation OFF - user presses F11 to enable
        print("\n" + "=" * 50)
        print("Ready! Press F11 to start/stop translation")
        print("Use the Settings window to adjust or quit")
        print("=" * 50 + "\n")

        # Create settings window
        initial_settings = SettingsValues(
            subtitle_ttl_s=self.config.overlay.subtitle_ttl_s,
            max_lines=self.config.overlay.max_lines,
            silence_threshold_ms=self.config.segmenter.silence_threshold_ms,
            translation_model=self._current_model,
        )
        self.settings_window = SettingsWindow(
            initial_values=initial_settings,
            available_models=self._available_models,
            on_settings_changed=self._on_settings_changed,
            on_quit=self._on_quit_requested,
        )

        # Main loop - process tkinter events
        while self._running:
            if self.settings_window and self.settings_window.is_alive():
                self.settings_window.update()
            else:
                # Settings window was closed, quit the app
                break
            await asyncio.sleep(0.05)

        # Ensure proper shutdown if loop exited
        if self._running:
            await self.stop()

    async def stop(self) -> None:
        """Stop the application."""
        print("\nShutting down...")
        self._running = False

        # Stop hotkey listener
        self.hotkey.stop()

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

    def _on_hotkey_toggle(self) -> None:
        """Handle F11 hotkey press."""
        new_state = self.mode.toggle()
        status = "ON - Translating" if new_state == ModeState.ON else "OFF - Paused"
        print(f"\n[F11] Translation: {status}")

    def _on_mode_change(self, state: ModeState) -> None:
        """Handle mode state changes."""
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
                print(f"  EN: {text}")

                # Translate if translator is available
                if self.translator:
                    translated = await asyncio.get_running_loop().run_in_executor(
                        self._executor,
                        self.translator.translate,
                        text,
                    )
                    output_text = translated.translated_text
                    output_lang = "pt"
                    print(f"  PT: {output_text}")
                else:
                    output_text = text
                    output_lang = "en"

                # Broadcast to overlay
                event = create_final_event(output_text, language=output_lang)
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

    app = LobaApp(config, script_dir)

    # Set up default translator (prefer MarianMT for better accuracy)
    if "marian" in app._available_models:
        app.set_translator("marian")
    elif "m2m100" in app._available_models:
        app.set_translator("m2m100")
    else:
        print("No translation model found")
        print("Running in transcription-only mode (English)")

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
