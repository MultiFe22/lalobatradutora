"""Subprocess wrapper for whisper.cpp CLI."""

import json
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import struct
import sys


@dataclass
class TranscriptionResult:
    """Result from whisper transcription."""
    text: str
    language: str
    duration_ms: float
    segments: list  # Raw segments from whisper if available


class WhisperRunner:
    """
    Wrapper for whisper.cpp CLI binary.

    Runs whisper as a subprocess with:
    - Input: WAV file (temp)
    - Output: JSON transcript
    """

    def __init__(
        self,
        binary_path: Optional[Path] = None,
        model_path: Optional[Path] = None,
        language: str = "en",
    ):
        self.binary_path = binary_path or self._default_binary_path()
        self.model_path = model_path or Path("models/ggml-small.en.bin")
        self.language = language

    def _default_binary_path(self) -> Path:
        """Get default whisper binary path based on platform."""
        if sys.platform == "darwin":
            return Path("bin/whisper-macos")
        elif sys.platform == "win32":
            return Path("bin/whisper-windows.exe")
        else:
            return Path("bin/whisper-linux")

    def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> TranscriptionResult:
        """
        Transcribe audio data using whisper.cpp.

        Args:
            audio_data: Raw PCM audio bytes (int16)
            sample_rate: Sample rate of the audio

        Returns:
            TranscriptionResult with transcribed text
        """
        # Write audio to temp WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            self._write_wav(tmp_path, audio_data, sample_rate)

        try:
            result = self._run_whisper(tmp_path)
            return result
        finally:
            # Clean up temp file
            tmp_path.unlink(missing_ok=True)

    def _write_wav(self, path: Path, audio_data: bytes, sample_rate: int) -> None:
        """Write PCM data to WAV file."""
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)  # mono
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(sample_rate)
            wav.writeframes(audio_data)

    def _run_whisper(self, audio_path: Path) -> TranscriptionResult:
        """Run whisper.cpp binary on audio file."""
        cmd = [
            str(self.binary_path),
            "-m", str(self.model_path),
            "-l", self.language,
            "-f", str(audio_path),
            "--output-json",
            "--no-timestamps",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Whisper failed: {result.stderr}")

            return self._parse_output(result.stdout)

        except subprocess.TimeoutExpired:
            raise RuntimeError("Whisper transcription timed out")
        except FileNotFoundError:
            raise RuntimeError(f"Whisper binary not found at {self.binary_path}")

    def _parse_output(self, output: str) -> TranscriptionResult:
        """Parse whisper output (JSON or plain text)."""
        try:
            # Try JSON format first
            data = json.loads(output)
            text = data.get("text", "").strip()
            segments = data.get("segments", [])
            return TranscriptionResult(
                text=text,
                language=self.language,
                duration_ms=0,
                segments=segments,
            )
        except json.JSONDecodeError:
            # Fall back to plain text
            return TranscriptionResult(
                text=output.strip(),
                language=self.language,
                duration_ms=0,
                segments=[],
            )

    def is_available(self) -> bool:
        """Check if whisper binary is available."""
        return self.binary_path.exists() and self.model_path.exists()
