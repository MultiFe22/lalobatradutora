"""VAD + chunking + finalization for audio segments."""

from dataclasses import dataclass, field
from typing import Callable, Optional
import time

from .config import SegmenterConfig


@dataclass
class AudioSegment:
    """Represents a segment of audio data."""
    data: bytes
    start_time: float
    end_time: float
    is_final: bool = False


class Segmenter:
    """
    Voice Activity Detection and audio chunking.

    Responsibilities:
    - Detect speech start/stop
    - Accumulate audio chunks during speech
    - Finalize segment on silence threshold
    - Force finalize on max segment length
    """

    def __init__(
        self,
        config: SegmenterConfig,
        on_segment_ready: Optional[Callable[[AudioSegment], None]] = None,
    ):
        self.config = config
        self.on_segment_ready = on_segment_ready

        self._buffer: bytearray = bytearray()
        self._segment_start: Optional[float] = None
        self._last_voice_time: Optional[float] = None
        self._is_speaking: bool = False

    def reset(self) -> None:
        """Reset segmenter state."""
        self._buffer.clear()
        self._segment_start = None
        self._last_voice_time = None
        self._is_speaking = False

    def process_chunk(self, audio_data: bytes, has_voice: bool) -> Optional[AudioSegment]:
        """
        Process an audio chunk and return a segment if ready.

        Args:
            audio_data: Raw audio bytes
            has_voice: Whether VAD detected voice in this chunk

        Returns:
            AudioSegment if a segment is finalized, None otherwise
        """
        current_time = time.time()

        if has_voice:
            self._last_voice_time = current_time

            if not self._is_speaking:
                # Speech started
                self._is_speaking = True
                self._segment_start = current_time
                self._buffer.clear()

            self._buffer.extend(audio_data)

        elif self._is_speaking:
            # No voice but was speaking - add to buffer (might be brief pause)
            self._buffer.extend(audio_data)

        # Check finalization conditions
        segment = self._check_finalization(current_time)
        return segment

    def _check_finalization(self, current_time: float) -> Optional[AudioSegment]:
        """Check if segment should be finalized."""
        if not self._is_speaking or self._segment_start is None:
            return None

        segment_duration = current_time - self._segment_start
        silence_duration = 0.0

        if self._last_voice_time:
            silence_duration = (current_time - self._last_voice_time) * 1000  # ms

        # Finalize on silence threshold
        if silence_duration >= self.config.silence_threshold_ms:
            return self._finalize_segment(current_time)

        # Force finalize on max length
        if segment_duration >= self.config.max_segment_length_s:
            return self._finalize_segment(current_time)

        return None

    def _finalize_segment(self, end_time: float) -> AudioSegment:
        """Create a finalized segment and reset state."""
        segment = AudioSegment(
            data=bytes(self._buffer),
            start_time=self._segment_start or end_time,
            end_time=end_time,
            is_final=True,
        )

        self.reset()

        if self.on_segment_ready:
            self.on_segment_ready(segment)

        return segment

    def force_finalize(self) -> Optional[AudioSegment]:
        """Force finalization of current segment (e.g., on toggle off)."""
        if self._is_speaking and len(self._buffer) > 0:
            return self._finalize_segment(time.time())
        return None
