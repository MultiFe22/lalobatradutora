"""Microphone audio capture adapter."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional, List
import threading


@dataclass
class AudioDevice:
    """Represents an audio input device."""
    index: int
    name: str
    sample_rate: int
    channels: int


class AudioCapture(ABC):
    """Abstract base class for audio capture."""

    @abstractmethod
    def list_devices(self) -> List[AudioDevice]:
        """List available audio input devices."""
        pass

    @abstractmethod
    def start(self, device_index: Optional[int] = None) -> None:
        """Start audio capture."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop audio capture."""
        pass

    @abstractmethod
    def set_callback(self, callback: Callable[[bytes], None]) -> None:
        """Set callback for audio data."""
        pass


class MicrophoneCapture(AudioCapture):
    """
    Microphone audio capture using sounddevice/pyaudio.

    Captures audio at 16kHz mono PCM for whisper.cpp compatibility.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration_ms: int = 100,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_size = int(sample_rate * chunk_duration_ms / 1000)

        self._callback: Optional[Callable[[bytes], None]] = None
        self._stream = None
        self._running = False
        self._lock = threading.Lock()

    def list_devices(self) -> List[AudioDevice]:
        """List available audio input devices."""
        devices = []
        try:
            import sounddevice as sd
            for i, device in enumerate(sd.query_devices()):
                if device["max_input_channels"] > 0:
                    devices.append(AudioDevice(
                        index=i,
                        name=device["name"],
                        sample_rate=int(device["default_samplerate"]),
                        channels=device["max_input_channels"],
                    ))
        except ImportError:
            pass  # sounddevice not installed
        return devices

    def start(self, device_index: Optional[int] = None) -> None:
        """Start audio capture from microphone."""
        with self._lock:
            if self._running:
                return

            try:
                import sounddevice as sd
                import numpy as np

                def audio_callback(indata, frames, time_info, status):
                    if status:
                        pass  # Could log status warnings
                    if self._callback:
                        # Convert float32 to int16 PCM
                        audio_int16 = (indata[:, 0] * 32767).astype(np.int16)
                        self._callback(audio_int16.tobytes())

                self._stream = sd.InputStream(
                    device=device_index,
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    blocksize=self.chunk_size,
                    dtype="float32",
                    callback=audio_callback,
                )
                self._stream.start()
                self._running = True

            except ImportError:
                raise RuntimeError("sounddevice is required for audio capture")

    def stop(self) -> None:
        """Stop audio capture."""
        with self._lock:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            self._running = False

    def set_callback(self, callback: Callable[[bytes], None]) -> None:
        """Set callback for audio data chunks."""
        self._callback = callback

    @property
    def is_running(self) -> bool:
        """Check if capture is running."""
        return self._running
