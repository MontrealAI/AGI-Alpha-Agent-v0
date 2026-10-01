# SPDX-License-Identifier: Apache-2.0
"""Validate the whole inventory and execute its finite offline launch contracts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import sys
from typing import Any

from alpha_factory_v1.demos.catalog import REPO_ROOT, command_for, entries, environment_for, prerequisites_for
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from scripts.sync_demo_catalog_docs import synchronize


def validate_inventory() -> list[str]:
    """Require one current guide and a valid launch module for every directory."""
    stale = synchronize(REPO_ROOT, check=True)
    if stale:
        raise ValueError("Stale demo inventories; run python -m scripts.sync_demo_catalog_docs: " + ", ".join(stale))
    base = REPO_ROOT / "alpha_factory_v1" / "demos"
    actual = {p.name for p in base.iterdir() if p.is_dir() and not p.name.startswith((".", "__"))}
    catalog = entries()
    declared = [entry["id"] for entry in catalog]
    if len(declared) != len(set(declared)) or set(declared) != actual:
        raise ValueError(f"Catalog inventory mismatch: {actual.symmetric_difference(declared)}")
    for entry in catalog:
        guide = base / entry["id"] / "README.md"
        if "<!-- CURRENT-DEMO:START -->" not in guide.read_text(encoding="utf-8"):
            raise ValueError(f"Missing current launch guide: {guide}")
        for field in ("title", "mode", "summary", "expected", "prerequisites", "limitations"):
            if not entry[field]:
                raise ValueError(f"Missing {field}: {entry['id']}")
        modules = entry["required_modules"]
        if not isinstance(modules, list) or any(
            not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_]\w*", name) for name in modules
        ):
            raise ValueError(f"Invalid prerequisite modules: {entry['id']}")
        if not isinstance(entry["offline"], bool):
            raise ValueError(f"Invalid offline setting: {entry['id']}")
        assets = entry["assets"]
        if not isinstance(assets, list) or any(not isinstance(name, str) for name in assets):
            raise ValueError(f"Invalid bundled files: {entry['id']}")
        for name in assets:
            path = (base / name).resolve()
            if not path.is_relative_to(base) or not path.is_file():
                raise ValueError(f"Missing or external bundled file: {entry['id']}: {name}")
        if entry["command"]:
            command = entry["command"]
            if command[:2] != ["python", "-m"]:
                raise ValueError("Launch commands must be explicit Python modules")
            module = REPO_ROOT.joinpath(*command[2].split("."))
            if not module.with_suffix(".py").is_file() and not (module / "__main__.py").is_file():
                raise ValueError(f"Missing launch module: {command[2]}")
    return sorted(actual)


def smoke() -> list[dict[str, Any]]:
    """Exercise every finite command and retain failures instead of losing the report."""
    records: list[dict[str, Any]] = []
    for entry in entries():
        if not entry["smoke"]:
            continue
        started = time.monotonic()
        record: dict[str, Any] = {
            "demo": entry["id"],
            "mode": entry["mode"],
            "runs": 0,
            "exit_codes": [],
            "stdout": "",
            "stderr": "",
            "status": "failed",
        }
        try:
            prerequisites = prerequisites_for(entry)
            record["prerequisites"] = prerequisites
            if not prerequisites["passed"]:
                record["status"] = "blocked"
                record["error"] = "Declared modules or bundled files are missing"
            else:
                with tempfile.TemporaryDirectory(prefix="demo-catalog-") as temp:
                    output = Path(temp)
                    environment = environment_for(entry, output)
                    environment["NO_DISCLAIMER"] = "1"
                    command = command_for(entry, output)
                    count = 2 if entry["id"] in {"meta_agentic_agi", "meta_agentic_agi_v2"} else 1
                    for _ in range(count):
                        record["runs"] += 1
                        result = subprocess.run(
                            command, cwd=output, env=environment, capture_output=True, text=True, timeout=90
                        )
                        record["exit_codes"].append(result.returncode)
                        record["stdout"], record["stderr"] = result.stdout, result.stderr
                        if result.returncode or not result.stdout.strip() and not result.stderr.strip():
                            raise RuntimeError("Command failed or produced no observable output")
                    if count == 2:
                        with sqlite3.connect(output / "lineage.sqlite") as db:
                            if db.execute("SELECT COUNT(*) FROM lineage").fetchone()[0] != 6:
                                raise AssertionError("Repeated runs did not preserve all six lineage records")
                    if entry["id"] == "meta_agentic_agi_v3":
                        from alpha_factory_v1.demos.meta_agentic_agi_v3.curriculum_lab import read_json, verify

                        runs = list(output.glob("*/run.json"))
                        assert len(runs) == 1
                        report = verify(read_json(runs[0]))
                        assert len(report["result"]["history"]) == 10
                        assert report["result"]["proposal"]["status"] == "UNAPPROVED"
                    record["status"] = "passed"
        except subprocess.TimeoutExpired as exc:
            record["status"] = "timeout"
            record["error"] = "Command exceeded its 90-second finite-launch limit"
            for key, value in (("stdout", exc.stdout), ("stderr", exc.stderr)):
                record[key] = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
        except (OSError, ValueError, RuntimeError, AssertionError, sqlite3.Error) as exc:
            record["error"] = str(exc)
        record["seconds"] = round(time.monotonic() - started, 2)
        records.append(record)
        print(f"{record['status'].upper()} {entry['id']} ({record['runs']} runs)", flush=True)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    inventory = validate_inventory()
    results = smoke() if args.smoke else []
    failed = [record["demo"] for record in results if record["status"] != "passed"]
    report = {
        "schema": "agialpha.demo.validation.v2",
        "inventory": inventory,
        "smoke": results,
        "smoke_requested": args.smoke,
        "passed": not failed,
        "scope": "Inventory and requested finite launch checks only; not universal production qualification.",
        "separate_acceptance": [entry["id"] for entry in entries() if not entry["smoke"]],
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Validated {len(inventory)} catalog entries; exercised {len(results)} finite commands")
    if failed:
        print("Finite launch checks did not pass: " + ", ".join(failed), file=sys.stderr)
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
