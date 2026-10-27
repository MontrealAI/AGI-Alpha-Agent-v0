#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replay the frozen opportunity-led extension without network or model calls."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any
import zipfile

STUDY = Path(__file__).resolve().parents[1]
HERE = STUDY / "opportunity"
SUPPORTING_SHA256 = "598fe56134ed1f745568a9b31bdd513bfc8cab94ccf01add5cfcdaf585490010"
SUMMARY_SHA256 = "5de12a457c39031ebf688e8f5c1a94bb0347758dcab870965582dba476613a1e"
ARMS = ("U", "E", "E_plus")
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def read(path: Path) -> Any:
    """Read a UTF-8 JSON evidence file."""
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    """Hash an ordinary file."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition: bool, message: str) -> None:
    """Raise on mismatches without relying on removable assertions."""
    if not condition:
        raise ValueError(message)


def load(name: str, path: Path) -> Any:
    """Import a local, previously source-verified module."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load " + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def invoke(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Execute local replay code, preserving failure details."""
    result = subprocess.run(args, cwd=cwd or STUDY, capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise RuntimeError(f"Replay failed ({result.returncode}): {args}\n{result.stdout}\n{result.stderr}")
    return result


def check_freezes() -> dict[str, Any]:
    """Bind prospective freezes and separately labeled archived outcomes."""
    pins: dict[str, str] = {}

    def pin(path: Path, expected: str) -> None:
        require(path.is_file() and not path.is_symlink(), "Missing ordinary file: " + str(path))
        require(sha(path) == expected, "Frozen bytes changed: " + str(path))
        pins[os.path.relpath(path, STUDY)] = expected

    pin(STUDY / "reproduce.py", SUPPORTING_SHA256)
    pin(HERE / "results/confirmation_summary.json", SUMMARY_SHA256)
    summary = read(HERE / "results/confirmation_summary.json")
    for name, digest in summary["source_freezes"].items():
        pin(STUDY / name, digest)
    for freeze_path in ("protocol/EXPOSURE_FREEZE.json", "protocol/PROTOCOL_FREEZE.json"):
        for name, digest in read(HERE / freeze_path)["files"].items():
            pin(STUDY / name, digest)
    protocol = read(HERE / "protocol/PROTOCOL_FREEZE.json")
    pin(HERE / "SELECTION.json", protocol["opportunity_selection_sha256"])
    instrument = read(HERE / "development/INSTRUMENT_FREEZE.json")
    for name, digest in instrument["generic_file_sha256"].items():
        pin(HERE / "instrument" / name, digest)
    for name, key in (
        ("instrument/capability_capsule.zip", "capsule_sha256"),
        ("development/test_model_reuse.py", "development_tests_sha256"),
        ("development/development_results.json", "development_results_sha256"),
        ("development/validation_history.json", "validation_history_sha256"),
    ):
        pin(HERE / name, instrument[key])
    require(instrument["development_tests_passed"] == 18, "Development test count changed")
    for source_root, manifest in (
        (HERE / "discovery/science/source_checkout/petab_select", HERE / "discovery/science/h4_source_manifest.json"),
        (HERE / "protocol/public_sources/boehm", HERE / "protocol/public_sources/boehm/SOURCE_MANIFEST.json"),
    ):
        for row in read(manifest)["files"]:
            path = source_root / row["path"]
            pin(path, row["sha256"])
            require(path.stat().st_size == row["bytes"], "Source byte count differs")
    for name, record in read(HERE / "protocol/public_case/SOURCE_FILES.json")["files"].items():
        path = HERE / "protocol/public_case" / name
        pin(path, record["sha256"])
        require(path.stat().st_size == record["bytes"], "Public source size differs")

    native = read(HERE / "integration/results/protocol.json")
    pin(STUDY / "integration/run_native_integration.py", native["runner_sha256"])
    require(native["artifact_sha256"] == instrument["capsule_sha256"], "Native receipt uses another capsule")
    upstream = STUDY.parent / "agi-alpha-capability-opportunity-v1/integration"
    for name, digest in native["upstream_adapter_pins"].items():
        pin(upstream / name, digest)
    for row in read(upstream / "source_manifest.json")["files"]:
        pin(upstream / row["local_path"], row["sha256"])
        require((upstream / row["local_path"]).stat().st_size == row["bytes"], "Prior closure size differs")

    arrangement = HERE / "arrangement"
    frozen = read(arrangement / "results/FREEZE.json")
    for name, key in (
        ("checker.py", "source_sha256"),
        ("PROTOCOL.json", "protocol_sha256"),
        ("results/conditional_frontier.json", "frontier_sha256"),
        ("results/reference_selection.json", "reference_sha256"),
    ):
        pin(arrangement / name, frozen[key])
    complete = read(arrangement / "results/FRESH_COMPLETE.json")
    pin(arrangement / "results/FREEZE.json", complete["freeze_sha256"])
    pin(arrangement / "results/fresh_stress.json", complete["results_sha256"])
    historical = read(arrangement / "results/historical_regressions.json")
    pin(STUDY.parents[1] / historical["source"], historical["source_sha256"])
    return {
        "distinct_file_commitments": len(pins),
        "pins": pins,
        "confirmation_summary_binding": "Post-result archive binding; not described as a prospective commitment.",
        "native_closure_files": 34,
        "additional_historical_source": historical["source"],
    }


def test_suite(path: Path, expected: int) -> dict[str, Any]:
    """Execute a meaningful frozen unittest suite with an explicit test count."""
    result = invoke([sys.executable, str(path)], path.parent)
    combined = result.stdout + result.stderr
    count = re.search(r"Ran (\d+) tests? in", combined)
    require(count is not None and int(count.group(1)) == expected, "Unexpected unittest count: " + str(path))
    require(re.search(r"\nOK\s*$", combined) is not None, "Unittest did not finish successfully")
    return {"tests": expected, "passed": True, "output": combined}


def development_and_oracle(temporary: Path) -> dict[str, Any]:
    """Repeat development tests and positive/negative independent acceptance controls."""
    tests = test_suite(HERE / "development/test_model_reuse.py", 18)
    control_root = temporary / "scientific-oracle"
    for directory in ("private", "conventional"):
        shutil.copytree(
            HERE / directory, control_root / directory, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
    shutil.copytree(HERE / "protocol/public_case", control_root / "protocol/public_case")
    invoke([sys.executable, str(control_root / "private/validate_protocol.py")], control_root / "private")
    controls = read(control_root / "private/protocol_validation.json")
    require(controls == read(HERE / "private/protocol_validation.json"), "Independent oracle control report changed")
    require(
        controls["positive_missions_passed"] == 4 and controls["negative_controls_rejected"] == 13,
        "Control totals differ",
    )
    output = temporary / "conventional-acceptance.json"
    invoke(
        [
            sys.executable,
            str(HERE / "private/evaluate.py"),
            str(HERE / "conventional/direct_method.py"),
            "--out",
            str(output),
        ]
    )
    accepted = read(output)
    require(
        accepted["accepted"] and accepted["passed"] == accepted["total"] == 4,
        "Conventional method fails frozen criteria",
    )
    require(accepted["source_inputs_unchanged"], "Conventional method changed source inputs")
    return {
        "development": tests,
        "protocol_controls": controls,
        "conventional_missions_accepted": accepted["passed"],
        "conventional_variants_per_mission": accepted["request_variants_per_mission"],
        "oracle_independence": "Source reaction identifiers, SVD nullspace and Poisson uniformization; does not import retained instrument or conventional method.",
        "scope": "Internal computational validation; no external scientific or biological validation.",
    }


def transport(temporary: Path, native_enabled: bool) -> dict[str, Any]:
    """Verify transported generic bytes and optionally execute the native fixture again."""
    source = HERE / "instrument/capability_capsule.zip"
    content = source.read_bytes()
    frozen = read(HERE / "development/INSTRUMENT_FREEZE.json")
    receipt = read(HERE / "integration/TRANSFER_RECEIPT.json")
    require(len(content) == frozen["capsule_bytes"] == 48797, "Scientific capsule length differs")
    require(receipt["received_capsule_sha256"] == sha(source), "Transfer receipt differs")
    for name in ("source-workflow.zip", "received-workflow.bin", "ordinary-library-workflow.bin"):
        require((HERE / "integration/results" / name).read_bytes() == content, "Transport/library bytes differ")
    with zipfile.ZipFile(source) as capsule:
        require(set(capsule.namelist()) == set(frozen["generic_file_sha256"]), "Capsule contains unexpected files")
        for name in capsule.namelist():
            generic = (HERE / "instrument" / name).read_bytes()
            require(capsule.read(name) == generic, "Capsule generic content differs")
            require(
                (HERE / "integration/received-capability" / name).read_bytes() == generic, "Recovered content differs"
            )
            require(receipt["files"][name] == frozen["generic_file_sha256"][name], "Receipt member hash differs")
    archived = read(HERE / "integration/results/summary.json")
    require(archived["passed"] == archived["total"] == 31, "Archived transport controls fail")
    require(
        archived["actual_collections_usd"] == archived["live_ens_authentications"] == 0,
        "Fixture money/identity mislabeled",
    )
    require(
        archived["actual_complete_cost_profit"] is None and not archived["empirical_alpha_admission"],
        "Unsupported economic admission",
    )
    status = "skipped by explicit flag; archived bytes and controls checked"
    if native_enabled:
        output = temporary / "scientific-native-transfer"
        invoke(
            [
                sys.executable,
                str(STUDY / "integration/run_native_integration.py"),
                "--artifact",
                str(source),
                "--out",
                str(output),
            ]
        )
        fresh = read(output / "summary.json")
        require(fresh["passed"] == fresh["total"] == 31, "Fresh native fixture failed")
        require(
            [(r["name"], r["passed"]) for r in fresh["checks"]]
            == [(r["name"], r["passed"]) for r in archived["checks"]],
            "Native control outcomes differ",
        )
        require((output / "received-workflow.bin").read_bytes() == content, "Fresh transfer changed bytes")
        status = "31/31 fresh controls under synthetic authority"
    return {
        "capsule_sha256": sha(source),
        "capsule_bytes": len(content),
        "native": status,
        "graph_library_same_contents": True,
        "live_identity": False,
        "production_admission": False,
    }


def acceptance_view(data: dict[str, Any]) -> dict[str, Any]:
    """Strip nonsemantic execution timing and stdout from acceptance comparisons."""
    return {
        key: data[key]
        for key in (
            "accepted",
            "passed",
            "total",
            "source_inputs_unchanged",
            "campaigns",
            "source_families",
            "request_variants_per_mission",
            "unit_of_inference",
            "physical_validation",
            "actual_cost",
        )
    } | {"variants": [{"variant": v["variant"], "missions": v["missions"]} for v in data["variants"]]}


def confirmation(temporary: Path) -> dict[str, Any]:
    """Replay only archived submissions after every recorded participant is closed."""
    summary = read(HERE / "results/confirmation_summary.json")
    exposure = read(HERE / "protocol/EXPOSURE_FREEZE.json")
    exposed = datetime.fromisoformat(exposure["recorded_at_utc"]).timestamp()
    states = {arm: read(HERE / "results/trials" / ("S3_" + arm) / "state.json") for arm in ARMS}
    require(all(state["closed"] for state in states.values()), "All scientific participants must freeze before replay")
    methods = read(HERE / "development/INSTRUMENT_FREEZE.json")
    require(
        datetime.fromisoformat(read(HERE / "SELECTION.json")["recorded_at_utc"]).timestamp()
        < datetime.fromisoformat(methods["frozen_at_utc"]).timestamp()
        < exposed,
        "Selection/method/exposure order differs",
    )
    require(
        datetime.fromisoformat(read(HERE / "integration/TRANSFER_RECEIPT.json")["recorded_at_utc"]).timestamp()
        < exposed,
        "Transport receipt follows exposure",
    )
    reports: dict[str, Any] = {}
    for arm in ARMS:
        folder = HERE / "results/trials" / ("S3_" + arm)
        state = states[arm]
        row = summary["arms"][arm]
        require(state["started_at"] > exposed, "Participant began before exposure freeze")
        require(
            state["within_envelope"] and state["operations"] <= 48 and state["elapsed_seconds"] <= 1200,
            "Scientific budget exceeded",
        )
        require(state["token_counts"] is None and state["actual_cost_usd"] is None, "Unknown billing boundary changed")
        for relative, entry in state["initial_inventory"].items():
            p = folder / relative
            require(
                sha(p) == entry["sha256"] and p.stat().st_size == entry["bytes"],
                "Initial scientific input changed: " + str(p),
            )
        inventory = state["submission_inventory"]
        frozen_root = folder / "frozen_submission"
        names = {
            str(p.relative_to(frozen_root))
            for p in frozen_root.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }
        require(names == set(inventory), "Frozen scientific submission file set differs")
        for relative, entry in inventory.items():
            p = frozen_root / relative
            require(
                sha(p) == entry["sha256"] and p.stat().st_size == entry["bytes"],
                "Scientific submission changed: " + str(p),
            )
        task = frozen_root / "qualification"
        for filename in ("state.json", "events.jsonl"):
            require(
                sha(folder / filename) == row["state_sha256" if filename == "state.json" else "events_sha256"],
                "Archived runner binding differs",
            )
        require(sha(task / "submission.py") == row["submission_sha256"], "Submission source binding differs")
        events = [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()]
        require(
            len(events) == state["operations"] + 1 and events[-1]["kind"] == "finish", "Scientific log count differs"
        )
        require(
            [e["operation"] for e in events[:-1]] == list(range(1, state["operations"] + 1)),
            "Scientific log sequence differs",
        )
        runs = [e for e in events if e["kind"] == "run"]
        require(
            len(runs) == row["logged_python_executions"] == state["test_executions"],
            "Python invocation counter differs",
        )
        require(
            sum(e["returncode"] != 0 for e in runs) == row["nonzero_exit_python_executions"],
            "Python failure counter differs",
        )
        for key in ("operations", "elapsed_seconds", "output_bytes", "tool_elapsed_seconds"):
            require(state[key] == row[key], "Summary runner metric differs: " + key)
        for name in ("submission.py", "packet.json", "REPORT.md"):
            require((task / name).is_file(), "Required scientific deliverable missing")
        for name, expected in read(HERE / "protocol/public_case/SOURCE_FILES.json")["files"].items():
            require(sha(task / name) == expected["sha256"], "Frozen scientific evidence changed")
        for name in ("BRIEF.md", "requests.json", "SOURCE_FILES.json", "test_public.py"):
            require(
                (task / name).read_bytes() == (HERE / "protocol/public_case" / name).read_bytes(),
                "Public scientific contract changed",
            )
        stored_path = HERE / "results" / ("S3_" + arm + "_acceptance.json")
        require(sha(stored_path) == row["acceptance_sha256"], "Acceptance archive binding differs")
        stored = read(stored_path)
        output = temporary / ("acceptance-" + arm + ".json")
        invoke([sys.executable, str(HERE / "private/evaluate.py"), str(task / "submission.py"), "--out", str(output)])
        fresh = read(output)
        require(acceptance_view(fresh) == acceptance_view(stored), "Scientific acceptance differs on replay")
        require(
            fresh["accepted"] and fresh["passed"] == fresh["total"] == row["passed_missions"] == 4,
            "Scientific mission acceptance mismatch",
        )
        packet_path = temporary / ("packet-" + arm + ".json")
        invoke(
            [
                sys.executable,
                str(task / "submission.py"),
                "--sources",
                str(task / "sources"),
                "--requests",
                str(task / "requests.json"),
                "--out",
                str(packet_path),
            ],
            task,
        )
        require(
            read(packet_path) == read(task / "packet.json"),
            "Saved declared packet is not deterministically reconstructed",
        )
        if arm == "E_plus":
            for name, digest in methods["generic_file_sha256"].items():
                require(sha(task / "capability" / name) == digest, "Recipient changed retained instrument")
        reports[arm] = {
            "accepted_missions": 4,
            "campaigns": 1,
            "families": 2,
            "request_variants_per_mission": 2,
            "packet_reconstruction": "exact JSON equality",
            "recorded_wall_seconds": state["elapsed_seconds"],
            "logged_operations": state["operations"],
            "actual_cost": None,
        }
    require(
        summary["actual_collections_usd"] == 0
        and summary["actual_complete_cost_usd"] is None
        and summary["actual_profit_usd"] is None,
        "Actual economic boundary changed",
    )
    require(
        summary["operational_alpha_acceptance_percentage_points"]
        == summary["additional_learned_alpha_acceptance_percentage_points"]
        == 0,
        "S3 acceptance contrast differs",
    )
    return {
        "arms": reports,
        "frozen_exact_prompts": True,
        "independence_limit": "One campaign over two public source families; H4 was used in development. Changed requests are not independent opportunities.",
        "prose_review": "Separately documented in validation/opportunity_review.md; string-length checks alone do not validate explanations.",
    }


def arrangement(temporary: Path) -> dict[str, Any]:
    """Rebuild the declared finite arrangement search, stress and exact accounting audit."""
    source = HERE / "arrangement"
    tests = test_suite(source / "test_checker.py", 10)
    output = temporary / "arrangement-reconstruction"
    invoke([sys.executable, str(source / "checker.py"), "freeze", "--out", str(output)])
    invoke([sys.executable, str(source / "checker.py"), "stress", "--out", str(output)])
    names = (
        "FREEZE.json",
        "conditional_frontier.json",
        "reference_selection.json",
        "fresh_stress.json",
        "FRESH_COMPLETE.json",
    )
    for name in names:
        require(
            read(output / name) == read(source / "results" / name),
            "Arrangement deterministic reconstruction differs: " + name,
        )
    copied = temporary / "arrangement-audit"
    shutil.copytree(source, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    invoke([sys.executable, str(copied / "audit.py")], copied)
    audited = read(copied / "results/independent_accounting_audit.json")
    require(
        audited == read(source / "results/independent_accounting_audit.json"), "Independent arrangement audit differs"
    )
    checker = load("review_arrangement_checker", source / "checker.py")
    historical_tests = load("review_arrangement_historical", source / "test_checker.py")
    history = read(source / "results/historical_regressions.json")
    for label, core, buyers in (
        ("four_buyer", 600000, 4),
        ("successor_setup_300k", 300000, 2),
        ("successor_setup_150k", 150000, 2),
    ):
        require(
            historical_tests.historical(core, buyers) == history["cases"][label],
            "Historical arithmetic regression differs",
        )
    timing = read(source / "results/timing_examples.json")
    for record in timing["cases"]:
        plan = {
            "technical": True,
            "coordinated": True,
            "participants": ["P1", "P2", "P3"],
            "price_cents": 30000,
            "finance": record["mode"],
        }
        world = {"id": "illustrative-success", "common_ok": True, "delay": record["payment_release_delay_days"]}
        require(
            checker.simulate(plan, timing["inputs"], world) == record["result"],
            "Post-confirmation timing illustration differs",
        )
    package = temporary / "illustrative-package.json"
    invoke(
        [
            sys.executable,
            str(source / "evaluate_package.py"),
            "--input",
            str(source / "illustrative_request.json"),
            "--out",
            str(package),
        ]
    )
    require(
        read(package) == read(source / "results/example_package_evaluation.json"),
        "Illustrative package evaluation differs",
    )
    return {
        "tests": tests,
        "reconstructed_files": list(names),
        "historical_cases": 3,
        "timing_illustrations": 6,
        "independent_audit": audited,
        "actual_commitments": 0,
        "default_learned_cost_reduction": "0",
        "scope": "Exact analysis of supplied assumptions and finite menus; not S3 market or revenue evidence.",
    }


def run(native_enabled: bool = True) -> dict[str, Any]:
    """Run the complete extension replay without altering archived evidence."""
    started = time.perf_counter()
    report: dict[str, Any] = {
        "schema": "opportunity-extension-replay/1",
        "edition": "2.1.0",
        "reproducer_sha256": sha(Path(__file__)),
        "actual_customer_collections_usd": 0,
        "actual_complete_cost_usd": None,
    }
    try:
        require(
            not sys.flags.optimize, "Run without -O or PYTHONOPTIMIZE; frozen evaluator assertions must remain enabled"
        )
        report["versions"] = {n: importlib.metadata.version(n) for n in ("numpy", "scipy", "PyYAML")}
        report["source_commitments"] = check_freezes()
        with tempfile.TemporaryDirectory(prefix="opportunity-replay-") as name:
            temporary = Path(name)
            report["development_and_oracle"] = development_and_oracle(temporary)
            report["transfer"] = transport(temporary, native_enabled)
            report["confirmation"] = confirmation(temporary)
            report["arrangement"] = arrangement(temporary)
        report["passed"] = True
    except Exception as exc:
        report.update(passed=False, failure_type=type(exc).__name__, failure=str(exc))
    report["elapsed_seconds"] = time.perf_counter() - started
    report["admission_observation"] = {
        "production_admission": False,
        "native_scope": "Unsupported scientific workflow; original native scope unchanged",
        "existing_minimum_independent_clusters": 6,
        "observed_campaigns_per_arm": 1,
        "public_source_families": 2,
        "sufficient_independent_cluster_evidence": False,
        "actual_complete_monetary_evidence": False,
        "transport_fixture_is_empirical_alpha": False,
    }
    report["not_claimed"] = [
        "new frontier-model trial",
        "protected fresh source-family generalization",
        "external scientific validation",
        "physical or biological validation",
        "live identity",
        "customer revenue",
        "full repository CI",
        "publication or deployment approval",
    ]
    return report


def main() -> None:
    """Emit a new replay report while refusing to replace existing evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-native", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.report is not None:
        output = args.report.resolve()
        if output.exists() or (output.is_relative_to(STUDY) and not output.is_relative_to(STUDY / "validation")):
            parser.error("report must be a new file outside frozen evidence directories; validation is allowed")
    result = run(not args.skip_native)
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
    print(encoded)
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
