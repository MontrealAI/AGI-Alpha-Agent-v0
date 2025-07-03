#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
# This script is a conceptual research prototype.
"""Download browser demo assets from IPFS or a mirror."""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
from pathlib import Path
import sys
import requests  # type: ignore
from requests.adapters import HTTPAdapter, Retry  # type: ignore

# IPFS gateway used for model downloads
GATEWAY = os.environ.get("IPFS_GATEWAY", "https://ipfs.io/ipfs").rstrip("/")
# Official fallback link for the wasm-gpt2 model
OFFICIAL_WASM_GPT2_URL = (
    "https://cloudflare-ipfs.com/ipfs/" "bafybeihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku?download=1"
)
# Alternate gateways to try when the main download fails
FALLBACK_GATEWAYS = [
    "https://w3s.link/ipfs",
    "https://ipfs.io/ipfs",
    "https://cloudflare-ipfs.com/ipfs",
]

ASSETS = {
    # Pyodide 0.25 runtime files
    "wasm/pyodide.js": "bafybeiaxk3fzpjn4oi2z7rn6p5wqp5b62ukptmzqk7qhmyeeri3zx4t2pa",  # noqa: E501
    "wasm/pyodide.asm.wasm": "bafybeifub317gmrhdss4u5aefygb4oql6dyks3v6llqj77pnibsglj6nde",  # noqa: E501
    "wasm/pyodide_py.tar": "bafybeidazzkz4a3qle6wvyjfwcb36br4idlm43oe5cb26wqzsa4ho7t52e",  # noqa: E501
    "wasm/packages.json": "bafybeib44a4x7jgqhkgzo5wmgyslyqi1aocsswcdpsnmqkhmvqchwdcql4",  # noqa: E501
    # wasm-gpt2 model archive
    "wasm_llm/wasm-gpt2.tar": "bafybeihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku",  # noqa: E501
    # Web3.Storage bundle
    "lib/bundle.esm.min.js": "bafkreihgldx46iuks4lybdsc5qc6xom2y5fqdy5w3vvrxntlr42wc43u74",  # noqa: E501
    # Workbox runtime
    "lib/workbox-sw.js": "https://storage.googleapis.com/workbox-cdn/releases/6.5.4/workbox-sw.js",
}

CHECKSUMS = {
    "lib/bundle.esm.min.js": "sha384-qri3JZdkai966TTOV3Cl4xxA97q+qXCgKrd49pOn7DPuYN74wOEd6CIJ9HnqEROD",  # noqa: E501
    "lib/workbox-sw.js": "sha384-LWo7skrGueg8Fa4y2Vpe1KB4g0SifqKfDr2gWFRmzZF9n9F1bQVo1F0dUurlkBJo",  # noqa: E501
    "pyodide.asm.wasm": "sha384-kdvSehcoFMjX55sjg+o5JHaLhOx3HMkaLOwwMFmwH+bmmtvfeJ7zFEMWaqV9+wqo",
}


def _session() -> requests.Session:
    retry = Retry(total=0)
    adapter = HTTPAdapter(max_retries=retry)
    s = requests.Session()
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def download(cid: str, path: Path, fallback: str | None = None) -> None:
    url = cid if cid.startswith("http") else f"{GATEWAY}/{cid}"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _session().get(url, timeout=60) as resp:
            resp.raise_for_status()
            data = resp.content
    except Exception:
        if not fallback:
            raise
        with _session().get(fallback, timeout=60) as resp:
            resp.raise_for_status()
            data = resp.content
    path.write_bytes(data)
    expected = CHECKSUMS.get(path.name)
    if expected:
        digest = base64.b64encode(hashlib.sha384(data).digest()).decode()
        if not expected.endswith(digest):
            raise RuntimeError(f"Checksum mismatch for {path.name}")


def download_with_retry(
    cid: str,
    path: Path,
    fallback: str | None = None,
    attempts: int = 3,
    label: str | None = None,
) -> None:
    last_exc: Exception | None = None
    lbl = label or str(path)
    alt_urls: list[str] = []
    if fallback:
        alt_urls.append(fallback)
    if not cid.startswith("http"):
        for gw in FALLBACK_GATEWAYS:
            if gw.rstrip("/") != GATEWAY:
                alt_urls.append(f"{gw.rstrip('/')}/{cid}")
    for i in range(1, attempts + 1):
        try:
            download(cid, path)
            return
        except Exception as exc:  # noqa: PERF203
            last_exc = exc
            for alt in alt_urls:
                try:
                    download(alt, path)
                    return
                except Exception:
                    continue
            if i < attempts:
                print(f"Attempt {i} failed for {lbl}: {exc}, retrying...")
            else:
                print(f"ERROR: could not fetch {lbl} after {attempts} attempts")
    if last_exc:
        raise last_exc


def verify_assets(base: Path) -> list[str]:
    """Return a list of assets that failed verification."""

    failures: list[str] = []
    for rel in ASSETS:
        dest = base / rel
        if not dest.exists():
            print(f"Missing {rel}")
            failures.append(rel)
            continue
        expected = CHECKSUMS.get(dest.name)
        if expected:
            digest = base64.b64encode(hashlib.sha384(dest.read_bytes()).digest()).decode()
            if not expected.endswith(digest):
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
    for rel, cid in ASSETS.items():
        dest = base / rel
        check_placeholder = rel in {
            "lib/bundle.esm.min.js",
            "lib/workbox-sw.js",
        }
        placeholder = False
        if dest.exists() and check_placeholder:
            text = dest.read_text(errors="ignore")
            placeholder = "placeholder" in text.lower()
        if not dest.exists() or placeholder:
            if placeholder:
                print(f"Replacing placeholder {rel}...")
            else:
                print(f"Fetching {rel} from {cid}...")
            fallback = None
            if rel == "lib/bundle.esm.min.js":
                fallback = "https://cdn.jsdelivr.net/npm/web3.storage/dist/bundle.esm.min.js"  # noqa: E501
            elif rel == "wasm_llm/wasm-gpt2.tar":
                fallback = OFFICIAL_WASM_GPT2_URL
            try:
                download_with_retry(cid, dest, fallback, label=rel)
            except Exception as exc:
                print(f"Download failed for {rel}: {exc}")
                dl_failures.append(rel)
        else:
            print(f"Skipping {rel}, already exists")

    if dl_failures:
        joined = ", ".join(dl_failures)
        print(
            f"\nERROR: Unable to retrieve {joined}.\n"
            "Check your internet connection or set IPFS_GATEWAY to a reachable "
            "gateway."
        )
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("aborted")
