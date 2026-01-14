#!/usr/bin/env python3
"""
Convert danhsf/m2m100_418M-finetuned-kde4-en-to-pt_BR model to CTranslate2 format.

Usage:
    python scripts/convert_m2m100.py
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

    model_id = "danhsf/m2m100_418M-finetuned-kde4-en-to-pt_BR"
    output_dir = Path(__file__).parent.parent / "models" / "m2m100-en-pt-br-ct2"

    print(f"Converting {model_id} to CTranslate2 format...")
    print(f"Output directory: {output_dir}\n")

    # CTranslate2 has a built-in converter for M2M100 models
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
    from transformers import M2M100Tokenizer
    tokenizer = M2M100Tokenizer.from_pretrained(model_id)
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
    from transformers import M2M100Tokenizer

    output_dir = Path(__file__).parent.parent / "models" / "m2m100-en-pt-br-ct2"

    print("\n" + "=" * 50)
    print("Testing converted model...")

    tokenizer = M2M100Tokenizer.from_pretrained(str(output_dir))
    tokenizer.src_lang = "en"
    translator = ctranslate2.Translator(str(output_dir))

    test_sentences = [
        "Hello, how are you?",
        "The quick brown fox jumps over the lazy dog.",
        "Welcome to the live subtitle system.",
    ]

    for sentence in test_sentences:
        # Tokenize with source language
        inputs = tokenizer(sentence, return_tensors="pt")
        tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])

        # Add target language token
        target_prefix = [tokenizer.lang_code_to_token["pt"]]

        # Translate
        results = translator.translate_batch(
            [tokens],
            target_prefix=[target_prefix],
        )

        # Decode output
        output_tokens = results[0].hypotheses[0]
        output_ids = tokenizer.convert_tokens_to_ids(output_tokens)
        translation = tokenizer.decode(output_ids, skip_special_tokens=True)

        print(f"\n  EN: {sentence}")
        print(f"  PT-BR: {translation}")

    print("\n" + "=" * 50)
    print("Model test completed!")


def main():
    install_dependencies()
    convert_model()
    test_model()


if __name__ == "__main__":
    main()
