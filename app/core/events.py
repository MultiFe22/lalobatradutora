"""Subtitle event schema for communication between components."""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional
import json
import time


class EventType(Enum):
    """Types of subtitle events."""
    PARTIAL = "partial"  # interim transcription (unstable)
    FINAL = "final"      # finalized transcription
    CLEAR = "clear"      # clear overlay (toggle off)


@dataclass
class SubtitleEvent:
    """Event sent to the overlay."""
    type: EventType
    text: str = ""
    timestamp: float = 0.0
    language: str = "en"

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_json(self) -> str:
        """Serialize event to JSON for WebSocket transmission."""
        return json.dumps({
            "type": self.type.value,
            "text": self.text,
            "timestamp": self.timestamp,
            "language": self.language,
        })

    @classmethod
    def from_json(cls, data: str) -> "SubtitleEvent":
        """Deserialize event from JSON."""
        obj = json.loads(data)
        return cls(
            type=EventType(obj["type"]),
            text=obj.get("text", ""),
            timestamp=obj.get("timestamp", 0.0),
            language=obj.get("language", "en"),
        )


def create_final_event(text: str, language: str = "pt") -> SubtitleEvent:
    """Create a final subtitle event (translated text)."""
    return SubtitleEvent(type=EventType.FINAL, text=text, language=language)


def create_partial_event(text: str) -> SubtitleEvent:
    """Create a partial subtitle event (interim transcription)."""
    return SubtitleEvent(type=EventType.PARTIAL, text=text, language="en")


def create_clear_event() -> SubtitleEvent:
    """Create a clear event (toggle off)."""
    return SubtitleEvent(type=EventType.CLEAR)
