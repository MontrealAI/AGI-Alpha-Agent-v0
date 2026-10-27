# SPDX-License-Identifier: Apache-2.0
"""Recover attributed public prompt inputs, refusing changed issue/comment bodies."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def body_hash(value: dict[str, Any]) -> str:
    """Hash the exact UTF-8 issue or comment body received by the original arms."""
    return hashlib.sha256((value.get("body") or "").encode("utf-8")).hexdigest()


def retrieve(url: str) -> dict[str, Any]:
    """Fetch public GitHub JSON without credentials or external mutations."""
    if not url.startswith("https://api.github.com/repos/scipy/scipy/issues/"):
        raise ValueError("Input manifest URL is outside the permitted public issue source")
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json", "User-Agent": "AGI-ALPHA-reproduction"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        value: Any = json.load(response)
    if not isinstance(value, dict):
        raise ValueError("Expected an issue/comment JSON object")
    return value


def verify(data: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Check the original supplied bodies rather than mutable transport metadata."""
    expected = manifest["selected_prompt_input"]
    if body_hash(data["issue"]) != expected["issue"]["body_sha256"]:
        raise ValueError("Public issue body changed; original prompt equivalence cannot be asserted")
    comments = {entry["id"]: entry for entry in data["comments"]}
    for item in expected["comments"]:
        if item["id"] not in comments or body_hash(comments[item["id"]]) != item["body_sha256"]:
            raise ValueError(f"Public comment {item['id']} changed or is missing")


def main() -> None:
    """Recover or verify inputs only when explicitly invoked by the recipient."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "discovery/scipy_26531.json")
    parser.add_argument("--verify-local", type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "delivery/public_input_manifest.json").read_text())
    if args.verify_local is not None:
        data = json.loads(args.verify_local.read_text())
    else:
        if args.output.exists():
            raise SystemExit("Refusing to overwrite an existing public-input record")
        expected = manifest["selected_prompt_input"]
        data = {
            "issue": retrieve(expected["issue"]["api_url"]),
            "comments": [retrieve(item["api_url"]) for item in expected["comments"]],
            "referencing_pr_search": expected["original_pr_search_summary"],
            "retrieval_note": "Body-equivalent reconstruction; mutable API metadata need not match the original snapshot.",
        }
    verify(data, manifest)
    if args.verify_local is None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps({"issue_and_recorded_comment_bodies_match": True, "network_used": args.verify_local is None}))


if __name__ == "__main__":
    main()
