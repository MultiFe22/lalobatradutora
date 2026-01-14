"""Global hotkey handler for cross-platform support (Windows/macOS)."""

from typing import Callable, Optional
import threading


class HotkeyHandler:
    """
    Cross-platform global hotkey handler using pynput.

    Listens for F11 key to toggle translation mode.
    Works on both Windows and macOS.
    """

    def __init__(self, on_toggle: Optional[Callable[[], None]] = None):
        self.on_toggle = on_toggle
        self._listener = None
        self._running = False

    def start(self) -> None:
        """Start listening for hotkey."""
        if self._running:
            return

        try:
            from pynput import keyboard

            def on_press(key):
                try:
                    # Check for F11 key
                    if key == keyboard.Key.f11:
                        if self.on_toggle:
                            self.on_toggle()
                except AttributeError:
                    pass

            self._listener = keyboard.Listener(on_press=on_press)
            self._listener.start()
            self._running = True
            print("Global hotkey registered: F11 to toggle translation")

        except ImportError:
            print("Warning: pynput not installed, hotkey disabled")
            print("Install with: pip install pynput")
        except Exception as e:
            print(f"Warning: Could not register hotkey: {e}")
            print("On macOS, you may need to grant Accessibility permissions")

    def stop(self) -> None:
        """Stop listening for hotkey."""
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._running = False

    def set_callback(self, callback: Callable[[], None]) -> None:
        """Set the toggle callback."""
        self.on_toggle = callback

    @property
    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._running
