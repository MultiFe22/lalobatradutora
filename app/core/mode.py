"""Translate mode state machine."""

from dataclasses import dataclass
from typing import Callable, Optional
from enum import Enum


class ModeState(Enum):
    """Possible states for translate mode."""
    OFF = "off"
    ON = "on"


@dataclass
class TranslateMode:
    """
    State machine for translate mode toggle.

    When OFF: do not show subtitles (clear overlay)
    When ON: translate + show subtitles
    """
    _state: ModeState = ModeState.OFF
    _on_change: Optional[Callable[[ModeState], None]] = None

    @property
    def enabled(self) -> bool:
        """Check if translate mode is enabled."""
        return self._state == ModeState.ON

    @property
    def state(self) -> ModeState:
        """Get current state."""
        return self._state

    def set_callback(self, callback: Callable[[ModeState], None]) -> None:
        """Set callback to be called on state change."""
        self._on_change = callback

    def toggle(self) -> ModeState:
        """Toggle between ON and OFF states."""
        if self._state == ModeState.OFF:
            self._state = ModeState.ON
        else:
            self._state = ModeState.OFF

        if self._on_change:
            self._on_change(self._state)

        return self._state

    def turn_on(self) -> None:
        """Explicitly turn on translate mode."""
        if self._state != ModeState.ON:
            self._state = ModeState.ON
            if self._on_change:
                self._on_change(self._state)

    def turn_off(self) -> None:
        """Explicitly turn off translate mode."""
        if self._state != ModeState.OFF:
            self._state = ModeState.OFF
            if self._on_change:
                self._on_change(self._state)
