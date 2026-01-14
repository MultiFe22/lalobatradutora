"""Application configuration with suggested default parameters."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AudioConfig:
    """Audio capture configuration."""
    sample_rate: int = 16000  # 16 kHz
    channels: int = 1  # mono
    chunk_duration_ms: int = 100  # audio chunk size for processing


@dataclass
class SegmenterConfig:
    """VAD and segmentation configuration."""
    silence_threshold_ms: int = 400  # 300-500ms to finalize
    max_segment_length_s: float = 10.0  # 8-12s force finalize
    chunk_overlap_ms: int = 200  # helps avoid cut words
    energy_threshold: float = 0.01  # RMS energy threshold for VAD
    min_speech_duration_ms: int = 250  # minimum speech to consider valid


@dataclass
class WhisperConfig:
    """Whisper transcription configuration."""
    binary_path: Path = field(default_factory=lambda: Path("bin/whisper-cli"))
    model_path: Path = field(default_factory=lambda: Path("models/ggml-base.en.bin"))
    language: str = "en"
    threads: int = 4


@dataclass
class OverlayConfig:
    """Overlay display configuration."""
    subtitle_ttl_s: float = 6.0  # seconds before fade out
    max_lines: int = 2  # rolling buffer of lines


@dataclass
class ServerConfig:
    """HTTP/WebSocket server configuration."""
    host: str = "127.0.0.1"
    port: int = 8765


@dataclass
class AppConfig:
    """Main application configuration."""
    audio: AudioConfig = field(default_factory=AudioConfig)
    segmenter: SegmenterConfig = field(default_factory=SegmenterConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    server: ServerConfig = field(default_factory=ServerConfig)


def load_config() -> AppConfig:
    """Load configuration (can be extended to load from file)."""
    return AppConfig()
