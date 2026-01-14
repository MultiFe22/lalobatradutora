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


class CTranslate2Translator(Translator):
    """
    Offline translation using CTranslate2 with Helsinki-NLP MarianMT model.

    Fast, efficient, fully local translation (no internet required).
    """

    def __init__(
        self,
        model_path: str = "models/opus-mt-en-pt-ct2",
        source_lang: str = "en",
        target_lang: str = "pt",
        device: str = "auto",
    ):
        from pathlib import Path
        self.model_path = Path(model_path)
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.device = device

        self._translator = None
        self._tokenizer = None
        self._loaded = False

    def load(self) -> None:
        """Load the model and tokenizer."""
        if self._loaded:
            return

        try:
            import ctranslate2
            from transformers import MarianTokenizer

            # Load CTranslate2 model
            self._translator = ctranslate2.Translator(
                str(self.model_path),
                device=self.device,
            )

            # Load tokenizer
            self._tokenizer = MarianTokenizer.from_pretrained(str(self.model_path))

            self._loaded = True
            print(f"Translation model loaded from {self.model_path}")

        except ImportError as e:
            raise RuntimeError(
                "CTranslate2 or transformers not installed. "
                "Run: pip install ctranslate2 transformers sentencepiece"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to load translation model: {e}") from e

    def translate(self, text: str) -> TranslationResult:
        """Translate text from English to Portuguese."""
        if not text.strip():
            return TranslationResult(
                source_text=text,
                translated_text="",
                source_lang=self.source_lang,
                target_lang=self.target_lang,
            )

        # Lazy load model on first use
        if not self._loaded:
            self.load()

        # Tokenize input
        tokens = self._tokenizer.convert_ids_to_tokens(
            self._tokenizer.encode(text)
        )

        # Translate
        results = self._translator.translate_batch([tokens])

        # Decode output
        output_tokens = results[0].hypotheses[0]
        translated_text = self._tokenizer.decode(
            self._tokenizer.convert_tokens_to_ids(output_tokens)
        )

        return TranslationResult(
            source_text=text,
            translated_text=translated_text,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
        )

    def is_available(self) -> bool:
        """Check if model files exist."""
        return self.model_path.exists()


class M2M100Translator(Translator):
    """
    Offline translation using CTranslate2 with M2M100 model.

    Supports Brazilian Portuguese (pt_BR) translation.
    """

    def __init__(
        self,
        model_path: str = "models/m2m100-en-pt-br-ct2",
        source_lang: str = "en",
        target_lang: str = "pt",
        device: str = "auto",
    ):
        from pathlib import Path
        self.model_path = Path(model_path)
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.device = device

        self._translator = None
        self._tokenizer = None
        self._loaded = False

    def load(self) -> None:
        """Load the model and tokenizer."""
        if self._loaded:
            return

        try:
            import ctranslate2
            from transformers import M2M100Tokenizer

            # Load CTranslate2 model
            self._translator = ctranslate2.Translator(
                str(self.model_path),
                device=self.device,
            )

            # Load tokenizer and set source language
            self._tokenizer = M2M100Tokenizer.from_pretrained(str(self.model_path))
            self._tokenizer.src_lang = self.source_lang

            self._loaded = True
            print(f"M2M100 translation model loaded from {self.model_path}")

        except ImportError as e:
            raise RuntimeError(
                "CTranslate2 or transformers not installed. "
                "Run: pip install ctranslate2 transformers sentencepiece"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to load translation model: {e}") from e

    def translate(self, text: str) -> TranslationResult:
        """Translate text from English to Portuguese."""
        if not text.strip():
            return TranslationResult(
                source_text=text,
                translated_text="",
                source_lang=self.source_lang,
                target_lang=self.target_lang,
            )

        # Lazy load model on first use
        if not self._loaded:
            self.load()

        # Tokenize input
        inputs = self._tokenizer(text, return_tensors="pt")
        tokens = self._tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])

        # Target language prefix (M2M100 requires this)
        target_prefix = [self._tokenizer.lang_code_to_token[self.target_lang]]

        # Translate
        results = self._translator.translate_batch(
            [tokens],
            target_prefix=[target_prefix],
        )

        # Decode output
        output_tokens = results[0].hypotheses[0]
        output_ids = self._tokenizer.convert_tokens_to_ids(output_tokens)
        translated_text = self._tokenizer.decode(output_ids, skip_special_tokens=True)

        return TranslationResult(
            source_text=text,
            translated_text=translated_text,
            source_lang=self.source_lang,
            target_lang=self.target_lang,
        )

    def is_available(self) -> bool:
        """Check if model files exist."""
        return self.model_path.exists()


# Alias for backwards compatibility
OfflineTranslator = M2M100Translator


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
