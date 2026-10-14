# SPDX-License-Identifier: Apache-2.0
"""Fail-closed verification around the preserved historical mechanical harness."""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "A_before": (8, 31),
    "A_after": (31, 31),
    "B_before": (9, 35),
    "B_after": (35, 35),
    "B_without-portability-fix": (29, 35),
}
APP_HASHES = {
    "A_after": "fde4d2f873c89356444c01ce3eb01fbc87dd2391d968abcc1fb6d47203a1baab",
    "B_after": "5d59f7eda0a3e9b217417ce7e95d1212e6e2ef7ad3af6bb8936f1b5d75a95dbf",
    "B_without-portability-fix": "5097ce8b3d6cb2f95fbc5a31c12f52a16dbc53393390e7d55b049c45381cf599",
}

TEST_OUTCOME_DIGESTS = {
    "A_before": "f8e2d6c5a349cb599e1e5cb7ec125d3b076faf370b8cc2432c13480789337e0f",
    "A_after": "250bbacc6f2d9446cd8fa93a6d6c74a8807fce25a5d346c6f1229594262e0459",
    "B_before": "f27575c4e09811be5687622de3f105d3d95344e7be70a6b56d7f8a32bd960a9a",
    "B_after": "d62e861afcbebeb7c47fa2a14d1a87c0b210efb0d129b9c162fb06aa93b5d259",
    "B_without-portability-fix": "8bef51c0885a2afc7cea3fcc0d22584f2c78016e6fa6cd49bd1c4ed8c142b9e8",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources(root: Path) -> dict:
    provenance = json.loads((root / "SOURCE_PROVENANCE.json").read_text())
    for name, expected in provenance["originalSourceFiles"].items():
        path = root / name
        if path.is_symlink() or digest(path) != expected:
            raise ValueError("Original source mismatch: " + name)
    for case, expected in APP_HASHES.items():
        task, variant = case.split("_", 1)
        if digest(root / f"02_Work_Products/Task_{task}/{variant}/index.html") != expected:
            raise ValueError("Generated application mismatch: " + case)
    status = json.loads((root / "pilot/status.json").read_text())
    if status["participantsObserved"] != 0 or status["results"] is not None:
        raise ValueError("This publication has no observed human results")
    return provenance


def verify_results(root: Path) -> dict:
    summary = {}
    for case, counts in EXPECTED.items():
        data = json.loads((root / f"03_Evidence/acceptance/{case}.json").read_text())
        checks = data["tests"]
        if not checks or len(checks) != counts[1] or sum(x["passed"] is True for x in checks) != counts[0]:
            raise ValueError("Unexpected individual acceptance outcomes: " + case)
        if (data["passed"], data["total"]) != counts:
            raise ValueError("Acceptance summary mismatch: " + case)
        if len({x["test"] for x in checks}) != len(checks):
            raise ValueError("Duplicate acceptance names")
        signature = hashlib.sha256(
            json.dumps([(x["test"], x["passed"]) for x in checks], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if signature != TEST_OUTCOME_DIGESTS[case]:
            raise ValueError("Individual test pattern differs: " + case)
        if data["sourceSha256"] != digest(root / f"02_Work_Products/Task_{data['task']}/{data['variant']}/index.html"):
            raise ValueError("Result refers to different source bytes")
        summary[case] = {"passed": data["passed"], "total": data["total"]}
    recovery = json.loads((root / "03_Evidence/recovery/RESULTS.json").read_text())
    if len(recovery["tests"]) != 19 or not all(x["passed"] is True for x in recovery["tests"]):
        raise ValueError("Recovery check missing or failed")
    effort = json.loads((root / "03_Evidence/OWNER_EFFORT.json").read_text())
    runs = effort["runs"]
    if len(runs) != 10:
        raise ValueError("Owner replays incomplete")
    for mode, count in [("familiar-no-profile", 14), ("retained-profile", 11)]:
        group = [x for x in runs if x["mode"] == mode]
        if len(group) != 5 or any(
            (x["actions"], x["freshScopeApprovals"], x["reviewChecks"]) != (count, 1, 3) for x in group
        ):
            raise ValueError("Owner controls or authorization changed")
    vectors = json.loads((root / "03_Evidence/acceptance/sha256_vectors.json").read_text())
    if len(vectors["tests"]) != 105 or not all(x["passed"] is True for x in vectors["tests"]):
        raise ValueError("Hash comparison vector missing or failed")
    return {
        "sha256Vectors": 105,
        "schema": "study-fresh-replay/v1",
        "acceptance": summary,
        "recovery": {"passed": 19, "total": 19},
        "ownerControls": {"noProfile": 14, "retainedProfile": 11, "runs": 10},
        "humanParticipants": 0,
        "repositoryRuntimeExecuted": False,
        "modelApiCalls": 0,
        "interpretation": "Fresh mechanical replay, not fresh model generation, independent replication, or human productivity evidence.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    verify_sources(ROOT)
    if args.verify_only:
        print("Original source and generated application hashes verified; real-user results remain empty.")
        return
    if not args.output:
        parser.error("--output must name a NEW directory outside this kit")
    dest = args.output.resolve()
    if dest.exists() or dest.is_relative_to(ROOT) or ROOT.is_relative_to(dest):
        parser.error("Choose a new destination outside the source kit")
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns("__pycache__", ".venv", "*.zip"))
    for relative in [
        "03_Evidence/acceptance",
        "03_Evidence/downloads",
        "03_Evidence/screenshots",
        "03_Evidence/recovery",
        "08_Metrics",
    ]:
        (dest / relative).mkdir(parents=True, exist_ok=True)
    commands = [
        ["browser_acceptance.py", "--tasks", "A", "B", "--variants", "before", "after"],
        ["browser_acceptance.py", "--tasks", "B", "--variants", "without-portability-fix"],
        ["recovery_tests.py"],
        ["owner_effort.py"],
    ]
    for cmd in commands:
        subprocess.run(
            [sys.executable, str(dest / "04_Reproduce" / cmd[0]), *cmd[1:]],
            check=True,
            timeout=240,
            env=os.environ.copy(),
        )
    result = verify_results(dest)
    verify_sources(ROOT)
    (dest / "FRESH_RESULTS.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
