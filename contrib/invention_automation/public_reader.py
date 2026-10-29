# SPDX-License-Identifier: Apache-2.0
"""Verify anonymous access to the exact merged public paper bytes and viewer page."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

COMMIT = "3544aa804b26364236dcac3a585f29c45498e73d"
PATH = "docs/papers/agi-alpha-invention-automation-v1-20261029.pdf"
REPOSITORY = "MontrealAI/AGI-Alpha-Agent-v0"
EXPECTED_SHA256 = "8142fe2452162901cda732f7a8070572a033ed4f0cfe269c514e40e19b60457f"


def retrieve(url: str, limit: int) -> tuple[bytes, dict[str, Any]]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "AGI-ALPHA-public-paper-readback/1"}
    )
    if any(key.lower() in {"authorization", "cookie"} for key in request.headers):
        raise ValueError("public verification must not authenticate")
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(limit + 1)
        if response.status != 200 or len(raw) > limit:
            raise ValueError("public response status or byte bound")
        return raw, {
            "url": url,
            "final_url": response.url,
            "status": response.status,
            "bytes": len(raw),
        }


def official_inline_url(page: str) -> str:
    """Bind GitHub's public displayUrl to the exact immutable PDF."""
    matches = re.findall(r'"displayUrl"\s*:\s*("(?:\\.|[^"\\])*")', page)
    if len(matches) != 1:
        raise ValueError("missing or ambiguous GitHub PDF displayUrl")
    url = json.loads(matches[0])
    if not isinstance(url, str) or any(ord(char) <= 32 or ord(char) == 127 for char in url):
        raise ValueError("invalid GitHub PDF viewer URL")
    parts = urllib.parse.urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.netloc != "viewscreen.githubusercontent.com"
        or parts.path != "/view/pdf"
        or parts.username is not None
        or parts.password is not None
        or parts.port is not None
        or "#" in url
    ):
        raise ValueError("GitHub PDF viewer origin or fragment mismatch")
    try:
        query = urllib.parse.parse_qs(parts.query, strict_parsing=True, keep_blank_values=True)
    except ValueError:
        raise ValueError("invalid GitHub PDF viewer query") from None
    if any(len(values) != 1 for values in query.values()):
        raise ValueError("ambiguous GitHub PDF viewer query")
    expected = {
        "commit": COMMIT,
        "logged_in": "false",
        "nwo": REPOSITORY,
        "path": PATH,
        "repository_id": "922805069",
        "repository_type": "Repository",
    }
    if any(query.get(key) != [value] for key, value in expected.items()):
        raise ValueError("GitHub PDF viewer source binding mismatch")
    encoded = query.get("enc_url", [""])[0]
    if not re.fullmatch(r"[0-9a-f]+", encoded):
        raise ValueError("invalid GitHub PDF viewer source encoding")
    raw_url = f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/{PATH}"
    if bytes.fromhex(encoded).decode("ascii") != raw_url:
        raise ValueError("GitHub PDF viewer raw source mismatch")
    return url


def write_inline_url(path: Path, url: str) -> None:
    """Keep the opaque viewer query out of artifacts and logs."""
    temporary = os.environ.get("RUNNER_TEMP")
    if not temporary or path.parent.resolve(strict=True) != Path(temporary).resolve(strict=True):
        raise ValueError("inline URL output must be directly inside RUNNER_TEMP")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(url + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inline-url-output", type=Path)
    args = parser.parse_args()
    result: dict[str, Any] = {
        "schema": "agialpha/anonymous-paper-readback/v1",
        "paper_commit": COMMIT,
        "authentication_headers": False,
        "cookie_jar": False,
        "scope": "anonymous HTTP viewer availability and exact PDF bytes; visual inline rendering checked separately",
    }
    try:
        raw, pdf = retrieve(
            f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/{PATH}", 1_048_576
        )
        identity = hashlib.sha256(raw).hexdigest()
        if len(raw) != 622_931 or not raw.startswith(b"%PDF-") or identity != EXPECTED_SHA256:
            raise ValueError("public paper differs from the qualified reader")
        page, viewer = retrieve(f"https://github.com/{REPOSITORY}/blob/{COMMIT}/{PATH}", 4_194_304)
        html = page.decode("utf-8")
        if (
            PATH.rsplit("/", 1)[-1] not in html
            or "Sign in to GitHub" in html.partition("</title>")[0]
        ):
            raise ValueError("viewer did not expose the public paper")
        inline_url = official_inline_url(html)
        if args.inline_url_output is not None:
            write_inline_url(args.inline_url_output, inline_url)
        result.update(
            status="PASS",
            pdf={**pdf, "sha256": identity},
            viewer=viewer,
            inline_viewer={
                "url_sha256": hashlib.sha256(inline_url.encode("utf-8")).hexdigest(),
                "provenance": "anonymous GitHub blob HTML displayUrl",
                "host": "viewscreen.githubusercontent.com",
                "paper_commit": COMMIT,
                "scope": "Validated official PDF iframe route; rendering requires visual inspection.",
            },
        )
    except (OSError, ValueError, UnicodeError) as error:
        result.update(status="FAIL", reason=str(error))
    with args.output.open("x", encoding="utf-8") as output:
        output.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
