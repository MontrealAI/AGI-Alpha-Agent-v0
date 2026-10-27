# SPDX-License-Identifier: Apache-2.0
"""Compare identical library and fixture-retrieved bytes on one scoped fresh-recipient task."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import stat
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

STUDY = Path(__file__).resolve().parents[1]
MEMBERS = frozenset({"continuity.py", "mapping_validator.py", "expert_method.txt", "manifest.json"})
RECIPIENT = '''# SPDX-License-Identifier: Apache-2.0
"""Separate-process recipient; receives the same explicit snapshot grant in both arms."""
import importlib.util
import json
import sys
from pathlib import Path
import scipy

bundle, input_path, output_path = map(Path, sys.argv[1:])
request = json.loads(input_path.read_text())
assert request["grant"]["scope"] == "independent-snapshot-revalidation-only"
assert request["grant"]["execute_authorized"] is True
assert request["grant"]["rights_current"] is True
spec = importlib.util.spec_from_file_location("received_continuity", bundle / "continuity.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
answers = [module.process(request["packet"], c["mission"], c["event"]) for c in request["cases"]]
with output_path.open("x", encoding="utf-8") as out:
    out.write(json.dumps(answers, indent=2, allow_nan=False) + "\\n")
print(json.dumps({"python": sys.version.split()[0], "numpy": module.np.__version__, "scipy": scipy.__version__}))
'''


def sha(path: Path) -> str:
    """Hash exact local bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    """Preserve prior receipts by refusing an existing output file."""
    with path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def unpack(archive: Path, destination: Path) -> dict[str, str]:
    """Extract only the four declared ordinary files, with identical local permissions."""
    destination.mkdir()
    with zipfile.ZipFile(archive) as bundle:
        items = bundle.infolist()
        if len(items) != len(MEMBERS) or {item.filename for item in items} != MEMBERS:
            raise ValueError("Archive is not the frozen four-file v1 capability")
        for item in items:
            if item.is_dir() or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("Archive members must be ordinary files")
            path = destination / item.filename
            with path.open("xb") as output:
                output.write(bundle.read(item))
            path.chmod(0o644)
    return {name: sha(destination / name) for name in sorted(MEMBERS)}


