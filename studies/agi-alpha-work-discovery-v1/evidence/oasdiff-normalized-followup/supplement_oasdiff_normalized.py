# SPDX-License-Identifier: Apache-2.0
"""Separate normalized-input follow-up after the preserved raw YAML parser failure."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("study", type=Path)
    parser.add_argument("converter", type=Path)
    args = parser.parse_args()
    study: Path = args.study.resolve()
    converter: Path = args.converter.resolve()
    sys.path.insert(0, str(study / "src"))
    from production_campaign import children_cpu, now, run_process, save, sha, verify_freeze

    start_at = now()
    start_wall, start_self, start_children = time.perf_counter(), time.process_time(), children_cpu()
    original = study / "evidence/oasdiff-primary-supplement"
    output = study / "evidence/oasdiff-normalized-followup"
    output.mkdir(exist_ok=False)
    source = Path(__file__).read_bytes()
    (output / "supplement_oasdiff_normalized.py").write_bytes(source)
    parent_summary = json.loads((original / "summary.json").read_text())
    versions = json.loads((original / "versions.json").read_text())
    manifest_path = study / "inputs/acquired/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    old_entry = manifest["entries"]["v20.10.0"]["normalized"]
    old_input = study / old_entry["path"]
    new_input = original / versions["v23.0.0"]["convertedPath"]
    old_converted = output / "v20_10_0-openapi.json"
    binary = study / "tools/oasdiff/oasdiff"
    commands: list[dict[str, Any]] = []

    def guard() -> None:
        verify_freeze(study, study / "protocol/production-freeze.json", parent_summary["productionFreezeSha256"])
        if sha(manifest_path.read_bytes()) != parent_summary["acquisitionManifestSha256"]:
            raise ValueError("ACQUISITION_CHANGED")
        if sha(old_input.read_bytes()) != old_entry["sha256"]:
            raise ValueError("NORMALIZED_INPUT_CHANGED")
        if sha(new_input.read_bytes()) != versions["v23.0.0"]["convertedSha256"]:
            raise ValueError("CACHED_CONVERSION_CHANGED")
        for binding in json.loads((original / "tool-source-binding.json").read_text()):
            if "sha256" in binding and sha(Path(binding["path"]).read_bytes()) != binding["sha256"]:
                raise ValueError("TOOL_SOURCE_CHANGED")

    def run(label: str, command: list[str]) -> dict[str, Any]:
        result = run_process(command, study, output / label, guard)
        result["label"] = label
        commands.append(result)
        save(output / "commands.json", commands)
        return result

    conversion = run("conversion", ["node", str(converter), str(old_input), "--outfile", str(old_converted)])
    findings: dict[str, Any] = {}
    validated = False
    if conversion["exit"] == 0:
        validation = run("validation", [str(binary), "validate", str(old_converted)])
        validation_text = (output / "validation.stdout").read_text()
        validated = validation["exit"] == 0 and "findings: 0 error," in validation_text
        if validated:
            for mode in ("breaking", "changelog", "diff"):
                result = run(mode, [str(binary), mode, str(old_converted), str(new_input), "--format", "json"])
                value = json.loads((output / (mode + ".stdout")).read_text()) if result["exit"] == 0 else None
                findings[mode] = {"exit": result["exit"], "count": len(value) if isinstance(value, list) else None}
    guard()
    summary = {
        "schema": "public-oasdiff-normalized-followup/v1",
        "startedAt": start_at,
        "finishedAt": now(),
        "sourceSha256": sha(source),
        "status": (
            "COMPLETE_SUPPLEMENT"
            if validated and all(item["exit"] == 0 for item in findings.values())
            else "FOLLOWUP_FAILED"
        ),
        "pair": ["v20.10.0", "v23.0.0"],
        "sourceQualification": "PASS",
        "parentSummarySha256": sha((original / "summary.json").read_bytes()),
        "inputNormalized": old_entry,
        "cachedNewConversion": versions["v23.0.0"]["convertedSha256"],
        "convertedOldSha256": sha(old_converted.read_bytes()) if old_converted.exists() else None,
        "primaryRerun": False,
        "sourceRepaired": False,
        "replacementQuestion": None,
        "interpretation": "Separate post-primary public-tool follow-up using the exact existing normalized JSON after the first-pass YAML parser failure. The failure and both costs remain. Primary inputs, acceptance, denominators and results are unchanged.",
        "costAllocation": "Cached v23 conversion and original acquisition charged in their original records once, not duplicated; add this follow-up's total CPU/wall to the first supplement for complete observed cost.",
        "findings": findings,
        "commands": len(commands),
        "wallSeconds": time.perf_counter() - start_wall,
        "cpuSeconds": time.process_time() - start_self + children_cpu() - start_children,
        "commandChildCpuSeconds": sum(item["cpuSeconds"] for item in commands),
        "actualCompleteMonetaryCost": None,
        "actualHumanSeconds": None,
        "actualCollections": 0,
    }
    save(output / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
