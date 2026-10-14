# SPDX-License-Identifier: Apache-2.0
"""Fail-closed verification around the preserved historical mechanical harness."""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

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


RECOVERY_NAMES = ['Actual worker termination after durable checkpoint', 'Fresh-process artifact restore 1', 'Fresh-process artifact restore 2', 'Fresh-process artifact restore 3', 'Fresh-process artifact restore 4', 'Fresh-process artifact restore 5', 'Tampered checkpoint refused', 'Older valid snapshot rejected against newer retained head', 'Wrong task refused', 'Unknown-effect checkpoint stops; no replay attempted', 'Parent-directory path rejected even with valid hash', 'Existing recovered work never overwritten', 'No approval or authority inherited', 'Unsaved work absence is a failure, not invented recovery', 'Fresh-browser offline recovery 1: exact quote bytes and new review', 'Fresh-browser offline recovery 2: exact quote bytes and new review', 'Fresh-browser offline recovery 3: exact quote bytes and new review', 'Fresh-browser offline recovery 4: exact quote bytes and new review', 'Fresh-browser offline recovery 5: exact quote bytes and new review']
OWNER_TRACE_SIGNATURES = {'familiar-no-profile': 'bfbcd797de9c68659643d478d3526a4ea620cb7ff0fd1a4048d4ba98f80d30f9', 'retained-profile': 'af028f1371864578052b28d779bb162808b34bd099ac2720606a5da15e08c650'}

PROVENANCE_SHA256 = "4056fed3c8a113256e8c576f956f59245883f671c32a3b767a91d04d9a2f227c"


def safe_file(root: Path, name: str) -> Path:
    """Require one canonical, regular file below root, with no symlink components."""
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("Unsafe evidence path")
    parts = PurePosixPath(name).parts
    if name.startswith("/") or name != "/".join(parts) or any(p in {".", ".."} for p in parts):
        raise ValueError("Non-canonical evidence path: " + name)
    if any(ord(c) < 32 for c in name):
        raise ValueError("Control character in evidence path")
    path = root.resolve()
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("Symlink in evidence path: " + name)
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("Missing evidence file: " + name)
    return path


def load_json(path: Path) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field: " + key)
            result[key] = value
        return result
    if path.stat().st_size > 5_000_000:
        raise ValueError("Oversized evidence JSON")
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique,
                       parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Non-finite JSON")))
    if not isinstance(value, dict):
        raise ValueError("Evidence must be a JSON object")
    return value


def manifest_files(root: Path) -> dict[str, str]:
    """Check every named publication file, not only the original applications."""
    manifest = safe_file(root, "SHA256SUMS")
    rows = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  (.+)", line)
        if not match or match[2] in rows or match[2] == "SHA256SUMS":
            raise ValueError("Invalid or duplicate checksum row")
        expected, name = match.groups()
        if digest(safe_file(root, name)) != expected:
            raise ValueError("Publication checksum mismatch: " + name)
        rows[name] = expected
    from package_clean import publication_names
    if set(rows) != publication_names(root):
        raise ValueError("Publication manifest membership differs")
    return rows


def verify_original_sources(root: Path) -> dict:
    provenance_path = safe_file(root, "SOURCE_PROVENANCE.json")
    if digest(provenance_path) != PROVENANCE_SHA256:
        raise ValueError("Original provenance record changed")
    provenance = load_json(provenance_path)
    for name, expected in provenance["originalSourceFiles"].items():
        if digest(safe_file(root, name)) != expected:
            raise ValueError("Original source mismatch: " + name)
    for case, expected in APP_HASHES.items():
        task, variant = case.split("_", 1)
        if digest(safe_file(root, f"02_Work_Products/Task_{task}/{variant}/index.html")) != expected:
            raise ValueError("Generated application mismatch: " + case)
    status = load_json(safe_file(root, "pilot/status.json"))
    if type(status["participantsObserved"]) is not int or status["participantsObserved"] != 0 or status["results"] is not None:
        raise ValueError("This publication has no observed human results")
    return provenance


def verify_sources(root: Path) -> dict:
    provenance = verify_original_sources(root)
    manifest_files(root)
    return provenance


