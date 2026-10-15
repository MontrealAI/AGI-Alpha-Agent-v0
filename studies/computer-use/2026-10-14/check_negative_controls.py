# SPDX-License-Identifier: Apache-2.0
"""Reject altered scope, incomplete records and inconsistent evidence before publication."""
from __future__ import annotations
import argparse
import json
import shutil
import tempfile
from pathlib import Path
from verify_and_replay import verify_results, verify_sources

CASES = (
    "missing",
    "changed-pass",
    "removed-review",
    "fake-human",
    "empty-vectors",
    "duplicate-recovery",
    "duplicate-vector",
    "duplicate-owner-run",
    "wrong-human-count",
    "missing-action-log",
    "changed-reader",
    "omitted-manifest-row",
    "duplicate-manifest-row",
    "unsafe-manifest-path",
    "changed-provenance",
    "forged-quality",
    "altered-action",
    "changed-recovered-quote",
    "wrong-recovery-summary",
    "wrong-vector-summary",
    "inconsistent-timing",
    "changed-wrapper",
    "symlinked-parent",
    "wrong-task-label",
)
SOURCE_CASES = {
    "fake-human",
    "changed-reader",
    "omitted-manifest-row",
    "duplicate-manifest-row",
    "unsafe-manifest-path",
    "changed-provenance",
    "changed-wrapper",
    "symlinked-parent",
}


def change(root: Path, case: str) -> None:
    target = root / "03_Evidence/acceptance/B_after.json"
    if case == "missing":
        target.unlink()
        return
    if case == "missing-action-log":
        (root / "03_Evidence/owner_familiar-no-profile_1.json").unlink()
        return
    if case in {"changed-reader", "changed-wrapper"}:
        (root / ("START_HERE.html" if case == "changed-reader" else "verify_and_replay.py")).write_text("changed\n")
        return
    if case == "changed-recovered-quote":
        (root / "03_Evidence/recovery/B-recovered-quote-5.json").write_text("{}\n")
        return
    if case in {"omitted-manifest-row", "duplicate-manifest-row", "unsafe-manifest-path"}:
        target = root / "SHA256SUMS"
        lines = target.read_text().splitlines()
        if case == "omitted-manifest-row":
            lines.pop()
        elif case == "duplicate-manifest-row":
            lines.append(lines[0])
        else:
            lines[0] = lines[0][:66] + "../outside.txt"
        target.write_text("\n".join(lines) + "\n")
        return
    if case == "symlinked-parent":
        original = root / "04_Reproduce"
        moved = root / "moved-source"
        original.rename(moved)
        original.symlink_to(moved, target_is_directory=True)
        return
    if case in {"removed-review", "duplicate-owner-run", "wrong-human-count", "forged-quality", "inconsistent-timing"}:
        target = root / "03_Evidence/OWNER_EFFORT.json"
    elif case in {"empty-vectors", "duplicate-vector", "wrong-vector-summary"}:
        target = root / "03_Evidence/acceptance/sha256_vectors.json"
    elif case in {"duplicate-recovery", "wrong-recovery-summary"}:
        target = root / "03_Evidence/recovery/RESULTS.json"
    elif case == "fake-human":
        target = root / "pilot/status.json"
    elif case == "changed-provenance":
        target = root / "SOURCE_PROVENANCE.json"
    elif case == "altered-action":
        target = root / "03_Evidence/owner_retained-profile_1.json"
    data = json.loads(target.read_text())
    if case == "changed-pass":
        data["tests"][0]["passed"] = False
    elif case == "removed-review":
        data["runs"][0]["reviewChecks"] = 0
    elif case == "fake-human":
        data["participantsObserved"] = 12
    elif case == "empty-vectors":
        data["tests"] = []
    elif case in {"duplicate-vector", "duplicate-recovery"}:
        data["tests"][-1] = data["tests"][-2]
    elif case == "duplicate-owner-run":
        data["runs"][2] = data["runs"][1]
    elif case == "wrong-human-count":
        data["participants"] = 12
    elif case == "changed-provenance":
        data["originalSourceFiles"] = {}
    elif case == "forged-quality":
        data["runs"][0]["qualityPassed"] = 34
    elif case == "altered-action":
        data["events"][-1]["value"] = "Unobserved action"
    elif case in {"wrong-recovery-summary", "wrong-vector-summary"}:
        data["passed"] = 0
    elif case == "inconsistent-timing":
        data["runs"][0]["mechanicalElapsedMs"] += 10
    elif case == "wrong-task-label":
        data["task"] = "A"
    else:
        raise ValueError("Unknown negative case: " + case)
    target.write_text(json.dumps(data))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    verify_results(args.replay)
    outcomes = []
    for case in CASES:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "copy"
            shutil.copytree(args.replay, root, ignore=shutil.ignore_patterns("__pycache__", ".ruff_cache"))
            change(root, case)
            try:
                (verify_sources if case in SOURCE_CASES else verify_results)(root)
            except (ValueError, FileNotFoundError) as error:
                outcomes.append({"case": case, "refused": True, "reason": str(error)})
            else:
                raise RuntimeError("Negative control incorrectly accepted: " + case)
    output = args.output or args.replay / "03_Evidence/VERIFIER_CHECKS.json"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "schema": "study-verifier-negative-controls/v2",
                    "passed": len(outcomes),
                    "total": len(CASES),
                    "checks": outcomes,
                },
                indent=2,
            )
            + "\n"
        )
    print(f"{len(outcomes)} verifier negative controls were refused as intended.")


if __name__ == "__main__":
    main()
