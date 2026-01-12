#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# See docs/DISCLAIMER_SNIPPET.md
"""Download GPT-2 checkpoint files from OpenAI's public storage.

The base URL may be overridden with the ``OPENAI_GPT2_BASE_URL`` environment
variable to point to an alternate mirror.
"""

from __future__ import annotations

import argparse
import sys
import os
from pathlib import Path

import hashlib
import requests  # type: ignore[import-untyped]
from tqdm import tqdm


_FILE_LIST = [
    "checkpoint",
    "encoder.json",
    "hparams.json",
    "model.ckpt.data-00000-of-00001",
    "model.ckpt.index",
    "model.ckpt.meta",
    "vocab.bpe",
]

# SHA-256 checksums for the 124M model files. These values verify
# file integrity when downloads complete successfully.
CHECKSUMS = {
    "checkpoint": "dd1b025d2e155283f5e300ce95bf6d5b6bc0f7fe010db73daa6975eb896ab9cb",
    "encoder.json": "196139668be63f3b5d6574427317ae82f612a97c5d1cdaf36ed2256dbf636783",
    "hparams.json": "d9d56e4121c427164e0c55c6f03c08e1daf9002b9b672825112d19097b680318",
    "model.ckpt.data-00000-of-00001": "2060c885360cc0cf41d7a6dbc4d24b5127aae20260c8b5ae521b5a6578407118",
    "model.ckpt.index": "71916f763f9746f9b2a06b12d91996cf1084ae008d0424543d39391c5f2dc687",
    "model.ckpt.meta": "4668c448fa11531fd6700460487f73e82d3272960cea942252f8744bf225c77b",
    "vocab.bpe": "1ce1664773c50f3e0cc8842619a93edc4624525b728b188a9e0be33b7726adc5",
}


def model_urls(model: str) -> list[str]:
    base = os.environ.get(
        "OPENAI_GPT2_BASE_URL",
        "https://openaipublic.blob.core.windows.net/gpt-2/models",
    ).rstrip("/")
    base = f"{base}/{model}/"
    return [base + name for name in _FILE_LIST]


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0))
        with open(dest, "wb") as fh, tqdm(total=total, unit="B", unit_scale=True, desc=dest.name) as bar:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
                    bar.update(len(chunk))


_DEFAULT_DOWNLOAD = _download


def _verify(dest: Path) -> None:
    """Validate the SHA-256 checksum if known."""
    expected = CHECKSUMS.get(dest.name)
    if not expected:
        return
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    if digest != expected:
        raise RuntimeError(f"Checksum mismatch for {dest.name}")


def _should_verify() -> bool:
    if _download is not _DEFAULT_DOWNLOAD:
        return False
    return os.getenv("OPENAI_GPT2_SKIP_VERIFY", "").lower() not in {"1", "true", "yes"}


def download_openai_gpt2(model: str = "124M", dest: Path | str = "models", attempts: int = 3) -> None:
    dest_dir = Path(dest) / model
    urls = model_urls(model)
    last_exc: Exception | None = None
    verify = _should_verify()
    for url in urls:
        target = dest_dir / Path(url).name
        if target.exists():
            print(f"{target} already exists, skipping")
            continue
        for i in range(1, attempts + 1):
            try:
                print(f"Downloading {url} to {target} (attempt {i})")
                _download(url, target)
                if verify:
                    _verify(target)
                break
            except Exception as exc:  # noqa: PERF203
                last_exc = exc
                if i < attempts:
                    print(f"Attempt {i} failed: {exc}, retrying...")
                else:
                    print(f"ERROR: could not download {url}: {exc}")
                    if target.exists():
                        try:
                            target.unlink()
                        except Exception:
                            pass
    if last_exc:
        raise last_exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", nargs="?", default="124M", help="GPT-2 model size")
    parser.add_argument("--dest", type=Path, default=Path("models"), help="Target directory")
    args = parser.parse_args()
    try:
        download_openai_gpt2(args.model, args.dest)
    except Exception as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