def outcome_signature(rows: list) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def verify_results(root: Path) -> dict:
    verify_sources(root)
    summary = {}
    for case, counts in EXPECTED.items():
        data = load_json(safe_file(root, f"03_Evidence/acceptance/{case}.json"))
        checks = data["tests"]
        if (data["task"], data["variant"]) != tuple(case.split("_", 1)):
            raise ValueError("Acceptance task/variant mismatch: " + case)
        if not isinstance(checks, list) or any(type(x.get("passed")) is not bool for x in checks):
            raise ValueError("Acceptance outcomes must be booleans")
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
    recovery = load_json(safe_file(root, "03_Evidence/recovery/RESULTS.json"))
    expected_recovery_names = RECOVERY_NAMES
    checks = recovery["tests"]
    if [x["test"] for x in checks] != expected_recovery_names or not all(x["passed"] is True for x in checks):
        raise ValueError("Recovery identities missing, duplicated or failed")
    if (recovery["passed"], recovery["total"]) != (19, 19):
        raise ValueError("Recovery summary differs")
    interrupted = checks[0]["detail"]
    if interrupted.get("marker") != "CHECKPOINT_DURABLE" or not isinstance(interrupted.get("returncode"), int) or interrupted["returncode"] >= 0:
        raise ValueError("Process interruption evidence differs")
    if any(x["detail"] is not True for x in checks[1:]):
        raise ValueError("Recovery detail differs from the claimed outcome")
    quote = safe_file(root, "03_Evidence/browser_downloads/B_after_quote.json").read_bytes()
    for i in range(1, 6):
        if safe_file(root, f"03_Evidence/recovery/B-recovered-quote-{i}.json").read_bytes() != quote:
            raise ValueError("Recovered quote bytes differ")
    effort = load_json(safe_file(root, "03_Evidence/OWNER_EFFORT.json"))
    if type(effort["participants"]) is not int or effort["participants"] != 0 or effort["timeModel"]["humanTimeObserved"] is not False:
        raise ValueError("Scripted replay cannot assert observed human outcomes")
    runs = effort["runs"]
    expected_order = [(mode, i) for i in range(1, 6) for mode in
                      (["familiar-no-profile", "retained-profile"] if i % 2 else ["retained-profile", "familiar-no-profile"])]
    if [(x["mode"], x["replicate"]) for x in runs] != expected_order:
        raise ValueError("Owner replicate identities/order missing or duplicated")
    for run in runs:
        mode, replicate = run["mode"], run["replicate"]
        count, edits = (14, 4) if mode == "familiar-no-profile" else (11, 0)
        if (run["actions"], run["preferenceEdits"], run["freshScopeApprovals"], run["reviewChecks"],
            run["qualityPassed"], run["qualityTotal"], run["typedBriefCharacters"]) != (count, edits, 1, 3, 35, 35, 180):
            raise ValueError("Owner controls, quality or authorization changed")
        if run["qualitySource"] != "03_Evidence/acceptance/B_after.json":
            raise ValueError("Owner quality source differs")
        trace = load_json(safe_file(root, f"03_Evidence/owner_{mode}_{replicate}.json"))
        if trace["schema"] != "owner-replay/v1" or type(trace["humanParticipants"]) is not int or trace["humanParticipants"] != 0:
            raise ValueError("Owner trace scope differs")
        events = trace["events"]
        rows = [[e[k] for k in ["sequence", "element", "type", "value", "actor", "context"]] for e in events]
        if len(events) != count or outcome_signature(rows) != OWNER_TRACE_SIGNATURES[mode]:
            raise ValueError("Owner event trace differs from the declared actions")
        times = [e["elapsedMs"] for e in events]
        if any(type(t) not in (int, float) or t < 0 for t in times) or times != sorted(times) or run["mechanicalElapsedMs"] != times[-1]:
            raise ValueError("Owner mechanical timings are inconsistent")
    if (effort["baselineActions"], effort["reuseActions"]) != (14, 11) or abs(effort["reductionFraction"] - 3 / 14) > 1e-12:
        raise ValueError("Owner headline differs from individual traces")
    vectors = load_json(safe_file(root, "03_Evidence/acceptance/sha256_vectors.json"))
    texts = ["", "abc", "école", 'Ω\n"', "a" * 1000] + ["sample-" + str(i) + "é" * i for i in range(100)]
    expected_vectors = [{"inputSha256": hashlib.sha256(t.encode()).hexdigest(), "passed": True, "length": len(t.encode())} for t in texts]
    if vectors["tests"] != expected_vectors or not all(x["passed"] is True for x in vectors["tests"]) or (vectors["count"], vectors["passed"]) != (105, 105):
        raise ValueError("Hash vector identities, outcomes or summary differ")
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
        print("Complete publication manifest, original source and generated applications verified; real-user results remain empty.")
        return
    if not args.output:
        parser.error("--output must name a NEW directory outside this kit")
    dest = args.output.resolve()
    if dest.exists() or dest.is_relative_to(ROOT) or ROOT.is_relative_to(dest):
        parser.error("Choose a new destination outside the source kit")
    names = sorted(manifest_files(ROOT)) + ["SHA256SUMS"]
    dest.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name in names:
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(safe_file(ROOT, name), target)
    verify_sources(dest)
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
