# SPDX-License-Identifier: Apache-2.0
"""Run bounded local checks and derive an additive, source-bound 80-case audit.

The original acceptance snapshot is immutable history. A passing command describes
only its declared automated scope, never the whole product, a human trial or live
commissioning. Evidence hashes provide integrity, not independent attestation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from typing import Any
import uuid

ROOT = Path(__file__).resolve().parents[1]
HISTORY = "docs/agent/ascension-cycle-acceptance.json"
POLICY = "docs/agent/ascension-cycle-audit-scope.json"
OUTPUT = "docs/agent/ascension-cycle-current-audit.json"
EVIDENCE = "docs/agent/release-evidence/current-acceptance"
SCHEMA = "agialpha.ascension.current-audit.v1"
RUN_SCHEMA = "agialpha.ascension.current-audit-run.v1"
HISTORY_SHA256 = "7662c4cc56c6c8f651635c7357b27ae9c5417795452e84ac1b96dd7baf3905f0"
EXCLUDED = (EVIDENCE + "/", OUTPUT, "docs/agent/ASCENSION_CURRENT_AUDIT.md")
GENERATED_INPUTS = ("docs/assets/ascension-wallet/profile.json",)


def sha256(data: bytes) -> str:
    """Return a byte identity, without asserting provenance or authority."""
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    """Use a stable encoding for source inventories and immutable specifications."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def load_json(path: Path) -> Any:
    """Reject ambiguous JSON rather than silently accepting duplicate keys."""

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def save_json(path: Path, value: Any) -> None:
    """Write a reviewable JSON artifact; callers choose a new evidence directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def git(root: Path, *args: str) -> str:
    """Read repository state without modifying it."""
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def source_identity(root: Path) -> dict[str, Any]:
    """Hash all tracked and unignored source files plus the generated archive profile.

    Only this audit's outputs are excluded to avoid self-reference. Ignored runtime
    dependencies are represented by lockfiles and the recorded runtime versions.
    Missing tracked files remain in the inventory as null; symlink targets are not
    traversed. Adding, deleting or editing an inventoried file invalidates old runs.
    """
    names = set(git(root, "ls-files", "-z", "--cached").split("\0"))
    names.update(
        name
        for name in git(root, "ls-files", "-z", "--others", "--exclude-standard").split("\0")
        if not name.startswith(("evidence/", "site/"))
    )
    names.update(GENERATED_INPUTS)
    inventory: dict[str, str | None] = {}
    for name in sorted(names):
        if not name or any(name == prefix or name.startswith(prefix) for prefix in EXCLUDED):
            continue
        path = root / name
        if path.is_symlink():
            inventory[name] = sha256(("symlink:" + os.readlink(path)).encode())
        else:
            inventory[name] = sha256(path.read_bytes()) if path.is_file() else None
    return {
        "commit": git(root, "rev-parse", "HEAD"),
        "source_sha256": sha256(canonical(inventory)),
        "files": inventory,
        "scope": (
            "Tracked files and unignored files outside runtime evidence/site outputs, "
            "plus generated archive profile; audit outputs excluded."
        ),
        "excluded_audit_outputs": list(EXCLUDED),
        "excluded_untracked_runtime_outputs": ["evidence/", "site/"],
        "dependency_limit": (
            "Lockfiles and runtime versions are bound; " "installed package bytes are not independently attested."
        ),
    }


def catalog(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Require all original case identities and an explicit bounded audit scope."""
    history_bytes = (root / HISTORY).read_bytes()
    if sha256(history_bytes) != HISTORY_SHA256:
        raise ValueError("The preserved historical acceptance snapshot changed")
    history = load_json(root / HISTORY)
    policy = load_json(root / POLICY)
    ids = [f"{number:02}" for number in range(1, 81)]
    if [case["id"] for case in history["cases"]] != ids or sorted(policy["cases"]) != ids:
        raise ValueError("Exactly the original 80 acceptance IDs are required")
    if policy["pilot"]["observed_participants"] != 0 or policy["pilot"]["benefit_validated"] is not False:
        raise ValueError("This audit cannot turn a zero-participant pilot into human-benefit evidence")
    for case in history["cases"]:
        scope = policy["cases"][case["id"]]
        if scope["requirement"] != case["requirement"] or not scope["remaining_acceptance"]:
            raise ValueError("Original requirements and explicit remaining acceptance must be preserved")
        if any(suite not in policy["suites"] for suite in scope["suite_ids"]):
            raise ValueError("Every coverage reference needs an executable suite specification")
    return history, policy


