# SPDX-License-Identifier: Apache-2.0
"""Fail-closed Git-object proof for the bounded, non-executable paper-only lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_service_worker import is_cache_asset, render_scripts
from scripts.release_plan import EDITORIAL_PATH, plan_for_full_scope, plan_for_proved_scope, prove_editorial_document
from scripts.research_papers import (
    CATALOG,
    HTML_END,
    HTML_START,
    README_END,
    README_START,
    asset_hashes,
    parse_catalog,
    preserve_catalog,
    render_readme,
    render_section,
    replace_block,
)

SCHEMA = "agialpha.paper-scope.v1"
WORKERS = (
    "docs/service-worker.js",
    "docs/assets/service-worker.js",
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js",
)
GENERATED = {"README.md", "docs/index.html", *WORKERS}
MAX_HISTORY = 200
MAX_BLOB = 25_000_000


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "--no-replace-objects", "-C", str(root), *args], capture_output=True, timeout=60)
    if result.returncode:
        raise ValueError(
            "Complete exact Git history is required: " + result.stderr.decode("utf-8", errors="replace")[:300]
        )
    return result.stdout


def commit(root: Path, sha: str) -> str:
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("An exact commit SHA is required")
    if git(root, "cat-file", "-t", sha).strip() != b"commit":
        raise ValueError("Source must identify a commit")
    return sha


def tree(root: Path, sha: str) -> dict[str, tuple[str, str]]:
    result = {}
    for record in git(root, "ls-tree", "-r", "-z", sha).split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, identity = metadata.decode("ascii").split()
        path = raw_path.decode("utf-8")
        result[path] = (mode, identity)
    return result


def blob(root: Path, inventory: dict[str, tuple[str, str]], path: str) -> bytes:
    if path not in inventory or inventory[path][0] != "100644":
        raise ValueError(f"Paper proof requires ordinary non-executable files: {path}")
    identity = inventory[path][1]
    size = int(git(root, "cat-file", "-s", identity))
    if not 0 <= size <= MAX_BLOB:
        raise ValueError("Source blob exceeds paper proof bounds")
    return git(root, "cat-file", "blob", identity)


def expected_workers(root: Path, inventory: dict[str, tuple[str, str]]) -> dict[str, bytes]:
    release = json.loads(blob(root, inventory, "alpha_factory_v1/demos/catalog.json"))["release"]
    assets = {
        name.removeprefix("docs/"): blob(root, inventory, name)
        for name in inventory
        if name.startswith("docs/") and is_cache_asset(Path(name.removeprefix("docs/")))
    }
    return {"docs/" + name: raw.encode() for name, raw in render_scripts(assets, release).items()}


def prove_transition(root: Path, before: str, after: str) -> dict[str, Any]:
    """Compare complete trees, preserve originals, and independently reproduce every output."""
    old, new = tree(root, before), tree(root, after)
    changed = {name for name in old.keys() | new.keys() if old.get(name) != new.get(name)}
    previous = parse_catalog(blob(root, old, CATALOG))
    current = parse_catalog(blob(root, new, CATALOG))
    preserve_catalog(previous, current)
    files = asset_hashes(current)
    allowed = {CATALOG, *files, *GENERATED, EDITORIAL_PATH}
    if changed - allowed:
        raise ValueError(
            "Software/mixed/unknown paths require full qualification: " + ", ".join(sorted(changed - allowed))
        )
    if any(name not in new for name in changed):
        raise ValueError("Paper-only changes cannot remove files")
    if EDITORIAL_PATH in changed:
        prove_editorial_document(blob(root, old, EDITORIAL_PATH), blob(root, new, EDITORIAL_PATH))
    for name, digest in files.items():
        raw = blob(root, new, name)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Paper bytes differ from catalog: " + name)
        if name.endswith(".pdf") and not raw.startswith(b"%PDF-"):
            raise ValueError("Catalog PDF lacks a PDF signature")
        if name.endswith(".tex"):
            raw.decode("utf-8")
    for name, start, end, renderer in (
        ("README.md", README_START, README_END, render_readme),
        ("docs/index.html", HTML_START, HTML_END, render_section),
    ):
        baseline = blob(root, old, name).decode("utf-8")
        if replace_block(baseline, start, end, renderer(previous)) != baseline:
            raise ValueError("Baseline paper rendering is not reproducible")
        if replace_block(baseline, start, end, renderer(current)).encode() != blob(root, new, name):
            raise ValueError("Untrusted change outside deterministic paper rendering: " + name)
    for inventory in (old, new):
        for name, expected in expected_workers(root, inventory).items():
            if blob(root, inventory, name) != expected:
                raise ValueError("Gallery worker differs from unchanged trusted generation: " + name)
    return {
        "before": before,
        "after": after,
        "paths": sorted(changed),
        "catalog_sha256": hashlib.sha256(blob(root, new, CATALOG)).hexdigest(),
        "has_paper_changes": bool(changed - {EDITORIAL_PATH}),
    }


def prove_paper_descendants(root: Path, base: str, head: str) -> dict[str, Any]:
    """Prove all newly introduced first-parent transitions, including side branches.

    Merge commits are compared with their first parent; each new side-branch commit
    is also checked. Thus a code change followed by a revert cannot hide in a net diff.
    """
    commit(root, base)
    commit(root, head)
    if base == head:
        return {"schema": SCHEMA, "mode": "unchanged", "software_commit": base, "paper_commit": head, "transitions": []}
    git(root, "merge-base", "--is-ancestor", base, head)
    history = git(root, "rev-list", "--reverse", "--topo-order", "--parents", f"{base}..{head}").decode().splitlines()
    if not history or len(history) > MAX_HISTORY:
        raise ValueError("Paper ancestry exceeds supported proof bounds")
    proofs = []
    for line in history:
        words = line.split()
        if len(words) < 2:
            raise ValueError("Incomplete paper ancestry")
        proofs.append(prove_transition(root, words[1], words[0]))
    final = prove_transition(root, base, head)
    plan = plan_for_proved_scope(base, head, has_paper_changes=final["has_paper_changes"])
    return {
        "schema": SCHEMA,
        "mode": "paper",
        "software_commit": base,
        "paper_commit": head,
        "catalog_sha256": final["catalog_sha256"],
        "release_plan": plan.to_dict(),
        "transitions": proofs,
    }


def classify(root: Path, base: str | None, head: str) -> dict[str, Any]:
    try:
        if not base or base == "0" * 40:
            raise ValueError("No trusted change base: full qualification")
        result = prove_paper_descendants(root, base, head)
        if result["mode"] != "paper" or not any(row["paths"] for row in result["transitions"]):
            raise ValueError("No substantive paper-only change")
        return result
    except (ValueError, OSError, UnicodeError, KeyError, TypeError, subprocess.SubprocessError) as error:
        return {
            "schema": SCHEMA,
            "mode": "full",
            "software_commit": head,
            "paper_commit": head,
            "reason": str(error),
            "release_plan": plan_for_full_scope(
                head if isinstance(head, str) and re.fullmatch(r"[0-9a-f]{40}", head) else None
            ).to_dict(),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--base")
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prove", action="store_true")
    args = parser.parse_args()
    result = (
        prove_paper_descendants(args.root, args.base, args.head)
        if args.prove
        else classify(args.root, args.base, args.head)
    )
    raw = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"mode={result['mode']}\n")
    print(raw, end="")


if __name__ == "__main__":
    main()
