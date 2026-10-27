# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CLOCK_FIELDS = frozenset(
    {"created_at_utc", "started_at_utc", "finished_at_utc", "elapsed_seconds", "wall_clock_seconds"}
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: semantic(item) for key, item in value.items() if key not in CLOCK_FIELDS}
    if isinstance(value, list):
        return [semantic(item) for item in value]
    return value


def command(args: list[str], output: Path, label: str, environment: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(args, cwd=ROOT, env=environment, text=True, capture_output=True)
    (output / f"{label}.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    receipt = {"label": label, "command": args, "returncode": completed.returncode, "log": f"{label}.log"}
    if completed.returncode:
        raise RuntimeError(f"{label} failed; see {output / (label + '.log')}")
    return receipt


def reproduce(output: Path, include_native_trust: bool, repository_root: Path) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Choose a new or empty output directory; historical results are never overwritten")
    output.mkdir(parents=True, exist_ok=True)
    economic_freeze = json.loads((ROOT / "economics/final_results/policy_freeze.json").read_text())
    if sha(ROOT / "economics/run.py") != economic_freeze["runner_sha256"]:
        raise ValueError("Economic runner differs from its final freeze")
    economic_config = json.loads((ROOT / "configs/economics.json").read_text())
    canonical_config = json.dumps(economic_config, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if hashlib.sha256(canonical_config).hexdigest() != economic_freeze["config_sha256"]:
        raise ValueError("Economic configuration differs from its final freeze")
    if economic_freeze["fresh_seed"] != 730552:
        raise ValueError("Unexpected commercial confirmation seed")
    environment = dict(os.environ, MPLCONFIGDIR=str(output / "mpl-cache"))
    commands = [
        command(
            [sys.executable, str(ROOT / "src/reproduce_technical.py"), "--out", str(output / "technical")],
            output,
            "technical",
            environment,
        ),
        command(
            [sys.executable, str(ROOT / "economics/run.py"), "all", "--output", str(output / "economics")],
            output,
            "economics",
            environment,
        ),
    ]
    economic_comparisons = []
    for expected in sorted((ROOT / "economics/final_results").glob("*.json")):
        observed = output / "economics" / expected.name
        record = {"file": expected.name, "present": observed.is_file(), "semantic_match": False, "byte_match": False}
        if observed.is_file():
            record["semantic_match"] = semantic(json.loads(observed.read_text())) == semantic(
                json.loads(expected.read_text())
            )
            record["byte_match"] = sha(observed) == sha(expected)
        economic_comparisons.append(record)
    technical = json.loads((output / "technical/reproduction_receipt.json").read_text())
    native: dict[str, Any] = {
        "requested": include_native_trust,
        "executed": False,
        "reason": "Optional existing-repository TrustRegistry fixture; standalone technical/economic replay needs no native admission",
    }
    if include_native_trust:
        native_source = repository_root / "alpha_factory_v1/core/runtime/successor/trust.py"
        if not native_source.is_file():
            raise FileNotFoundError(
                "Native trust replay needs an existing canonical repository; pass --repository-root"
            )
        mirror = output / "technical/study"
        script = Path("technical/independent_audit/trust_fixture.py")
        shutil.copy2(ROOT / script, mirror / script)
        manifest = json.loads((ROOT / "technical/capability_manifest.json").read_text())
        references = ["technical/capability_manifest.json", *manifest["evaluation"]]
        for reference in references:
            source = (ROOT / reference).resolve()
            if not source.is_relative_to(ROOT):
                raise ValueError("Manifest evidence must stay inside this study")
            destination = mirror / reference
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        native_environment = dict(environment)
        native_environment["PYTHONPATH"] = os.pathsep.join(
            x for x in (str(repository_root), environment.get("PYTHONPATH", "")) if x
        )
        commands.append(command([sys.executable, str(mirror / script)], output, "native_trust", native_environment))
        actual = json.loads((mirror / "technical/independent_audit/trust_fixture_results.json").read_text())
        previous = json.loads((ROOT / "technical/independent_audit/trust_fixture_results.json").read_text())
        expected_checks = [(item["name"], item["passed"]) for item in previous["checks"]]
        actual_checks = [(item["name"], item["passed"]) for item in actual["checks"]]
        native = {
            "requested": True,
            "executed": True,
            "passed": actual["passed"],
            "semantic_checks_reproduced": actual_checks == expected_checks,
            "checks": len(actual_checks),
            "native_source_sha256": sha(native_source),
            "principal_is_live_ens": actual["principal_is_live_ens"],
            "execution_or_admission_granted": actual["execution_or_admission_granted"],
            "comparison": "Ephemeral keys/signatures change; compare signed-manifest binding and the ten named semantic outcomes",
        }
    checks = {
        "technical_reproduced": technical["reproduced"],
        "all_economic_json_semantics_match": all(row["semantic_match"] for row in economic_comparisons),
        "optional_native_trust_reproduced": not include_native_trust
        or bool(native["passed"] and native["semantic_checks_reproduced"]),
    }
    receipt = {
        "reproduced": all(checks.values()),
        "checks": checks,
        "commands": commands,
        "economic_confirmation_seed": economic_freeze["fresh_seed"],
        "economic_worlds": economic_freeze["fresh_worlds"],
        "economic_json_comparisons": economic_comparisons,
        "clock_fields_excluded_from_semantic_comparison": sorted(CLOCK_FIELDS),
        "technical_summary": {
            "source_rows": technical["public_summary"],
            "conventional_decisions": technical["independent_public_decisions"],
            "structural_cases": technical["independent_structural_cases"],
            "format_parity": technical["format_semantic_parity"],
        },
        "native_trust": native,
        "actual_collected_service_revenue": 0,
        "actual_complete_research_cost": None,
        "scope": "Reproduction of executed software and explicitly modeled commercial worlds. Preserved failures remain failures; no customer receipts, live ENS or production qualification are created.",
        "wrapper_sha256": sha(Path(__file__)),
    }
    (output / "reproduction_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    if not receipt["reproduced"]:
        raise RuntimeError("A saved result did not reproduce; inspect the preserved receipt")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-native-trust", action="store_true")
    parser.add_argument("--repository-root", type=Path, default=ROOT.parents[1])
    args = parser.parse_args()
    result = reproduce(args.output.resolve(), args.include_native_trust, args.repository_root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
