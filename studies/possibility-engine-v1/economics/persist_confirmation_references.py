# SPDX-License-Identifier: Apache-2.0
"""Persist existing frozen reference calculations; introduce no new samples.

The frozen confirmation runner already computes these two groups but saves only
their summaries. This reporting companion saves their complete journals using
the same frozen functions and independently issued seeds. It refuses any changed
frozen file and requires byte-for-byte-equivalent summary values.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import model


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parent
    study = root.parent
    freeze_path = root / "FREEZE.json"
    freeze = json.loads(freeze_path.read_text())
    for name, expected in freeze["sha256"].items():
        if sha256(root / name) != expected:
            raise RuntimeError(f"Frozen economic file changed: {name}")
    bank_path = study / "evidence" / "confirmation" / "seeds.json"
    bank = json.loads(bank_path.read_text())
    if sha256(study / "FREEZE.json") != bank["freeze_sha256"]:
        raise RuntimeError("Study freeze differs from independently issued seed bank")
    seeds = bank["economic_seeds"]
    policy = json.loads((root / "selected_policy.json").read_text())
    original = json.loads((root / "confirmation" / "summary.json").read_text())
    manifest: list[dict[str, str]] = []
    summaries: dict[str, Any] = {}
    groups = {
        "conventional_same_arrangement": [
            model.run_world(seed, "reference", policy, True) for seed in seeds
        ],
        "no_launch_after_research": [model.run_no_launch(seed) for seed in seeds],
    }
    output = root / "confirmation" / "supplementary_references"
    for name, worlds in groups.items():
        summaries[name] = model.summarize(worlds)
        if summaries[name] != original[name]:
            raise AssertionError(f"Reference replay differs from frozen output: {name}")
        directory = output / name
        directory.mkdir(parents=True, exist_ok=True)
        for world in worlds:
            path = directory / f"{world['seed']}.json"
            path.write_text(json.dumps(world, separators=(",", ":")) + "\n")
            manifest.append(
                {"path": str(path.relative_to(output)), "sha256": sha256(path)}
            )
    report = {
        "scope": "Persistence of the original reference groups; not new samples",
        "economic_freeze_sha256": sha256(freeze_path),
        "study_freeze_sha256": bank["freeze_sha256"],
        "seed_bank_sha256": sha256(bank_path),
        "original_summary_sha256": sha256(root / "confirmation" / "summary.json"),
        "exact_summary_match": True,
        "worlds_per_group": len(seeds),
        "summaries": summaries,
        "world_manifest": manifest,
    }
    for name, expected in freeze["sha256"].items():
        if sha256(root / name) != expected:
            raise RuntimeError(f"Frozen economic file changed during replay: {name}")
    (output / "persistence_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"groups": list(groups), "worlds": len(manifest), "exact_summary_match": True}))


if __name__ == "__main__":
    main()