def counts_from_log(text: str, kind: str) -> dict[str, int] | None:
    """Extract honest test counts when the runner has a recognized test summary."""
    if kind == "node":
        keys = {
            key: [int(value) for value in re.findall(rf"^# {key} (\d+)$", text, re.M)]
            for key in ("tests", "pass", "fail", "cancelled", "skipped", "todo")
        }
        if not all(keys.values()):
            return None
        return {key: sum(value) for key, value in keys.items()}
    if kind == "pytest":
        summaries = re.findall(r"^.*\b\d+ (?:passed|failed|error|skipped).*$", text, re.M)
        if not summaries:
            return None
        line = summaries[-1]
        result = {
            key: sum(int(value) for value in re.findall(rf"(\d+) {key}\b", line))
            for key in ("passed", "failed", "errors", "skipped", "xfailed", "xpassed")
        }
        return result if sum(result.values()) else None
    return None


def run_outcome(record: dict[str, Any], output: str) -> str:
    """Never mark a failed, changed-source, empty or skipped test run fully passing."""
    if record["returncode"] is None:
        return "incomplete"
    if record["returncode"] != 0 or record["source_before"] != record["source_after"]:
        return "failed"
    counts = counts_from_log(output, record["kind"])
    if record["kind"] in {"node", "pytest"}:
        if not counts or not sum(counts.get(key, 0) for key in ("pass", "passed")):
            return "unverified"
        if any(counts.get(key, 0) for key in ("fail", "failed", "errors", "cancelled", "xpassed")):
            return "failed"
        if any(counts.get(key, 0) for key in ("skipped", "todo", "xfailed")):
            return "partial"
    return "passed"


def artifact_inventory(directory: Path) -> dict[str, str]:
    """Bind every retained harness artifact, without following symlinks."""
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Evidence artifacts cannot contain symlinks")
        if path.is_file():
            result[str(path.relative_to(directory))] = sha256(path.read_bytes())
    return result


