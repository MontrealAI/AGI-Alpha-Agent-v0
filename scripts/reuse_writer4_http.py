# SPDX-License-Identifier: Apache-2.0
"""Reuse one authenticated HTTP component proof; otherwise run the unchanged full QA."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any
from urllib.request import urlopen

QUALIFIED = "ce2e8f4e9a1b715c9369a49b2a7fa69c89512174"
PROOF = "a13f397a0ca7a28a75db7c99928ad696850f777f"
RECEIPT_SHA256 = "5939939343fcd834ad67fb007ad3ee9cd01b0bb1f02c49d974b5e287db628786"
RECEIPT_BYTES = 11536
RECEIPT_URL = (
    "https://raw.githubusercontent.com/MontrealAI/AGI-Alpha-Agent-v0/" + PROOF
    + "/docs/delivery/recovery-20261023/completion-qualification/site-companion141/ce2-http-acceptance.json"
)
STUDY = "studies/transformational-autonomous-enterprises-v1"
DOCUMENTS = {STUDY + "/README.md", STUDY + "/PUBLICATION_HANDOFF.md"}
WRAPPER = "scripts/qualify_writer4_http.py"
WRAPPER_SHA256 = "08af2c355b713cdd4e974f34efb780652d1918d0b78351fe715445afc9186328"
GUARD_INPUTS = (
    WRAPPER,
    "scripts/check_held_native_source.py",
    "tests/test_successor_capability_delivery.py",
    "tests/browser/fleet_receipt_native.mjs",
    "tests/browser/fleet_git_metadata.mjs",
    "tests/browser/fleet_module_boundary.mjs",
    "tests/browser/test_discovery_lab_continuation.py",
)
Inventory = dict[str, tuple[str, str, int]]


def same_component(expected: Inventory, actual: Inventory) -> bool:
    """Require the complete nonempty path/mode/body identity set, without normalization."""
    return bool(expected) and expected == actual


def git(root: Path, *arguments: str) -> bytes:
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null", GIT_OPTIONAL_LOCKS="0")
    result = subprocess.run(
        ["git", "--no-replace-objects", "-c", "core.fsmonitor=false", "-C", str(root), *arguments],
        env=environment, capture_output=True, check=False,
    )
    if result.returncode:
        raise ValueError("Complete qualifying Git ancestry is unavailable")
    return result.stdout


def committed(root: Path, commit: str, paths: tuple[str, ...]) -> Inventory:
    result = {}
    for row in git(root, "ls-tree", "-r", "-l", "-z", commit, "--", *paths).split(b"\0"):
        if not row:
            continue
        metadata, name_bytes = row.split(b"\t", 1)
        mode, kind, digest, size = metadata.decode("ascii").split()
        name = name_bytes.decode("utf-8")
        if kind != "blob" or mode not in {"100644", "100755"} or name in result:
            raise ValueError("Unexpected component source entry")
        if name not in DOCUMENTS:
            result[name] = (mode, digest, int(size))
    return result


def physical(root: Path, names: set[str]) -> Inventory:
    result = {}
    for name in sorted(names):
        target = root / name
        if target.resolve(strict=True) != target or not stat.S_ISREG(target.lstat().st_mode):
            raise ValueError("Component source is not a direct regular file")
        before = target.stat()
        raw = target.read_bytes()
        after = target.stat()
        keys = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before, key) != getattr(after, key) for key in keys):
            raise ValueError("Component source changed during capture")
        digest = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        result[name] = ("100755" if before.st_mode & 0o111 else "100644", digest, len(raw))
    return result


def validate_prior(raw: bytes) -> dict[str, Any]:
    if len(raw) != RECEIPT_BYTES or hashlib.sha256(raw).hexdigest() != RECEIPT_SHA256:
        raise ValueError("Qualifying receipt identity differs")
    decoded = json.loads(raw)
    if not isinstance(decoded, dict):
        raise ValueError("Qualifying receipt must be a JSON object")
    prior: dict[str, Any] = decoded
    if not (
        prior["schema"] == "tae.http-ui-ci-acceptance.v1" and prior["passed"] is True
        and prior["head"] == QUALIFIED and prior["runId"] == "40056653650" and prior["attempt"] == "1"
        and prior["failure"] is None and len(prior["phases"]) == 12
        and all(value == 0 for value in prior["phases"].values())
        and prior["report"]["passed"] is True and prior["report"]["errors"] == []
        and len(prior["report"]["checks"]) == 11
        and all(check["passed"] is True for check in prior["report"]["checks"])
        and prior["omittedOriginalFourQualified"] is False and prior["priorDeniedObjectivesAttempted"] is False
        and prior["browserExport"]["currentProof"] is None and prior["browserExport"]["authority"] == []
    ):
        raise ValueError("Qualifying receipt does not record the accepted bounded result")
    return prior


def output(reused: bool) -> None:
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
        stream.write("reused=" + ("true" if reused else "false") + "\n")


def main() -> int:
    root = Path.cwd().resolve()
    head, base = os.environ["TAE_EXPECTED_HEAD_SHA"], os.environ["TAE_EXPECTED_BASE_SHA"]
    if not all(re.fullmatch(r"[0-9a-f]{40}", value) for value in (head, base)):
        raise RuntimeError("Exact current head/base identities required")
    if git(root, "rev-parse", "HEAD").decode().strip() != head:
        raise RuntimeError("Checkout does not match the actual current head")
    try:
        git(root, "merge-base", "--is-ancestor", base, head)
        git(root, "merge-base", "--is-ancestor", QUALIFIED, head)
        expected = committed(root, QUALIFIED, (STUDY,))
        current = committed(root, head, (STUDY,))
        if len(expected) != 293 or not same_component(expected, current):
            raise ValueError("Study path/mode/body set changed")
        study = root / STUDY
        if study.is_symlink():
            raise ValueError("Study root is a symlink")
        actual_names = set()
        for path in study.rglob("*"):
            name = path.relative_to(root).as_posix()
            if name in DOCUMENTS:
                continue
            if path.is_symlink():
                raise ValueError("Study contains a symlink")
            if path.is_file():
                actual_names.add(name)
        if not same_component(expected, physical(root, actual_names)):
            raise ValueError("Actual study path/mode/body set changed")
        guards = committed(root, QUALIFIED, GUARD_INPUTS)
        if (
            len(guards) != len(GUARD_INPUTS)
            or not same_component(guards, committed(root, head, GUARD_INPUTS))
            or not same_component(guards, physical(root, set(guards)))
        ):
            raise ValueError("Original wrapper or critical guard inputs changed")
        if hashlib.sha256((root / WRAPPER).read_bytes()).hexdigest() != WRAPPER_SHA256:
            raise ValueError("Original full QA wrapper changed")
        # The byte count is the exact prior receipt identity, not a general response limit.
        with urlopen(RECEIPT_URL, timeout=30) as response:
            raw = response.read(RECEIPT_BYTES + 1)
        prior = validate_prior(raw)
        runtime = {"python": sys.version.split()[0]}
        for key, command in (("node", ["node", "--version"]), ("npm", ["npm", "--version"])):
            runtime[key] = subprocess.run(command, capture_output=True, text=True, check=True).stdout.strip()
        if any(runtime[key] != prior["toolchain"][key] for key in runtime):
            raise ValueError("Current Python/Node/npm differs from the qualifying toolchain")
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print("RUN_UNCHANGED_FULL_QA: " + str(error))
        output(False)
        return 0
    public = Path(os.environ["TAE_HTTP_PUBLIC"])
    task = Path(os.environ["RUNNER_TEMP"]) / (
        "writer4-http-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"]
    )
    if public != task / "public" or task.exists() or task.is_symlink():
        raise RuntimeError("Fresh task-owned public evidence directory required")
    public.mkdir(parents=True)
    receipt = {
        "schema": "tae.http-ui-exact-component-reuse.v1", "status": "REUSED_EXACT_COMPONENT",
        "head": head, "base": base, "runId": os.environ["GITHUB_RUN_ID"],
        "currentTree": git(root, "rev-parse", "HEAD^{tree}").decode().strip(),
        "qualifyingHead": QUALIFIED, "qualifyingRun": "40056653650", "proofCommit": PROOF,
        "qualifyingTree": "3d64c035df6a9b3cab7b1aee4471819a64e57a7e", "qualifyingAttempt": "1",
        "priorReceiptUrl": RECEIPT_URL, "priorReceiptSha256": RECEIPT_SHA256,
        "componentFiles": len(expected), "excludedMaintainedDocumentsOnly": sorted(DOCUMENTS),
        "componentIdentitySha256": hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest(),
        "originalFullQaWrapperSha256": WRAPPER_SHA256, "currentRuntimeObserved": runtime,
        "browserInputs": "Unchanged whole-study pinned package.json/package-lock.json; prior actual browser proof reused",
        "historicalResearchPins": prior["setupRecords"][0]["pins"],
        "priorDerivedSourceClosure": prior["derivedSourceClosure"],
        "originalArchiveSha256": prior["originalArchiveSha256"],
        "freshQaExecuted": False, "freshNativeMissionsExecuted": False, "fullSourceQualified": False,
        "scope": prior["scope"], "omittedOriginalFourQualified": False, "priorDeniedObjectivesAttempted": False,
    }
    (public / "reuse.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("REUSED_EXACT_COMPONENT: qualifying ce2 run40056653650; no fresh HTTP/native run")
    output(True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
