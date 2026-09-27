# SPDX-License-Identifier: Apache-2.0
"""Preserve the original factory paths, diagrams and media while checking new entry points."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

BASE = "72ca8082329fcbab88fb1e47825774f8a4bb218b"
ROOT = Path(__file__).resolve().parents[1]
MEDIA = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf", ".pptx", ".mp4"}


def check() -> dict[str, object]:
    """Require retention against the immutable pre-update tree, not a moving branch."""
    rows = subprocess.check_output(["git", "ls-tree", "-rz", BASE, "alpha_factory_v1"], cwd=ROOT).split(b"\0")
    diagrams = media = paths = 0
    for row in rows:
        if not row:
            continue
        metadata, encoded = row.split(b"\t", 1)
        name = encoded.decode("utf-8")
        path = ROOT / name
        if not path.is_file():
            raise ValueError(f"Original factory path missing: {name}")
        paths += 1
        if path.suffix.lower() in MEDIA:
            old_hash = metadata.split()[2].decode()
            current_hash = subprocess.check_output(["git", "hash-object", name], cwd=ROOT, text=True).strip()
            if old_hash != current_hash:
                raise ValueError(f"Original factory media changed: {name}")
            media += 1
        if path.suffix == ".md":
            before = subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT).decode("utf-8")
            original = Counter(re.findall(r"```mermaid[^\n]*\n.*?\n```", before, re.S))
            current = Counter(re.findall(r"```mermaid[^\n]*\n.*?\n```", path.read_text(encoding="utf-8"), re.S))
            if original - current:
                raise ValueError(f"Original Mermaid block removed or changed: {name}")
            diagrams += sum(original.values())
    examples = {}
    for source in sorted((ROOT / "examples/missions").glob("*.json")):
        packaged = ROOT / "alpha_factory_v1/core/runtime/examples" / source.name
        if source.read_bytes() != packaged.read_bytes():
            raise ValueError(f"Packaged mission differs from canonical example: {source.name}")
        examples[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    for name in (
        "alpha_factory_v1/README.md",
        "alpha_factory_v1/docs/README.md",
        "alpha_factory_v1/backend/README.md",
        "docs/agent/FACTORY_GUIDE.md",
    ):
        source = ROOT / name
        text = re.sub(r"```.*?```", "", source.read_text(encoding="utf-8"), flags=re.S)
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if link.startswith(("http:", "https:", "mailto:", "#")):
                continue
            destination = link.split("#", 1)[0]
            if not (source.parent / destination).exists():
                raise ValueError(f"Broken factory guide link: {name}: {link}")
    return {
        "baseline": BASE,
        "factory_paths_preserved": paths,
        "mermaid_blocks_preserved": diagrams,
        "media_preserved": media,
        "packaged_examples": examples,
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
