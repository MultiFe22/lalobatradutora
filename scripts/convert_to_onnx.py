#!/usr/bin/env python3
"""
Convert Helsinki-NLP/opus-mt-tc-big-en-pt model to CTranslate2 format.

CTranslate2 is optimized for efficient inference of transformer models,
especially translation models like MarianMT.

Usage:
    python scripts/convert_to_onnx.py
"""

import subprocess
import sys
from pathlib import Path


def install_dependencies():
    """Install required packages."""
    packages = [
        "ctranslate2",
        "transformers",
        "sentencepiece",
    ]

    print("Installing dependencies...")
    for pkg in packages:
        print(f"  Installing {pkg}...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", pkg, "-q"],
            stderr=subprocess.DEVNULL
        )
    print("Dependencies installed.\n")


def convert_model():
    """Convert the model to CTranslate2 format."""
    import ctranslate2

    model_id = "Helsinki-NLP/opus-mt-tc-big-en-pt"
    output_dir = Path(__file__).parent.parent / "models" / "opus-mt-en-pt-ct2"

    print(f"Converting {model_id} to CTranslate2 format...")
    print(f"Output directory: {output_dir}\n")

    # CTranslate2 has a built-in converter for Hugging Face models
    converter = ctranslate2.converters.TransformersConverter(model_id)
    converter.convert(
        str(output_dir),
        quantization="int8",  # Use int8 for faster inference and smaller size
        force=True,
    )

    print(f"\nModel converted successfully!")
    print(f"Files saved to: {output_dir}")

    # Copy tokenizer files (needed for inference)
    print("\nCopying tokenizer files...")
    from transformers import MarianTokenizer
    tokenizer = MarianTokenizer.from_pretrained(model_id)
    tokenizer.save_pretrained(output_dir)

    # List output files
    print("\nGenerated files:")
    total_size = 0
    for f in sorted(output_dir.iterdir()):
        size_mb = f.stat().st_size / (1024 * 1024)
        total_size += size_mb
        print(f"  {f.name}: {size_mb:.2f} MB")
    print(f"\nTotal size: {total_size:.2f} MB")


def test_model():
    """Quick test of the converted model."""
    import ctranslate2
    from transformers import MarianTokenizer

    output_dir = Path(__file__).parent.parent / "models" / "opus-mt-en-pt-ct2"

    print("\n" + "=" * 50)
    print("Testing converted model...")

    tokenizer = MarianTokenizer.from_pretrained(str(output_dir))
    translator = ctranslate2.Translator(str(output_dir))

    test_sentences = [
        "Hello, how are you?",
        "The quick brown fox jumps over the lazy dog.",
        "Welcome to the live subtitle system.",
    ]

    for sentence in test_sentences:
        # Tokenize
        tokens = tokenizer.convert_ids_to_tokens(tokenizer.encode(sentence))

        # Translate
        results = translator.translate_batch([tokens])

        # Decode
        output_tokens = results[0].hypotheses[0]
        translation = tokenizer.decode(tokenizer.convert_tokens_to_ids(output_tokens))

        print(f"\n  EN: {sentence}")
        print(f"  PT: {translation}")

    print("\n" + "=" * 50)
    print("Model test completed!")


def main():
    install_dependencies()
    convert_model()
    test_model()


if __name__ == "__main__":
    main()
