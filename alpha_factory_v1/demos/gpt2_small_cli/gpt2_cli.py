#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Interactive GPT‑2 small demo.

This module downloads the official GPT‑2 124M checkpoint from
OpenAI if it is not already present and then generates text.

The demo prefers the locally converted PyTorch weights when
available, falling back to the built‑in ``gpt2`` model from
``transformers`` when necessary.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


MODEL_NAME = "124M"
MODEL_DIR = Path.home() / ".cache" / "agialpha" / "models"


def ensure_model() -> Path:
    """Download and verify the Hugging Face checkpoint into a user cache."""
    from .model_download import download_hf_gpt2

    dest = MODEL_DIR / "gpt2"
    download_hf_gpt2(dest)
    return dest


def generate(prompt: str, max_length: int, model_path: Path | None = None, *, offline: bool = False) -> str:
    """Generate text from the prompt using GPT‑2."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not prompt.strip() or max_length < 1:
        raise ValueError("A non-empty prompt and positive max-length are required")
    if model_path is not None and not model_path.is_dir():
        raise ValueError(f"Model directory does not exist: {model_path}")
    source = str(model_path) if model_path is not None else "gpt2"
    options = {"local_files_only": True} if offline else {}
    if hasattr(AutoTokenizer, "from_pretrained"):
        tokenizer = AutoTokenizer.from_pretrained(source, **options)
    else:  # compatibility with tests
        tokenizer = AutoTokenizer(source)
    model = AutoModelForCausalLM.from_pretrained(source, **options)
    inputs = tokenizer(prompt, return_tensors="pt")
    tokens = model.generate(
        **inputs,
        max_length=max_length,
        pad_token_id=tokenizer.eos_token_id,
    )
    text: str = tokenizer.decode(tokens[0], skip_special_tokens=True)
    return text


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run a small GPT-2 generation demo")
    parser.add_argument("--prompt", default="Hello, world!", help="Input prompt")
    parser.add_argument("--max-length", type=int, default=50, help="Maximum output length")
    parser.add_argument("--model-path", type=Path, help="Existing Hugging Face model directory")
    parser.add_argument("--offline", action="store_true", help="Never download model or tokenizer files")
    args = parser.parse_args(argv)
    if not args.prompt.strip() or args.max_length < 1:
        parser.error("Provide a non-empty prompt and a positive --max-length")
    try:
        model_path = args.model_path
        if model_path is None:
            model_path = MODEL_DIR / "gpt2" if args.offline else ensure_model()
        print(generate(args.prompt, args.max_length, model_path, offline=args.offline))
    except (ImportError, OSError, ValueError, RuntimeError) as exc:
        parser.exit(
            1,
            f"GPT-2 could not start: {exc}\nInstall torch and transformers; "
            "use --model-path with cached weights for offline use.\n",
        )


if __name__ == "__main__":
    main()
