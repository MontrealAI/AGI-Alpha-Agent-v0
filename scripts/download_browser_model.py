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
from typing import Any, Callable

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


class ResourceLimitExceeded(ValueError):
    """A declared response-body/request budget was exhausted; do not retry."""


class BoundedOpener:
    """Wrap a urllib-shaped opener with cumulative positive integer budgets.

    Reuse the same instance across retries. Failed opens count as requests;
    returned read bytes count as body bytes. Internal redirects are not counted
    separately. At most one excess-detection byte is
    requested beyond the body cap when the underlying read(n) honors n. Hidden
    buffering, failed-read internals, wire traffic and time are not observable.
    This object requires sequential use and is not an adversarial transport or
    concurrent security boundary.
    """

    def __init__(self, opener: Callable[..., Any], *, max_body_bytes: int, max_requests: int) -> None:
        for name, value in (("max_body_bytes", max_body_bytes), ("max_requests", max_requests)):
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        self._opener = opener
        self._body_limit = max_body_bytes
        self._request_limit = max_requests
        self.body_bytes = 0
        self.requests = 0
        self.exhausted = False

    def __call__(self, *args: Any, **kwargs: Any) -> _Response:
        if self.exhausted or self.requests >= self._request_limit:
            self.exhausted = True
            raise ResourceLimitExceeded("cumulative request/body limit exhausted")
        self.requests += 1
        return _Response(self, self._opener(*args, **kwargs))


class _Response:
    def __init__(self, budget: BoundedOpener, response: Any) -> None:
        self._budget = budget
        self._manager = response
        self._response = response

    def __enter__(self) -> _Response:
        self._response = self._manager.__enter__()
        return self

    def __exit__(self, *args: Any) -> Any:
        result = self._manager.__exit__(*args)
        if len(args) > 1 and isinstance(args[1], ResourceLimitExceeded):
            return False
        return result

    def read(self, size: int = -1) -> bytes:
        budget = self._budget
        if budget.exhausted:
            raise ResourceLimitExceeded("cumulative body limit exhausted")
        if type(size) is not int:
            raise TypeError("read size must be an integer")
        if size == 0:
            return b""
        remaining = budget._body_limit - budget.body_bytes
        requested = remaining + 1 if size < 0 else min(size, remaining + 1)
        data = self._response.read(requested)
        if not isinstance(data, bytes):
            budget.exhausted = True
            raise TypeError("underlying response must return bytes")
        budget.body_bytes += len(data)
        if len(data) > requested:
            budget.exhausted = True
            raise ResourceLimitExceeded("underlying response violated read bound")
        if budget.body_bytes > budget._body_limit:
            budget.exhausted = True
            raise ResourceLimitExceeded("cumulative body limit exceeded")
        return data


def download(output: Path, *, opener: Callable[..., Any] | None = None) -> None:
    if opener is None:
        opener = urlopen
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
                with opener(url, timeout=120) as response:
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


def download_with_retry(
    output: Path,
    attempts: int = 1,
    backoff: float = 0.25,
    *,
    max_body_bytes: int | None = None,
    max_requests: int | None = None,
    opener: Callable[..., Any] | None = None,
) -> None:
    """Resume verified files after a bounded number of transient failures.

    The downloader verifies cached files and atomically replaces only
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
    if (max_body_bytes is None) != (max_requests is None):
        raise ValueError("max_body_bytes and max_requests must be supplied together")
    selected_opener = opener
    if max_body_bytes is not None and max_requests is not None:
        selected_opener = BoundedOpener(
            urlopen if opener is None else opener,
            max_body_bytes=max_body_bytes,
            max_requests=max_requests,
        )
    for attempt in range(attempts):
        try:
            if selected_opener is None:
                download(output)
            else:
                download(output, opener=selected_opener)
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
    parser.add_argument("--max-body-bytes", type=int, help="Cumulative application response-byte cap, not wire bytes")
    parser.add_argument(
        "--max-requests", type=int,
        help="Opener-invocation cap, including failures; internal redirects are not counted",
    )
    args = parser.parse_args()
    if (args.max_body_bytes is None) != (args.max_requests is None):
        parser.error("--max-body-bytes and --max-requests must be supplied together")
    if args.max_body_bytes is not None:
        if args.max_body_bytes < 1 or args.max_requests < 1:
            parser.error("resource budgets must be positive integers")
        download_with_retry(
            args.output, attempts=args.attempts,
            max_body_bytes=args.max_body_bytes, max_requests=args.max_requests,
        )
        return
    download_with_retry(args.output, attempts=args.attempts)


if __name__ == "__main__":
    main()
