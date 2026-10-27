# SPDX-License-Identifier: Apache-2.0
"""Operate the bounded research offering without credentials or external effects."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from alpha_factory_v1.core.runtime.successor.protocol import safe_json_loads

from .schema import parse_brief


def read_json(path: Path, limit: int = 1_000_000) -> dict[str, Any]:
    """Read a bounded regular JSON file, refusing ambiguous duplicate members."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("expected a bounded regular JSON file")
    value = safe_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("expected one JSON object")
    return value


def verify_pack(path: Path) -> dict[str, Any]:
    """Verify exact inventory and independently recheck the named plan."""
    from .report import checked_delivery, render_pack

    expected = {"brief.json", "execution.json", "delivery.json", "plan.csv", "index.html"}
    if (
        path.is_symlink()
        or not path.is_dir()
        or {entry.name for entry in path.iterdir()} != expected | {"manifest.json"}
    ):
        raise ValueError("delivery directory must contain exactly the six public pack members")
    manifest = read_json(path / "manifest.json")
    if manifest.get("schema_name") != "resilient-placement-pack/v1" or set(manifest.get("files", {})) != expected:
        raise ValueError("unexpected delivery inventory")
    for name in sorted(expected):
        file = path / name
        if file.is_symlink() or not file.is_file() or file.stat().st_size > 1_000_000:
            raise ValueError("delivery member missing, symbolic or oversized")
        raw = file.read_bytes()
        if manifest["files"][name] != {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}:
            raise ValueError("delivery bytes differ from manifest: " + name)
    brief = parse_brief(read_json(path / "brief.json", 32_768))
    checked = checked_delivery(brief, read_json(path / "execution.json"))
    delivery = read_json(path / "delivery.json")
    if any(delivery.get(key) != checked[key] for key in ("outcome", "verification", "artifact_digest")):
        raise ValueError("delivery summary differs from independently checked output")
    with tempfile.TemporaryDirectory(prefix="placement-pack-verification-") as temporary:
        rebuilt = Path(temporary) / "pack"
        render_pack(brief.model_dump(), read_json(path / "execution.json"), rebuilt)
        for name in sorted(expected | {"manifest.json"}):
            if (path / name).read_bytes() != (rebuilt / name).read_bytes():
                raise ValueError("delivery differs from canonical checked packaging: " + name)
    return {"verified_files": len(expected), "brief_id": brief.brief_id, "research_acceptance": True}


def main() -> None:
    """Expose feasibility, research delivery, economics and read-only verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    check = commands.add_parser("check", help="Validate named inputs without executing a mission")
    check.add_argument("brief", type=Path)
    deliver = commands.add_parser("deliver", help="Run local research work; never a live sale or provider call")
    deliver.add_argument("brief", type=Path)
    deliver.add_argument("--output", type=Path, required=True)
    economics = commands.add_parser("economics", help="Print explicitly conditional same-offering economics")
    economics.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify-pack", help="Check exported bytes and exact finite result")
    verify.add_argument("pack", type=Path)
    args = parser.parse_args()
    if args.action == "check":
        brief = parse_brief(read_json(args.brief, 32_768))
        answer: dict[str, Any] = {
            "brief_id": brief.brief_id,
            "supported": True,
            "oracle_assignments": (len(brief.hosts) * (len(brief.hosts) - 1) // 2) ** len(brief.services),
            "execution_performed": False,
            "price_hypothesis_micro_usd": brief.price_micro_usd,
        }
    elif args.action == "deliver":
        from .report import render_pack
        from .runner import run_research

        raw = read_json(args.brief, 32_768)
        evidence = run_research(raw, args.output)
        execution = read_json(args.output / "actual" / "execution.json")
        pack = render_pack(raw, execution, args.output / "pack")
        answer = {"evidence": str(args.output / "evidence.json"), "pack": pack["path"], "summary": evidence["summary"]}
    elif args.action == "economics":
        from .economics import model

        if args.output.exists() or args.output.is_symlink():
            raise FileExistsError("choose a new economics output; preserve earlier evidence")
        value = model()
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        answer = {"output": str(args.output), "actual_customer_collections_micro_usd": 0}
    else:
        answer = verify_pack(args.pack)
    print(json.dumps(answer, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