def checked_runs(root: Path, directory: Path, policy: dict[str, Any], identity: dict[str, Any]) -> list[dict[str, Any]]:
    """Verify retained command/output/source identities; historical runs stay stale."""
    results: list[dict[str, Any]] = []
    if not directory.exists():
        return results
    for source_path in sorted(directory.glob("*/source.json")):
        path = source_path.parent / "run.json"
        if not path.is_file():
            raise ValueError(f"Incomplete evidence has no retained invocation: {source_path.parent}")
        record = load_json(path)
        suite_id = record.get("suite_id")
        if record.get("schema") != RUN_SCHEMA or suite_id not in policy["suites"]:
            raise ValueError(f"Unknown evidence schema or suite: {path}")
        expected = policy["suites"][suite_id]
        original_spec = record.get("suite_spec", {})
        if record.get("suite_spec_sha256") != sha256(canonical(original_spec)):
            raise ValueError(f"Evidence command/scope specification changed: {path}")
        if record["run_id"] != path.parent.name:
            raise ValueError(f"Evidence run identity changed: {path}")
        runtime = record["runtime"]
        replacements = {
            "{python}": runtime["python"],
            "{node}": runtime["node"],
            "{evidence}": str(Path(record["execution_root"]) / EVIDENCE / record["run_id"] / "artifacts"),
        }
        expected_command = [replacements.get(arg, arg) for arg in original_spec["argv"]]
        if record.get("argv") != expected_command or record.get("cwd") != original_spec.get("cwd", "."):
            raise ValueError(f"Evidence executed command changed: {path}")
        expected_environment = {
            "PYTHONPATH": record["execution_root"],
            "ALPHA_PYTHON": runtime["python"],
            "NO_DISCLAIMER": "1",
        }
        expected_environment.update(
            {key: replacements.get(value, value) for key, value in original_spec.get("environment", {}).items()}
        )
        if record.get("environment") != expected_environment or record.get("scope") != original_spec["scope"]:
            raise ValueError(f"Evidence environment or scope changed: {path}")
        if record.get("human_participants") != 0 or record.get("real_funds") is not False:
            raise ValueError(f"Local commands cannot certify human participants or real funds: {path}")
        if record.get("kind") != original_spec["kind"]:
            raise ValueError(f"Evidence runner kind changed: {path}")
        output_path = path.parent / "output.txt"
        output_bytes = output_path.read_bytes()
        if sha256(output_bytes) != record.get("output_sha256"):
            raise ValueError(f"Evidence output changed: {output_path}")
        output = output_bytes.decode("utf-8", errors="replace")
        if record.get("counts") != counts_from_log(output, record["kind"]):
            raise ValueError(f"Evidence test counts changed: {path}")
        if record.get("outcome") != run_outcome(record, output):
            raise ValueError(f"Evidence outcome does not match its execution: {path}")
        manifest = load_json(path.parent / "source.json")
        if sha256(canonical(manifest["files"])) != record["source_before"]:
            raise ValueError(f"Evidence source inventory changed: {path}")
        if record.get("source_manifest_sha256") != sha256((path.parent / "source.json").read_bytes()):
            raise ValueError(f"Evidence source manifest changed: {path}")
        if record.get("artifacts") != artifact_inventory(path.parent / "artifacts"):
            raise ValueError(f"Evidence artifacts changed: {path}")
        current = (
            record["source_before"] == identity["source_sha256"]
            and (record["source_after"] == identity["source_sha256"] or record["outcome"] == "incomplete")
            and original_spec == expected
        )
        results.append(
            {
                **record,
                "current_source": current,
                "evidence_path": str(path.relative_to(root)),
                "record_sha256": sha256(path.read_bytes()),
            }
        )
    return results


