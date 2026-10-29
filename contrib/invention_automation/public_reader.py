# SPDX-License-Identifier: Apache-2.0
"""Verify anonymous access to the exact merged public paper bytes and viewer page."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

COMMIT = "3544aa804b26364236dcac3a585f29c45498e73d"
PATH = "docs/papers/agi-alpha-invention-automation-v1-20261029.pdf"
REPOSITORY = "MontrealAI/AGI-Alpha-Agent-v0"
EXPECTED_SHA256 = "8142fe2452162901cda732f7a8070572a033ed4f0cfe269c514e40e19b60457f"


def retrieve(url: str, limit: int) -> tuple[bytes, dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": "AGI-ALPHA-public-paper-readback/1"})
    if any(key.lower() in {"authorization", "cookie"} for key in request.headers):
        raise ValueError("public verification must not authenticate")
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(limit + 1)
        if response.status != 200 or len(raw) > limit:
            raise ValueError("public response status or byte bound")
        return raw, {"url": url, "final_url": response.url, "status": response.status, "bytes": len(raw)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result: dict[str, Any] = {
        "schema": "agialpha/anonymous-paper-readback/v1",
        "paper_commit": COMMIT,
        "authentication_headers": False,
        "cookie_jar": False,
        "scope": "anonymous HTTP viewer availability and exact PDF bytes; visual inline rendering checked separately",
    }
    try:
        raw, pdf = retrieve(f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/{PATH}", 1_048_576)
        identity = hashlib.sha256(raw).hexdigest()
        if len(raw) != 622_931 or not raw.startswith(b"%PDF-") or identity != EXPECTED_SHA256:
            raise ValueError("public paper differs from the qualified reader")
        page, viewer = retrieve(f"https://github.com/{REPOSITORY}/blob/{COMMIT}/{PATH}", 4_194_304)
        html = page.decode("utf-8")
        if PATH.rsplit("/", 1)[-1] not in html or "Sign in to GitHub" in html.partition("</title>")[0]:
            raise ValueError("viewer did not expose the public paper")
        result.update(status="PASS", pdf={**pdf, "sha256": identity}, viewer=viewer)
    except (OSError, ValueError, UnicodeError) as error:
        result.update(status="FAIL", reason=str(error))
    with args.output.open("x", encoding="utf-8") as output:
        output.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
