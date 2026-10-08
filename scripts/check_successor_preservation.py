# SPDX-License-Identifier: Apache-2.0
"""Inventory the complete pre-SUCCESSOR tree and enforce retained assets/diagrams."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

BASE = "aab4995ee87f7fb575180931c79b8bf86e26d50d"
ROOT = Path(__file__).resolve().parents[1]
MEDIA = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf", ".pptx", ".mp4", ".mp3"}


def check(root: Path = ROOT, baseline: str = BASE) -> dict[str, Any]:
    """Require every baseline path, original media bytes and original Mermaid block."""
    rows = subprocess.check_output(["git", "ls-tree", "-rz", baseline], cwd=root).split(b"\0")
    inventory = []
    diagrams = media = 0
    for row in rows:
        if not row:
            continue
        metadata, encoded = row.split(b"\t", 1)
        mode, kind, blob = metadata.decode().split()
        name = encoded.decode("utf-8")
        path = root / name
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"Unsupported original tree entry: {name}")
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Original path missing or replaced by a link: {name}")
        after_blob = subprocess.check_output(["git", "hash-object", "--", name], cwd=root, text=True).strip()
        unchanged = after_blob == blob
        if path.suffix.lower() in MEDIA:
            if not unchanged:
                raise ValueError(f"Original media bytes changed: {name}")
            media += 1
        retained = 0
        if path.suffix.lower() in {".md", ".html", ".mmd"}:
            before = subprocess.check_output(["git", "cat-file", "blob", blob], cwd=root).decode("utf-8")
            prior = Counter(re.findall(r"```mermaid[^\n]*\n.*?\n```", before, re.DOTALL))
            current = Counter(re.findall(r"```mermaid[^\n]*\n.*?\n```", path.read_text(encoding="utf-8"), re.DOTALL))
            if prior - current:
                raise ValueError(f"Original Mermaid diagram removed or changed: {name}")
            retained = sum(prior.values())
            diagrams += retained
        with path.open("rb") as stream:
            after_sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
        inventory.append(
            {
                "path": name,
                "before_git_blob": blob,
                "after_git_blob": after_blob,
                "after_sha256": after_sha256,
                "bytes": path.stat().st_size,
                "unchanged": unchanged,
                "retained_mermaid_blocks": retained,
            }
        )
    return {
        "schema": "agialpha.successor.preservation.v1",
        "baseline": baseline,
        "files_preserved": len(inventory),
        "media_bytes_preserved": media,
        "mermaid_blocks_preserved": diagrams,
        "changed_files": sum(not item["unchanged"] for item in inventory),
        "inventory": inventory,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = check()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "inventory"}))


if __name__ == "__main__":
    main()