def build_audit(root: Path = ROOT) -> dict[str, Any]:
    """Derive the current view without copying historical pass/fail assertions."""
    history, policy = catalog(root)
    identity = source_identity(root)
    runs = checked_runs(root, root / EVIDENCE, policy, identity)
    latest = {}
    for run in sorted(runs, key=lambda item: (item["finished_utc"], item["run_id"])):
        if run["current_source"]:
            latest[run["suite_id"]] = run
    suites = {}
    for suite_id, spec in policy["suites"].items():
        selected_run = latest.get(suite_id)
        suites[suite_id] = {
            "scope": spec["scope"],
            "command": spec["argv"],
            "cwd": spec.get("cwd", "."),
            "status": selected_run["outcome"] if selected_run else "not_run",
            "evidence_id": selected_run["run_id"] if selected_run else None,
        }
    cases = []
    for original in history["cases"]:
        case_id = original["id"]
        scope = policy["cases"][case_id]
        status = [suites[name]["status"] for name in scope["suite_ids"]]
        if "failed" in status:
            automated = "failed"
        elif status and all(value == "passed" for value in status):
            automated = "passed"
        elif any(value in {"passed", "partial"} for value in status):
            automated = "partial"
        else:
            automated = "not_run"
        refs = {item["path"] for key in ("implementation_refs", "test_refs") for item in original[key]}
        refs.update(scope.get("additional_refs", []))
        cases.append(
            {
                "id": case_id,
                "requirement": original["requirement"],
                "requirement_status": (
                    "failed" if automated == "failed" else "partial" if automated != "not_run" else "not_run"
                ),
                "automated_scope_status": automated,
                "suite_ids": scope["suite_ids"],
                "current_evidence_ids": [latest[name]["run_id"] for name in scope["suite_ids"] if name in latest],
                "unexecuted_suites": [name for name in scope["suite_ids"] if name not in latest],
                "source_refs": [
                    {"path": name, "sha256": identity["files"].get(name), "present": (root / name).is_file()}
                    for name in sorted(refs)
                ],
                "remaining_acceptance": scope["remaining_acceptance"],
                "product_decisions": scope.get("product_decisions", []),
                "external_prerequisites": scope.get("external_prerequisites", []),
            }
        )
    return {
        "schema": SCHEMA,
        "historical_snapshot": {"path": HISTORY, "sha256": HISTORY_SHA256, "promoted_to_current_evidence": False},
        "source_identity": {key: value for key, value in identity.items() if key != "commit"},
        "semantics": {
            "automated_scope_status": "Only the explicitly mapped commands; never the entire original requirement.",
            "requirement_status": (
                "No whole-case pass is inferred. " "Remaining acceptance needs specific review and evidence."
            ),
            "integrity": (
                "Content hashes and logs bind local evidence; "
                "they do not prove independent review or actor authorization."
            ),
            "stale": "Prior source inventories are retained and listed but contribute no current passing outcome.",
        },
        "graph": {
            "nodes": history["graph"]["nodes"],
            "edges": history["graph"]["edges"],
            "source": "BACKGROUND.md",
            "sha256": identity["files"].get("BACKGROUND.md"),
            "original_source_sha256": history["graph"]["source_sha256"],
            "original_preserved": identity["files"].get("BACKGROUND.md") == history["graph"]["source_sha256"],
        },
        "suites": suites,
        "runs": runs,
        "cases": cases,
        "pilot": policy["pilot"],
        "external_prerequisites": policy["external_prerequisites"],
        "product_decisions": policy["product_decisions"],
        "additional_integration_matrix": policy["additional_integration_matrix"],
        "interruption_matrix": policy["interruption_matrix"],
        "summary": {
            "total_requirements": len(cases),
            "requirement_counts": dict(sorted(Counter(case["requirement_status"] for case in cases).items())),
            "automated_scope_counts": dict(sorted(Counter(case["automated_scope_status"] for case in cases).items())),
            "complete_software_release": False,
            "operational_mainnet_completion": False,
            "human_benefit_validated": False,
            "release_gates": policy["release_gates"],
        },
    }


