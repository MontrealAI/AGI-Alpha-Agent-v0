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

from alpha_factory_v1.demos.catalog import REPO_ROOT, command_for, entries, environment_for, prerequisites_for
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from scripts.sync_demo_catalog_docs import synchronize


def validate_inventory() -> list[str]:
    """Require one current guide and a valid launch module for every directory."""
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
    if stale := synchronize(REPO_ROOT, check=True):
        paths = ", ".join(str(path.relative_to(REPO_ROOT)) for path in stale)
        raise ValueError(f"Stale catalog guides: {paths}. Run python -m scripts.sync_demo_catalog_docs")
    return sorted(actual)


def smoke() -> list[dict[str, object]]:
    """Run finite examples, including repeated lineage writes, with real processes."""
    records: list[dict[str, object]] = []
    for entry in entries():
        if not entry["smoke"]:
            continue
        prerequisites = prerequisites_for(entry)
        if not prerequisites["passed"]:
            raise ValueError(f"Missing demo prerequisites: {prerequisites}")
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="demo-catalog-") as temp:
            output = Path(temp)
            environment = environment_for(entry, output)
            environment["NO_DISCLAIMER"] = "1"
            command = command_for(entry, output)
            count = 2 if entry["id"] in {"meta_agentic_agi", "meta_agentic_agi_v2"} else 1
            results = [
                subprocess.run(command, cwd=output, env=environment, capture_output=True, text=True, timeout=90)
                for _ in range(count)
            ]
            for result in results:
                if result.returncode or not result.stdout.strip() and not result.stderr.strip():
                    raise RuntimeError(f"{entry['id']} failed: {result.stdout}\n{result.stderr}")
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
            records.append(
                {
                    "demo": entry["id"],
                    "mode": entry["mode"],
                    "runs": count,
                    "exit_codes": [result.returncode for result in results],
                    "seconds": round(time.monotonic() - started, 2),
                    "stdout": results[-1].stdout,
                    "stderr": results[-1].stderr,
                }
            )
            print(f"PASS {entry['id']} ({count} run{'s' if count > 1 else ''})", flush=True)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    inventory = validate_inventory()
    report = {"inventory": inventory, "smoke": smoke() if args.smoke else []}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Validated {len(inventory)} catalog entries")


if __name__ == "__main__":
    main()
