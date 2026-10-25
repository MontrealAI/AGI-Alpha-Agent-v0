# SPDX-License-Identifier: Apache-2.0
"""Narrow post-delivery checks; no benchmark rerun or source modification."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import callsite_adapters as adapter


def main() -> None:
    checks = []

    def passed(name: str) -> None:
        checks.append({"name": name, "passed": True})

    selection = json.loads((ROOT / "protocol/selection.json").read_text())
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest(ROOT / selection["selected_source"]) == selection["selected_source_sha256"]
    assert (ROOT / selection["selected_source"]).read_bytes() == (ROOT / selection["template_source"]).read_bytes()
    passed("retained reader is byte-identical to the A-selected source")
    assert digest(ROOT / selection["qualification_path"]) == selection["qualification_sha256"]
    assert json.loads((ROOT / selection["qualification_path"]).read_text())["passed"]
    passed("selection binds the exact successful A qualification record")
    for mission, expected in (("A", 20), ("B", 10)):
        rows = [json.loads(line) for line in (ROOT / f"development/callsite-benchmark/{mission}-raw.jsonl").read_text().splitlines()]
        assert len(rows) == expected and all(row["passed"] for row in rows)
        key = "output_inventory_sha256" if mission == "A" else "rendered_inventory_sha256"
        assert len({row[key] for row in rows}) == 1
        passed(f"all {expected} {mission} timed outputs have one exact byte inventory")

    def unreachable(*args, **kwargs):
        raise AssertionError("reader must not run for an ineligible paper mode")

    try:
        adapter.expected_workers(Path("unused"), "f" * 40, {adapter.CATALOG: ("100755", "0" * 40)}, unreachable, lambda _: True, unreachable)
    except ValueError as error:
        assert "non-executable" in str(error)
    else:
        raise AssertionError("executable paper input was accepted")
    passed("paper executable-file refusal happens before byte retrieval")

    called = []
    def reader(root, commit, paths, **bounds):
        called.append(bounds)
        return {adapter.CATALOG: b'{"release":"test"}'}
    try:
        adapter.expected_workers(Path("unused"), "f" * 40, {adapter.CATALOG: ("100644", "0" * 40)}, reader, lambda _: True, unreachable, max_blob=123)
    except ValueError as error:
        assert "inventory differs" in str(error)
    else:
        raise AssertionError("stale inventory identity was accepted")
    assert called == [{"max_file": 123, "total": 123}]
    passed("stale caller identity refuses before rendering and propagates MAX_BLOB")

    patch = ROOT / "patches/0001-add-bounded-snapshot-reader-and-adapters.patch"
    result = subprocess.run(["git", "-C", str(ROOT.parent / "alpha"), "apply", "--check", str(patch)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    passed("additive review patch applies cleanly to pinned upstream without application")
    output = {"schema": "foundry-delivery-check/v1", "checks": checks, "count": len(checks), "passed": True, "no_benchmark_rerun": True,
              "prior_attempt": {"status": "check-script schema error", "error": "KeyError: output_inventory_sha256 on B rows; B correctly uses rendered_inventory_sha256", "changed_evidence": False}}
    (ROOT / "development/delivery-checks.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