def execute_suite(root: Path, suite_id: str, *, python: str, node: str, timeout: int) -> dict[str, Any]:
    """Execute only a catalogued local test command and retain original output."""
    _, policy = catalog(root)
    spec = policy["suites"][suite_id]
    identity = source_identity(root)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + suite_id + "-" + uuid.uuid4().hex[:8]
    directory = root / EVIDENCE / run_id
    directory.mkdir(parents=True, exist_ok=False)
    save_json(directory / "source.json", identity)
    replacements = {"{python}": python, "{node}": node, "{evidence}": str(directory / "artifacts")}
    command = [replacements.get(arg, arg) for arg in spec["argv"]]
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONPATH": str(root),
            "ALPHA_PYTHON": python,
            "NO_DISCLAIMER": "1",
            "PATH": str(Path(node).parent) + os.pathsep + environment.get("PATH", ""),
        }
    )
    for key, value in spec.get("environment", {}).items():
        environment[key] = replacements.get(value, value)
    started = datetime.now(timezone.utc).isoformat()
    output, code = b"", None
    record = {
        "schema": RUN_SCHEMA,
        "run_id": run_id,
        "suite_id": suite_id,
        "kind": spec["kind"],
        "suite_spec_sha256": sha256(canonical(spec)),
        "suite_spec": spec,
        "execution_root": str(root),
        "argv": command,
        "cwd": spec.get("cwd", "."),
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "returncode": code,
        "source_before": identity["source_sha256"],
        "source_after": None,
        "source_manifest_sha256": sha256((directory / "source.json").read_bytes()),
        "output_sha256": sha256(output),
        "artifacts": artifact_inventory(directory / "artifacts"),
        "runtime": {
            "audit_python": sys.version,
            "platform": platform.platform(),
            "python": python,
            "node": node,
            "node_version": subprocess.check_output([node, "--version"], text=True).strip(),
            "test_python_version": subprocess.check_output([python, "--version"], text=True).strip(),
            "playwright_browsers_path": environment.get("PLAYWRIGHT_BROWSERS_PATH"),
            "python_packages": json.loads(
                subprocess.check_output(
                    [
                        python,
                        "-c",
                        "import importlib.metadata as m,json; "
                        "print(json.dumps({d.metadata['Name']:d.version for d in m.distributions()}))",
                    ],
                    text=True,
                )
            ),
        },
        "scope": spec["scope"],
        "environment": {
            key: environment[key]
            for key in ("PYTHONPATH", "ALPHA_PYTHON", "NO_DISCLAIMER", *spec.get("environment", {}))
        },
        "human_participants": 0,
        "real_funds": False,
    }
    # Retain an incomplete invocation before launching. A killed runner cannot
    # disappear behind an older passing run of the same source.
    (directory / "output.txt").write_bytes(output)
    record.update(counts=None, outcome="incomplete")
    save_json(directory / "run.json", record)
    try:
        result = subprocess.run(
            command,
            cwd=root / spec.get("cwd", "."),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output, code = result.stdout, result.returncode
    except subprocess.TimeoutExpired as exc:
        output, code = (exc.stdout or b"") + b"\nAUDIT RUNNER: command timed out; no passing outcome.\n", 124
    except OSError as exc:
        output, code = str(exc).encode(), 127
    (directory / "output.txt").write_bytes(output)
    record.update(
        returncode=code,
        finished_utc=datetime.now(timezone.utc).isoformat(),
        source_after=source_identity(root)["source_sha256"],
        output_sha256=sha256(output),
        artifacts=artifact_inventory(directory / "artifacts"),
    )
    record["counts"] = counts_from_log(output.decode("utf-8", errors="replace"), spec["kind"])
    record["outcome"] = run_outcome(record, output.decode("utf-8", errors="replace"))
    save_json(directory / "run.json", record)
    return record


def main() -> int:
    """Generate/validate a report or record explicitly selected local test suites."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("generate", "validate", "run", "list"))
    parser.add_argument("--suite", action="append", default=[])
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--node", default=shutil.which("node") or "node")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    _, policy = catalog(ROOT)
    if args.action == "list":
        print("\n".join(f"{key}: {value['scope']}" for key, value in policy["suites"].items()))
        return 0
    failed = False
    if args.action == "run":
        if not args.suite or any(name not in policy["suites"] for name in args.suite):
            parser.error("Choose one or more explicit --suite IDs from list; no implicit broad or external run")
        for name in args.suite:
            record = execute_suite(
                ROOT,
                name,
                python=os.path.abspath(args.python),
                node=os.path.abspath(args.node),
                timeout=args.timeout,
            )
            print(f"{name}: {record['outcome']} ({record['run_id']})", flush=True)
            failed |= record["outcome"] in {"failed", "unverified"}
    report = build_audit()
    if args.action == "validate":
        if load_json(ROOT / OUTPUT) != report:
            raise ValueError("Audit is stale or modified; regenerate from current source and verified retained logs")
        print("Validated 80 unchanged requirements and current source/evidence identities; release remains gated.")
    else:
        save_json(ROOT / OUTPUT, report)
        print(f"Wrote {OUTPUT}; no whole-product, live-operation or human-benefit pass inferred.")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
