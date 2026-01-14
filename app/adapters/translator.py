"""Translation adapter for EN -> PT translation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TranslationResult:
    """Result from translation."""
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str


class Translator(ABC):
    """Abstract base class for translation."""

    @abstractmethod
    def translate(self, text: str) -> TranslationResult:
        """Translate text from English to Portuguese."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if translator is available."""
        pass


class CloudTranslator(Translator):
    """
    Cloud-based translation (e.g., Google Translate API, DeepL).

    Best quality, simplest implementation for v1.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        source_lang: str = "en",
        target_lang: str = "pt",
    ):
        self.api_key = api_key
        self.source_lang = source_lang
        self.target_lang = target_lang

    def translate(self, text: str) -> TranslationResult:
        """Translate text using cloud API."""
        if not text.strip():
            return TranslationResult(
                source_text=text,
                translated_text="",
                source_lang=self.source_lang,
                target_lang=self.target_lang,
            )

        # TODO: Implement actual API call
        # For now, return placeholder
        translated = self._call_api(text)

        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
        )

    def _call_api(self, text: str) -> str:
        """Call translation API."""
        # Placeholder - implement with actual API
        # Options: Google Translate, DeepL, Azure, etc.
        raise NotImplementedError("Translation API not configured")

    def is_available(self) -> bool:
        """Check if API is configured."""
        return self.api_key is not None


class OfflineTranslator(Translator):
    """
    Offline translation using local models.

    Harder to implement but fully local (no internet required).
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        source_lang: str = "en",
        target_lang: str = "pt",
    ):
        self.model_path = model_path
        self.source_lang = source_lang
        self.target_lang = target_lang
        self._model = None

    def translate(self, text: str) -> TranslationResult:
        """Translate text using local model."""
        if not text.strip():
            return TranslationResult(
                source_text=text,
                translated_text="",
                source_lang=self.source_lang,
                target_lang=self.target_lang,
            )

        # TODO: Implement with local model (e.g., MarianMT, NLLB)
        raise NotImplementedError("Offline translation not yet implemented")

    def is_available(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None


class PassthroughTranslator(Translator):
    """
    Passthrough translator - returns original text.

    Useful for Phase 1 testing (transcription only).
    """

    def __init__(self, source_lang: str = "en", target_lang: str = "en"):
        self.source_lang = source_lang
        self.target_lang = target_lang

    def translate(self, text: str) -> TranslationResult:
        """Return text unchanged."""
        return TranslationResult(
            source_text=text,
            translated_text=text,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
        )

    def is_available(self) -> bool:
        """Always available."""
        return True
