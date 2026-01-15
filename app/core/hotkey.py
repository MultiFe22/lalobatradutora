"""Global hotkey handler for cross-platform support (Windows/macOS)."""

from typing import Callable, Optional
import threading


class HotkeyHandler:
    """
    Cross-platform global hotkey handler using pynput.

    Listens for configurable hotkey to toggle translation mode.
    Works on both Windows and macOS.
    Supports function keys F1-F12.
    """

    def __init__(self, on_toggle: Optional[Callable[[], None]] = None, hotkey: str = "f11"):
        self.on_toggle = on_toggle
        self.hotkey = hotkey.lower()  # Normalize to lowercase
        self._target_key = None  # Will be set when listener starts
        self._listener = None
        self._running = False

    def _get_key(self, key_name: str):
        """Convert string key name to pynput Key object."""
        try:
            from pynput import keyboard

            # Map string names to keyboard.Key attributes
            key_map = {
                "f1": keyboard.Key.f1,
                "f2": keyboard.Key.f2,
                "f3": keyboard.Key.f3,
                "f4": keyboard.Key.f4,
                "f5": keyboard.Key.f5,
                "f6": keyboard.Key.f6,
                "f7": keyboard.Key.f7,
                "f8": keyboard.Key.f8,
                "f9": keyboard.Key.f9,
                "f10": keyboard.Key.f10,
                "f11": keyboard.Key.f11,
                "f12": keyboard.Key.f12,
            }

            return key_map.get(key_name.lower(), keyboard.Key.f11)
        except ImportError:
            return None

    def start(self) -> None:
        """Start listening for hotkey."""
        if self._running:
            return

        try:
            from pynput import keyboard

            # Set the initial target key
            self._target_key = self._get_key(self.hotkey)

            def on_press(key):
                try:
                    # Check against current target key (allows dynamic updates)
                    if key == self._target_key:
                        if self.on_toggle:
                            self.on_toggle()
                except AttributeError:
                    pass

            self._listener = keyboard.Listener(on_press=on_press)
            self._listener.start()
            self._running = True
            print(f"Global hotkey registered: {self.hotkey.upper()} to toggle translation")

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

    def set_hotkey(self, hotkey: str) -> None:
        """Update the hotkey dynamically without restarting the listener."""
        self.hotkey = hotkey.lower()
        if self._running:
            # Update the target key that the listener checks against
            self._target_key = self._get_key(self.hotkey)
            print(f"Hotkey updated to: {self.hotkey.upper()}")

    @property
    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._running
