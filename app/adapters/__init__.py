"""Adapter modules for external integrations."""

from .audio_mic import MicrophoneCapture, AudioCapture, AudioDevice
from .whisper_runner import WhisperRunner, TranscriptionResult
from .translator import Translator, CloudTranslator, OfflineTranslator, PassthroughTranslator

__all__ = [
    "MicrophoneCapture",
    "AudioCapture",
    "AudioDevice",
    "WhisperRunner",
    "TranscriptionResult",
    "Translator",
    "CloudTranslator",
    "OfflineTranslator",
    "PassthroughTranslator",
]
