# SPDX-License-Identifier: Apache-2.0
"""Bounded supplemental public-tool run, separate from matched primary arms."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("study", type=Path)
    parser.add_argument("converter", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--freeze-sha256", required=True)
    parser.add_argument("--acquisition-sha256", required=True)
    args = parser.parse_args()
    study: Path = args.study.resolve()
    converter: Path = args.converter.resolve()
    output: Path = args.output.resolve()
    sys.path.insert(0, str(study / "src"))
    from production_campaign import children_cpu, now, run_process, save, sha, verify_freeze

    started_at = now()
    started_wall, started_self, started_children = time.perf_counter(), time.process_time(), children_cpu()
    output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).read_bytes()
    (output / "supplement_oasdiff.py").write_bytes(source)
    binary = study / "tools/oasdiff/oasdiff"
    manifest_path = study / "inputs/acquired/manifest.json"
    protocol_path = study / "protocol/production.json"
    manifest_bytes = manifest_path.read_bytes()
    if sha(manifest_bytes) != args.acquisition_sha256:
        raise ValueError("ACQUISITION_IDENTITY")
    manifest = json.loads(manifest_bytes)
    protocol = json.loads(protocol_path.read_text())
    commands: list[dict[str, Any]] = []
    versions: dict[str, Any] = {}
    pairs: list[dict[str, Any]] = []
    node_modules = converter.parent.parent
    lock = node_modules.parent / "package-lock.json"
    tool_files = [
        {"path": str(binary), "sha256": sha(binary.read_bytes())},
        {"path": str(lock), "sha256": sha(lock.read_bytes())},
    ]
    for path in sorted(node_modules.rglob("*")):
        if path.is_symlink():
            tool_files.append({"path": str(path), "symlinkTarget": str(path.readlink())})
        elif path.is_file():
            tool_files.append({"path": str(path), "sha256": sha(path.read_bytes())})
    save(output / "tool-source-binding.json", tool_files)

    def guard() -> None:
        verify_freeze(study, study / "protocol/production-freeze.json", args.freeze_sha256)
        if sha(manifest_path.read_bytes()) != args.acquisition_sha256:
            raise ValueError("ACQUISITION_CHANGED")

    def run(label: str, command: list[str]) -> dict[str, Any]:
        record = run_process(command, study, output / label, guard)
        record["label"] = label
        commands.append(record)
        save(output / "commands.json", commands)
        return record

    def stdout(label: str) -> str:
        return (output / (label + ".stdout")).read_text(errors="replace")

    def validation_summary(label: str) -> dict[str, Any]:
        text = stdout(label)
        match = re.search(r"(\d+) findings: (\d+) error, (\d+) warning, (\d+) info", text)
        if not match:
            return {"recognizedSummary": False, "rawOutput": label + ".stdout"}
        fields = ("findings", "errors", "warnings", "info")
        return {"recognizedSummary": True, **dict(zip(fields, map(int, match.groups()), strict=True))}

    guard()
    run("oasdiff-version", [str(binary), "--version"])
    run("node-version", ["node", "--version"])
    for before, after in protocol["primary_pairs"]:
        missing = [tag for tag in (before, after) if manifest["entries"][tag]["status"] != "ACQUIRED"]
        pair: dict[str, Any] = {"pair": [before, after], "supplementOnly": True, "matchedPrimaryReplacement": False}
        pairs.append(pair)
        if missing:
            pair.update(
                status="INPUT_ACQUISITION_FAILED",
                missing=missing,
                attempts=0,
                replacement=None,
                costTreatment="Shared acquisition failure charged in primary manifest, not duplicated here",
            )
            continue
        for tag in (before, after):
            if tag in versions:
                continue
            entry = manifest["entries"][tag]
            raw = study / entry["artifacts"]["spec"]["path"]
            if sha(raw.read_bytes()) != entry["artifacts"]["spec"]["sha256"]:
                raise ValueError("RAW_INPUT_CHANGED")
            label = tag.replace(".", "_")
            converted = output / (label + "-openapi.json")
            conversion = run(label + "-convert", ["node", str(converter), str(raw), "--outfile", str(converted)])
            raw_validation = run(label + "-raw-validate", [str(binary), "validate", str(raw)])
            version: dict[str, Any] = {
                "source": entry["artifacts"]["spec"],
                "conversion": conversion,
                "rawValidation": raw_validation,
                "rawValidationSummary": validation_summary(label + "-raw-validate"),
            }
            versions[tag] = version
            if conversion["exit"] != 0 or not converted.is_file():
                version["status"] = "CONVERSION_FAILED"
                continue
            validation = run(label + "-converted-validate", [str(binary), "validate", str(converted)])
            summary = validation_summary(label + "-converted-validate")
            version.update(
                convertedPath=converted.name,
                convertedSha256=sha(converted.read_bytes()),
                convertedValidation=validation,
                convertedValidationSummary=summary,
                status=(
                    "CONVERTED_VALIDATED"
                    if validation["exit"] == 0 and summary.get("errors") == 0
                    else "CONVERTED_VALIDATION_UNCONFIRMED"
                ),
            )
        label = before.replace(".", "_") + "-to-" + after.replace(".", "_")
        raw_before = study / manifest["entries"][before]["artifacts"]["spec"]["path"]
        raw_after = study / manifest["entries"][after]["artifacts"]["spec"]["path"]
        raw_command = run(
            label + "-raw-breaking", [str(binary), "breaking", str(raw_before), str(raw_after), "--format", "json"]
        )
        pair.update(
            rawBreaking=raw_command,
            rawBreakingInterpretation="INVALID_INPUT_FALSE_LEAD: raw Swagger2 is outside this OpenAPI3 comparator input contract; empty output cannot establish compatibility",
        )
        if any(versions[tag]["status"] != "CONVERTED_VALIDATED" for tag in (before, after)):
            pair["status"] = "CONVERSION_OR_VALIDATION_FAILED"
            continue
        converted_paths = [str(output / versions[tag]["convertedPath"]) for tag in (before, after)]
        for mode in ("breaking", "changelog", "diff"):
            record = run(label + "-converted-" + mode, [str(binary), mode, *converted_paths, "--format", "json"])
            pair[mode] = record
            try:
                value = json.loads(stdout(label + "-converted-" + mode))
                pair[mode + "FindingCount"] = len(value) if isinstance(value, list) else None
            except json.JSONDecodeError:
                pair[mode + "FindingCount"] = None
        pair["status"] = (
            "COMPLETE_SUPPLEMENT"
            if all(pair[mode]["exit"] == 0 for mode in ("breaking", "changelog", "diff"))
            else "TOOL_FAILED"
        )
        pair["interpretation"] = (
            "oasdiff findings span broader request/response semantics; counts and runtime are not the matched structural-dossier acceptance result; inspect findings rather than default exit code"
        )
        save(output / "pairs.json", pairs)
        save(output / "versions.json", versions)
    guard()
    for binding in tool_files:
        path = Path(binding["path"])
        if "sha256" in binding and sha(path.read_bytes()) != binding["sha256"]:
            raise ValueError("TOOL_SOURCE_CHANGED")
        if "symlinkTarget" in binding and str(path.readlink()) != binding["symlinkTarget"]:
            raise ValueError("TOOL_SYMLINK_CHANGED")
    save(output / "pairs.json", pairs)
    save(output / "versions.json", versions)
    summary = {
        "schema": "public-oasdiff-supplement/v1",
        "startedAt": started_at,
        "finishedAt": now(),
        "sourceSha256": sha(source),
        "productionFreezeSha256": args.freeze_sha256,
        "acquisitionManifestSha256": args.acquisition_sha256,
        "sourceQualification": "PASS",
        "protocolSha256": sha(protocol_path.read_bytes()),
        "plannedPairs": len(pairs),
        "completedPairs": sum(pair["status"] == "COMPLETE_SUPPLEMENT" for pair in pairs),
        "commands": len(commands),
        "wallSeconds": time.perf_counter() - started_wall,
        "cpuSeconds": time.process_time() - started_self + children_cpu() - started_children,
        "commandChildCpuSeconds": sum(command["cpuSeconds"] for command in commands),
        "sharedConversion": "Each available unique source converted and validated once, then cached; primary acquisition is separately charged once and unchanged",
        "scope": "Supplementary strongest practical public tool; broader semantics; not a replacement for the four matched primary arms",
        "constructionCost": "Supplement driver authoring elapsed/inference/human monetary cost not metered; unknown, not zero",
        "actualCompleteMonetaryCost": None,
        "actualHumanSeconds": None,
        "actualCollections": 0,
        "converterVersion": json.loads((converter.parent / "package.json").read_text())["version"],
        "oasdiffVersion": stdout("oasdiff-version").strip(),
        "findings": [
            {
                "pair": pair["pair"],
                "status": pair["status"],
                "breakingCount": pair.get("breakingFindingCount"),
                "changelogCount": pair.get("changelogFindingCount"),
            }
            for pair in pairs
        ],
    }
    save(output / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
