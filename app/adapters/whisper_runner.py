"""Subprocess wrapper for whisper.cpp CLI."""

import json
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..core.config import WhisperConfig


@dataclass
class TranscriptionResult:
    """Result from whisper transcription."""
    text: str
    language: str
    duration_ms: float
    segments: list  # Raw segments from whisper if available


class WhisperRunner:
    """
    Wrapper for whisper.cpp CLI binary (whisper-cli).

    Runs whisper as a subprocess with:
    - Input: WAV file (temp)
    - Output: JSON transcript
    """

    def __init__(self, config: Optional[WhisperConfig] = None):
        if config is None:
            config = WhisperConfig()
        self.config = config
        self.binary_path = config.binary_path
        self.model_path = config.model_path
        self.language = config.language
        self.threads = config.threads

    def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> TranscriptionResult:
        """
        Transcribe audio data using whisper.cpp.

        Args:
            audio_data: Raw PCM audio bytes (int16)
            sample_rate: Sample rate of the audio

        Returns:
            TranscriptionResult with transcribed text
        """
        # Create temp directory for input and output files
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            wav_path = tmp_path / "audio.wav"
            output_base = tmp_path / "audio"

            # Write audio to temp WAV file
            self._write_wav(wav_path, audio_data, sample_rate)

            # Run whisper
            result = self._run_whisper(wav_path, output_base)
            return result

    def _write_wav(self, path: Path, audio_data: bytes, sample_rate: int) -> None:
        """Write PCM data to WAV file."""
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)  # mono
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(sample_rate)
            wav.writeframes(audio_data)

    def _run_whisper(self, audio_path: Path, output_base: Path) -> TranscriptionResult:
        """Run whisper-cli binary on audio file."""
        cmd = [
            str(self.binary_path),
            "-m", str(self.model_path),
            "-l", self.language,
            "-t", str(self.threads),
            "-f", str(audio_path),
            "-of", str(output_base),  # Output file base (will add .json)
            "-oj",  # Output JSON
            "-np",  # No prints (quiet mode)
            "-sns",  # Suppress non-speech tokens (brackets, musical notes, etc.)
        ]

        try:
            # Suppress console window on Windows
            creationflags = 0
            if sys.platform == "win32":
                # CREATE_NO_WINDOW flag (0x08000000) suppresses console window on Windows
                creationflags = 0x08000000

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=creationflags,
            )

            if result.returncode != 0:
                # Check stderr for actual errors
                stderr = result.stderr.strip()
                if stderr and "error" in stderr.lower():
                    raise RuntimeError(f"Whisper failed: {stderr}")

            # Read JSON output file
            json_path = Path(str(output_base) + ".json")
            if json_path.exists():
                return self._parse_json_file(json_path)

            # Fallback: try to parse stdout
            if result.stdout.strip():
                return self._parse_text_output(result.stdout)

            return TranscriptionResult(
                text="",
                language=self.language,
                duration_ms=0,
                segments=[],
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError("Whisper transcription timed out")
        except FileNotFoundError:
            raise RuntimeError(f"Whisper binary not found at {self.binary_path}")

    def _parse_json_file(self, json_path: Path) -> TranscriptionResult:
        """Parse whisper JSON output file."""
        with open(json_path, "r") as f:
            data = json.load(f)

        # whisper-cli JSON format has "transcription" array with segments
        transcription = data.get("transcription", [])

        # Extract text from all segments
        text_parts = []
        for segment in transcription:
            text = segment.get("text", "").strip()
            if text:
                text_parts.append(text)

        full_text = " ".join(text_parts)

        return TranscriptionResult(
            text=full_text,
            language=self.language,
            duration_ms=0,
            segments=transcription,
        )

    def _parse_text_output(self, output: str) -> TranscriptionResult:
        """Parse plain text output from whisper."""
        # Remove timestamp prefixes if present (e.g., "[00:00:00.000 --> 00:00:02.000]")
        lines = output.strip().split("\n")
        text_parts = []

        for line in lines:
            line = line.strip()
            if line.startswith("[") and "]" in line:
                # Remove timestamp prefix
                idx = line.index("]")
                line = line[idx + 1:].strip()
            if line:
                text_parts.append(line)

        return TranscriptionResult(
            text=" ".join(text_parts),
            language=self.language,
            duration_ms=0,
            segments=[],
        )

    def is_available(self) -> bool:
        """Check if whisper binary and model are available."""
        return self.binary_path.exists() and self.model_path.exists()