def run(original: Path, authenticated: Path, fixture_receipt: Path, confirmation: Path, out: Path) -> dict[str, Any]:
    """Execute two independent recipients without measuring or assigning route advantages."""
    source_paths = {
        "original_archive": original,
        "authenticated_archive": authenticated,
        "fixture_receipt": fixture_receipt,
        "packet": confirmation / "raudenbush1985-packet.json",
        "mission": confirmation / "raudenbush1985-mission.json",
        "confirmed_cases": confirmation / "events-and-results.json",
    }
    before = {name: sha(path) for name, path in source_paths.items()}
    fixture = json.loads(fixture_receipt.read_text())
    if not (
        before["original_archive"] == before["authenticated_archive"] == fixture["artifact_sha256"]
        and fixture["passed"] == fixture["total"]
        and fixture["production_scope_changed"] is False
    ):
        raise ValueError("Identical v1 bytes and successful unchanged-scope fixture receipt are required")
    packet = json.loads(source_paths["packet"].read_text())
    mission = json.loads(source_paths["mission"].read_text())
    confirmed = [
        row for row in json.loads(source_paths["confirmed_cases"].read_text()) if row["dataset"] == "raudenbush1985"
    ]
    cases = []
    for row in confirmed:
        scoped_mission = copy.deepcopy(mission)
        mutation = row["mission_mutation"]
        if mutation:
            scoped_mission[mutation] = {"new": "purpose"} if mutation == "purpose" else False
        cases.append({"event": row["event"], "mission": scoped_mission})
    grant = {
        "principal": "same-local-research-recipient",
        "scope": "independent-snapshot-revalidation-only",
        "execute_authorized": True,
        "rights_current": True,
        "source_rights": "GPL (>=2) source packet retained separately; generic artifact Apache-2.0",
        "live_identity": False,
        "production_authority": False,
    }
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "recipient-input.json", {"grant": grant, "packet": packet, "cases": cases})
    with (out / "recipient.py").open("x", encoding="utf-8") as script:
        script.write(RECIPIENT)
    results, receipts = {}, []
    for arm, source in (("ordinary_library", original), ("authenticated_fixture", authenticated)):
        arm_root = out / arm
        arm_root.mkdir()
        copied = arm_root / "capability.zip"
        shutil.copyfile(source, copied)
        copied.chmod(0o644)
        members = unpack(copied, arm_root / "capability")
        output = arm_root / "answers.json"
        command = [
            sys.executable,
            "-I",
            "-B",
            str((out / "recipient.py").resolve()),
            str((arm_root / "capability").resolve()),
            str((out / "recipient-input.json").resolve()),
            str(output.resolve()),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False, cwd=arm_root)
        if completed.returncode != 0:
            write_json(arm_root / "failure.json", {"returncode": completed.returncode, "stderr": completed.stderr})
            raise RuntimeError(f"Recipient failed: {arm}; inspect its new failure receipt")
        results[arm] = json.loads(output.read_text())
        receipts.append(
            {
                "arm": arm,
                "archive_sha256": sha(copied),
                "member_sha256": members,
                "input_sha256": sha(out / "recipient-input.json"),
                "output_sha256": sha(output),
                "separate_process": True,
                "python_isolated_mode": True,
                "returncode": completed.returncode,
                "runtime": json.loads(completed.stdout),
                "timing_or_cost_measured": False,
            }
        )
    ordinary, mediated = results["ordinary_library"], results["authenticated_fixture"]
    controls = [
        {"name": "identical-executable-bytes", "passed": receipts[0]["member_sha256"] == receipts[1]["member_sha256"]},
        {"name": "identical-mission-and-grant", "passed": receipts[0]["input_sha256"] == receipts[1]["input_sha256"]},
        {"name": "identical-complete-results", "passed": ordinary == mediated},
        {
            "name": "same-semantic-dispositions-and-numeric-values-as-v1-confirmation",
            "passed": ordinary == [row["result"] for row in confirmed],
        },
        {
            "name": "original-inputs-unchanged",
            "passed": before == {name: sha(path) for name, path in source_paths.items()},
        },
    ]
    summary = {
        "schema": "same-content-library-equality/v1",
        "evidence": "OBSERVED_LOCAL_EXECUTION; AUTHENTICATED_ROUTE_USES_EXISTING_RESEARCH_FIXTURE",
        "passed": sum(check["passed"] for check in controls),
        "total": len(controls),
        "controls": controls,
        "cases_per_recipient": len(cases),
        "dispositions": dict(Counter(answer["status"] for answer in ordinary)),
        "numeric_results_per_recipient": sum(answer["numeric_result"] is not None for answer in ordinary),
        "scope": grant["scope"],
        "freshness": "Fresh to the capability recipient relative to the writing-study origin; previously used by the research team.",
        "authority": "Identical explicit local research grants; live ENS authentication not run.",
        "cost_or_latency_advantage_claimed": False,
        "graph_specific_technical_advantage": False,
        "original_input_sha256": before,
        "recipient_receipts": receipts,
        "limits": [
            "Equality control replays existing confirmation fixtures; it is not fresh independent efficacy confirmation.",
            "Both arms have identical content and permissions. Neither receives cumulative-event authority.",
            "Bytes do not establish source independence, current editorial validity, buyer acceptance or production authorization.",
            "The v1 artifact retains known post-confirmation defects; additive corrections are separately frozen and evaluated.",
        ],
    }
    write_json(out / "summary.json", summary)
    return summary


def main() -> None:
    """Run the equality control into a new result directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, default=STUDY / "instrument/capability-v1.zip")
    parser.add_argument(
        "--authenticated", type=Path, default=STUDY / "integration/results/capability-v1/received-v2.zip"
    )
    parser.add_argument(
        "--fixture-receipt", type=Path, default=STUDY / "integration/results/capability-v1/inherited-controls.json"
    )
    parser.add_argument("--confirmation", type=Path, default=STUDY / "results/confirmation-v1")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summary = run(args.original, args.authenticated, args.fixture_receipt, args.confirmation, args.out)
    print(json.dumps({key: summary[key] for key in ("passed", "total", "cases_per_recipient", "dispositions")}))
    raise SystemExit(0 if summary["passed"] == summary["total"] else 1)


if __name__ == "__main__":
    main()
