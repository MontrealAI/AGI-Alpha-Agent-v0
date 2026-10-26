#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Download the pinned browser ONNX baseline and verify every file."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def download(output: Path) -> None:
    manifest = json.loads(Path(__file__).with_name("browser_model_manifest.json").read_text())
    for name, expected in manifest["files"].items():
        target = output / name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        source_name = manifest.get("sources", {}).get(name, name)
        url = f"https://huggingface.co/{manifest['repository']}/resolve/{manifest['revision']}/{source_name}"
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            temp = Path(stream.name)
            try:
                digest = hashlib.sha256()
                with urlopen(url, timeout=120) as response:
                    while chunk := response.read(1024 * 1024):
                        digest.update(chunk)
                        stream.write(chunk)
                stream.close()
                if digest.hexdigest() != expected:
                    raise ValueError(f"Model checksum mismatch: {name}")
                temp.replace(target)
            finally:
                temp.unlink(missing_ok=True)
        print(f"Verified {name}", flush=True)


def download_with_retry(output: Path, attempts: int = 1, backoff: float = 0.25) -> None:
    """Resume verified files after a bounded number of transient failures.

    The unchanged downloader verifies cached files and atomically replaces only
    checksum-verified responses. Retry the queue at most three times; successful
    files are reused. One attempt is the default; retries require explicit opt-in.
    Permanent, integrity and unknown errors propagate directly.
    This is not a whole-operation deadline, Retry-After policy or concurrent lock.
    """
    if type(attempts) is not int or not 1 <= attempts <= 3:
        raise ValueError("attempts must be an integer from 1 to 3")
    if type(backoff) is not int and type(backoff) is not float:
        raise ValueError("backoff must be from 0 to 2 seconds")
    if not 0 <= backoff <= 2:
        raise ValueError("backoff must be from 0 to 2 seconds")
    for attempt in range(attempts):
        try:
            download(output)
            return
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt + 1 == attempts:
                raise
        except URLError as exc:
            if not isinstance(exc.reason, (TimeoutError, ConnectionError)) or attempt + 1 == attempts:
                raise
        except (TimeoutError, ConnectionError):
            if attempt + 1 == attempts:
                raise
        time.sleep(backoff * (2**attempt))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--attempts", type=int, choices=(1, 2, 3), default=1,
        help="Whole-manifest attempts; default 1. Opt-in retries can redownload large files.",
    )
    args = parser.parse_args()
    download_with_retry(args.output, attempts=args.attempts)


if __name__ == "__main__":
    main()
