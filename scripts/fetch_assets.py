#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
# See docs/DISCLAIMER_SNIPPET.md
"""Download browser demo assets from official mirrors.

Environment variables:
    HF_GPT2_BASE_URL -- Override the Hugging Face base URL for the GPT‑2 model.
    PYODIDE_BASE_URL -- Override the base URL for Pyodide runtime files.

Pyodide runtime files are fetched directly from the official CDN or a user
specified mirror. The script no longer attempts alternate gateways when a
download fails.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
from pathlib import Path
import sys
import requests  # type: ignore
from requests.adapters import HTTPAdapter, Retry  # type: ignore


# Base URL for the GPT-2 small weights
DEFAULT_HF_GPT2_BASE_URL = "https://huggingface.co/openai-community/gpt2/resolve/main"
HF_GPT2_BASE_URL = os.environ.get("HF_GPT2_BASE_URL", DEFAULT_HF_GPT2_BASE_URL).rstrip("/")

# Base URL for the Pyodide runtime
# Updated to Pyodide 0.26.0
DEFAULT_PYODIDE_BASE_URL = "https://cdn.jsdelivr.net/pyodide/v0.26.0/full"
PYODIDE_BASE_URL = os.environ.get("PYODIDE_BASE_URL", DEFAULT_PYODIDE_BASE_URL).rstrip("/")
# Number of download attempts before giving up
MAX_ATTEMPTS = int(os.environ.get("FETCH_ASSETS_ATTEMPTS", "3"))

PYODIDE_ASSETS = {
    "wasm/pyodide.js",
    "wasm/pyodide.asm.wasm",
    "wasm/repodata.json",
}

ASSETS = {
    # Pyodide 0.26.0 runtime files
    "wasm/pyodide.js": f"{PYODIDE_BASE_URL}/pyodide.js",
    "wasm/pyodide.asm.wasm": f"{PYODIDE_BASE_URL}/pyodide.asm.wasm",
    "wasm/repodata.json": f"{PYODIDE_BASE_URL}/pyodide-lock.json",
    # GPT-2 small weights
    "wasm_llm/pytorch_model.bin": f"{HF_GPT2_BASE_URL}/pytorch_model.bin",
    "wasm_llm/vocab.json": f"{HF_GPT2_BASE_URL}/vocab.json",
    "wasm_llm/merges.txt": f"{HF_GPT2_BASE_URL}/merges.txt",
    "wasm_llm/config.json": f"{HF_GPT2_BASE_URL}/config.json",
    # Web3.Storage bundle
    "lib/bundle.esm.min.js": "https://cdn.jsdelivr.net/npm/web3.storage/dist/bundle.esm.min.js",  # noqa: E501
    # Workbox runtime
    "lib/workbox-sw.js": "https://storage.googleapis.com/workbox-cdn/releases/6.5.4/workbox-sw.js",
}

CHECKSUMS = {
    "lib/bundle.esm.min.js": "sha384-qri3JZdkai966TTOV3Cl4xxA97q+qXCgKrd49pOn7DPuYN74wOEd6CIJ9HnqEROD",  # noqa: E501
    "lib/workbox-sw.js": "sha384-R7RXlLLrbRAy0JWTwv62SHZwpjwwc7C0wjnLGa5bRxm6YCl5zw87IRvhlleSM5zd",  # noqa: E501
    "pyodide.asm.wasm": "sha384-EUqmec0z8Sj94lyhfS28Q0rsvZxo0lEPa3Nz2MQJz3NizgBcfd69cC2EluBQcA51",
    "pyodide.js": "sha384-KQtL+EUxNlEbNm6gFVMiDz6Glmgq4QV4VZdSHIrcpw4tCRUGtjUeLJbuQAIfxFfM",
    "repodata.json": "sha384-0jg1cSxhjdgM3qp6WXMysptCeRCzlYI2HhY0Nqy1AFzfp3GnDIFLDs7MTlaJz+Nz",
    "pytorch_model.bin": "sha256-7c5d3f4b8b76583b422fcb9189ad6c89d5d97a094541ce8932dce3ecabde1421",
}


def _session() -> requests.Session:
    retry = Retry(total=0)
    adapter = HTTPAdapter(max_retries=retry)
    s = requests.Session()
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def download(cid: str, path: Path, label: str | None = None) -> None:
    url = cid
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _session().get(url, timeout=60) as resp:
            resp.raise_for_status()
            data = resp.content
    except Exception:
        raise
    path.write_bytes(data)
    key = label or path.name
    expected = CHECKSUMS.get(key) or CHECKSUMS.get(path.name)
    if expected:
        algo, ref = expected.split("-", 1)
        digest_bytes = getattr(hashlib, algo)(data).digest()
        calc_b64 = base64.b64encode(digest_bytes).decode()
        if ref == calc_b64:
            return
        calc_hex = digest_bytes.hex()
        if ref.lower() != calc_hex:
            raise RuntimeError(f"Checksum mismatch for {key}")


def download_with_retry(
    cid: str,
    path: Path,
    attempts: int = MAX_ATTEMPTS,
    label: str | None = None,
) -> None:
    last_exc: Exception | None = None
    last_url = cid
    first_failure = True
    lbl = label or str(path)
    for i in range(1, attempts + 1):
        try:
            download(cid, path, label=lbl)
            print(f"Fetched {lbl} via primary mirror")
            return
        except Exception as exc:  # noqa: PERF203
            last_exc = exc
            last_url = cid
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if first_failure:
                first_failure = False
                if status in {401, 404}:
                    if lbl in PYODIDE_ASSETS:
                        print(f"Download returned HTTP {status}. Set PYODIDE_BASE_URL to a reachable mirror")
                    else:
                        print(f"Download returned HTTP {status}. Set HF_GPT2_BASE_URL to a reachable mirror")
            if status in {401, 404}:
                break
            if i < attempts:
                print(f"Attempt {i} failed for {lbl}: {exc}, retrying...")
            else:
                print(f"ERROR: could not fetch {lbl} from {last_url} after {attempts} attempts")
    if last_exc:
        url = getattr(getattr(last_exc, "response", None), "url", last_url)
        raise RuntimeError(f"failed to download {lbl} from {url}: {last_exc}. Some mirrors may require authentication")


def verify_assets(base: Path) -> list[str]:
    """Return a list of assets that failed verification."""

    failures: list[str] = []
    for rel in ASSETS:
        dest = base / rel
        if not dest.exists():
            print(f"Missing {rel}")
            failures.append(rel)
            continue
        expected = CHECKSUMS.get(rel) or CHECKSUMS.get(dest.name)
        if expected:
            algo, ref = expected.split("-", 1)
            digest_bytes = getattr(hashlib, algo)(dest.read_bytes()).digest()
            calc_b64 = base64.b64encode(digest_bytes).decode()
            if ref == calc_b64:
                continue
            calc_hex = digest_bytes.hex()
            if ref.lower() != calc_hex:
                print(f"Checksum mismatch for {rel}")
                failures.append(rel)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Verify asset checksums and exit")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    base = root / "alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"  # noqa: E501

    if args.verify_only:
        failures = verify_assets(base)
        if failures:
            joined = ", ".join(failures)
            sys.exit(f"verification failed for: {joined}")
        print("All assets verified successfully")
        return

    dl_failures: list[str] = []
    PLACEHOLDER_ASSETS = {
        "lib/bundle.esm.min.js",
        "lib/workbox-sw.js",
        "wasm/pyodide.js",
        "wasm/pyodide.asm.wasm",
    }
    for rel, cid in ASSETS.items():
        dest = base / rel
        check_placeholder = rel in PLACEHOLDER_ASSETS
        placeholder = False
        if dest.exists() and check_placeholder:
            text = dest.read_text(errors="ignore")
            content = text.strip()
            placeholder = not content or content == "{}" or "placeholder" in content.lower()
        if not dest.exists() or placeholder:
            if placeholder:
                print(f"Replacing placeholder {rel}...")
            else:
                print(f"Fetching {rel} from {cid}...")
            if rel in PYODIDE_ASSETS:
                print(f"Resolved Pyodide URL: {cid}")
            try:
                download_with_retry(cid, dest, label=rel)
            except Exception as exc:
                print(f"Download failed for {rel}: {exc}")
                dl_failures.append(rel)
        else:
            print(f"Skipping {rel}, already exists")

    if dl_failures:
        joined = ", ".join(dl_failures)
        print(
            f"\nERROR: Unable to retrieve {joined}.\n"
            "Check your internet connection or override the Hugging Face base URL via HF_GPT2_BASE_URL "
            "or the Pyodide base URL via PYODIDE_BASE_URL."
        )
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("aborted")
