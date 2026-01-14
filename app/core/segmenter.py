"""VAD + chunking + finalization for audio segments."""

from dataclasses import dataclass
from typing import Callable, Optional
import time
import struct
import math

from .config import SegmenterConfig


@dataclass
class AudioSegment:
    """Represents a segment of audio data."""
    data: bytes
    start_time: float
    end_time: float
    is_final: bool = False


def calculate_rms(audio_data: bytes) -> float:
    """Calculate RMS (Root Mean Square) energy of int16 PCM audio."""
    if len(audio_data) < 2:
        return 0.0

    # Unpack int16 samples
    n_samples = len(audio_data) // 2
    samples = struct.unpack(f"<{n_samples}h", audio_data[:n_samples * 2])

    if not samples:
        return 0.0

    # Calculate RMS normalized to 0-1 range
    sum_squares = sum(s * s for s in samples)
    rms = math.sqrt(sum_squares / n_samples) / 32768.0

    return rms


class Segmenter:
    """
    Voice Activity Detection and audio chunking.

    Responsibilities:
    - Detect speech start/stop using energy-based VAD
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
        self._speech_start_time: Optional[float] = None

    def reset(self) -> None:
        """Reset segmenter state."""
        self._buffer.clear()
        self._segment_start = None
        self._last_voice_time = None
        self._is_speaking = False
        self._speech_start_time = None

    def detect_voice(self, audio_data: bytes) -> bool:
        """
        Detect voice activity using RMS energy.

        Args:
            audio_data: Raw PCM audio bytes (int16)

        Returns:
            True if voice is detected, False otherwise
        """
        rms = calculate_rms(audio_data)
        return rms > self.config.energy_threshold

    def process_chunk(self, audio_data: bytes, has_voice: Optional[bool] = None) -> Optional[AudioSegment]:
        """
        Process an audio chunk and return a segment if ready.

        Args:
            audio_data: Raw audio bytes (int16 PCM)
            has_voice: Whether VAD detected voice (if None, will auto-detect)

        Returns:
            AudioSegment if a segment is finalized, None otherwise
        """
        current_time = time.time()

        # Auto-detect voice if not provided
        if has_voice is None:
            has_voice = self.detect_voice(audio_data)

        if has_voice:
            self._last_voice_time = current_time

            if not self._is_speaking:
                # Speech started
                self._is_speaking = True
                self._segment_start = current_time
                self._speech_start_time = current_time
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
            # Check minimum speech duration
            speech_duration_ms = (current_time - self._segment_start) * 1000
            if speech_duration_ms >= self.config.min_speech_duration_ms:
                return self._finalize_segment(current_time)
            else:
                # Too short, discard
                self.reset()
                return None

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
