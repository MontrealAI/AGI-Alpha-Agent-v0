# SPDX-License-Identifier: Apache-2.0
"""Auditable, bounded transfer experiments; never a certification of general RSI.

The learner receives Mandate A only. A frozen forecasting policy, not an answer
oracle, predicts new Mandate B tasks. Integer fixed-point arithmetic is shared
with the browser implementation so every reported prediction can be replayed.
"""

from __future__ import annotations

import hashlib
import io
import json
import time
import zipfile
from typing import Any

PROTOCOL = "agialpha.transfer.v1"
MANUSCRIPT_SHA256 = "4b290d5a8232364b8808c0af8a96e7c9b152afd7ac3f5ba05668a538e073791a"
MAX_BYTES = 1_000_000
POLICIES = ["last", "mean", "linear", *[f"seasonal-{p}" for p in range(2, 9)]]
SECTIONS = [
    "00_manifest.md",
    "01_claims_matrix.md",
    "02_environment.md",
    "03_benchmark_tasks",
    "04_baselines",
    "05_agialpha_runs",
    "06_proof_bundles",
    "07_replay_logs",
    "08_cost_ledgers",
    "09_safety_ledgers",
    "10_validator_reports",
    "11_alpha_wu_calibration",
    "12_summary_tables",
]


def canonical(value: Any) -> str:
    """Encode bounded interoperable JSON without non-finite numbers."""

    def check(item: Any, depth: int = 0) -> None:
        if depth > 20:
            raise ValueError("Document nesting exceeds 20 levels")
        if item is None or type(item) in (str, bool):
            return
        if type(item) is int and abs(item) <= 2**53 - 1:
            return
        if type(item) is list:
            for part in item:
                check(part, depth + 1)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for part in item.values():
                check(part, depth + 1)
            return
        raise ValueError("Only bounded integer JSON data is accepted")

    check(value)
    result = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if len(result.encode()) > MAX_BYTES:
        raise ValueError("Document exceeds one megabyte")
    return result


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def parse(raw: str) -> dict[str, Any]:
    """Reject duplicate keys before validating or replaying an imported document."""
    if len(raw.encode()) > MAX_BYTES:
        raise ValueError("Document exceeds one megabyte")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        canonical(value)
    except (RecursionError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid JSON document") from exc
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def fields(value: Any, expected: str) -> None:
    if type(value) is not dict or set(value) != set(expected.split()):
        raise ValueError(f"Expected exactly these fields: {expected}")


def integer(value: Any, lower: int, upper: int) -> None:
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"Expected an integer from {lower} to {upper}")


def series(value: Any, minimum: int, maximum: int) -> None:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise ValueError("Invalid series length")
    for item in value:
        integer(item, -10_000, 10_000)


def divide(numerator: int, denominator: int) -> int:
    """Round to nearest integer, ties away from zero (also used by JavaScript)."""
    return (1 if numerator >= 0 else -1) * ((abs(numerator) * 2 + denominator) // (2 * denominator))


def predict(policy: str, observed: list[int], horizon: int) -> list[int]:
    """Return milliunit predictions using only the observed calibration prefix."""
    if policy not in POLICIES or len(observed) < 2:
        raise ValueError("Unknown policy or insufficient observations")
    n = len(observed)
    if policy.startswith("seasonal-"):
        period = int(policy.split("-")[1])
        if n < period:
            raise ValueError("The frozen policy needs a longer calibration prefix")
        return [observed[n - period + h % period] * 1000 for h in range(horizon)]
    if policy == "last":
        return [observed[-1] * 1000] * horizon
    if policy == "mean":
        return [divide(sum(observed) * 1000, n)] * horizon
    sx = n * (n - 1) // 2
    sxx = n * (n - 1) * (2 * n - 1) // 6
    sy = sum(observed)
    slope = n * sum(i * value for i, value in enumerate(observed)) - sx * sy
    denominator = n * sxx - sx * sx
    return [divide((sy * denominator + slope * (n * (n + h) - sx)) * 1000, n * denominator) for h in range(horizon)]


def learn(observed: list[int]) -> dict[str, Any]:
    """Select a policy by walk-forward error, without access to future tasks."""
    scores: list[dict[str, Any]] = []
    calls = 0
    for policy in POLICIES:
        period = int(policy.split("-")[1]) if policy.startswith("seasonal-") else 1
        if len(observed) < 2 * period + 1:
            continue
        start = max(3, period)
        errors = [abs(predict(policy, observed[:i], 1)[0] - observed[i] * 1000) for i in range(start, len(observed))]
        if not errors:
            continue
        calls += len(errors)
        scores.append(
            {"policy": policy, "error_milli": divide(sum(errors), len(errors)), "forecast_calls": len(errors)}
        )
    best = min(scores, key=lambda row: row["error_milli"])
    return {"policy": best["policy"], "scores": scores, "forecast_calls": calls}


def freeze(training: list[int]) -> dict[str, Any]:
    """Produce an immutable capability from A alone; B is not an argument."""
    series(training, 20, 64)
    learned = learn(training)
    payload = {
        "schema": PROTOCOL + ".capability",
        "training_sha256": digest(training),
        "learner": "walk-forward-mae-v1",
        "policy": learned["policy"],
        "scores": learned["scores"],
        "training_forecast_calls": learned["forecast_calls"],
        "contract": "integer-series -> milliunit-forecast; no tools, network or executable imports",
        "rollback": "Discard capability and rerun B5 without the archive",
    }
    return {**payload, "sha256": digest(payload)}


def example(scenario: str = "seasonal", seed: int = 37) -> dict[str, Any]:
    """Disclosed synthetic tasks, held out by construction, never a blind benchmark."""
    if scenario not in {"seasonal", "shift", "ablation"}:
        raise ValueError("Unknown scenario")
    integer(seed, 1, 9999)
    pattern = [6, 21, -8, 32, -17]
    training = [80 + pattern[i % 5] * 2 for i in range(40)]
    tasks = []
    for index in range(4):
        phase = (seed + index) % 5
        values = [120 + seed % 17 + index * 11 + pattern[(i + phase) % 5] * (index + 1) for i in range(14)]
        if scenario == "shift":
            values = [80 + index * 11 + i * (index + 3) for i in range(14)]
        tasks.append({"id": f"future-{seed}-{index + 1}", "observed": values[:6], "heldout": values[6:]})
    return {
        "schema": PROTOCOL + ".spec",
        "scenario": scenario,
        "seed": seed,
        "training": training,
        "tasks": tasks,
        "archive_enabled": scenario != "ablation",
        "call_cost_milli": 20,
        "human_cost_milli_per_second": 10,
        "coordination_cost_milli": 1000,
        "risk_limit_milli": 100_000,
    }


def validate_spec(spec: dict[str, Any]) -> None:
    fields(
        spec,
        "schema scenario seed training tasks archive_enabled call_cost_milli "
        "human_cost_milli_per_second coordination_cost_milli risk_limit_milli",
    )
    canonical(spec)
    if spec["schema"] != PROTOCOL + ".spec" or spec["scenario"] not in {"seasonal", "shift", "ablation", "custom"}:
        raise ValueError("Invalid experiment schema or scenario")
    integer(spec["seed"], 1, 9999)
    series(spec["training"], 20, 64)
    if type(spec["archive_enabled"]) is not bool:
        raise ValueError("archive_enabled must be boolean")
    for key in ("call_cost_milli", "human_cost_milli_per_second", "coordination_cost_milli", "risk_limit_milli"):
        integer(spec[key], 0, 10_000_000)
    if type(spec["tasks"]) is not list or not 2 <= len(spec["tasks"]) <= 8:
        raise ValueError("Provide two to eight future tasks")
    identifiers: set[str] = set()
    commitments: set[str] = {digest(spec["training"])}
    for task in spec["tasks"]:
        fields(task, "id observed heldout")
        name = task["id"]
        if not isinstance(name, str) or not name.isascii() or not 1 <= len(name) <= 64 or name in identifiers:
            raise ValueError("Task identifiers must be unique short ASCII strings")
        identifiers.add(name)
        series(task["observed"], 6, 16)
        series(task["heldout"], 4, 16)
        commitment = digest(task["observed"] + task["heldout"])
        if commitment in commitments:
            raise ValueError("Training and future tasks must have distinct content")
        commitments.add(commitment)


def compute(spec: dict[str, Any]) -> dict[str, Any]:
    """Recompute every artifact and all baseline predictions from raw inputs."""
    validate_spec(spec)
    capsule = freeze(spec["training"])
    arms: dict[str, Any] = {}
    for arm in ("B0", "B3", "B5", "B6"):
        rows = []
        calls = capsule["training_forecast_calls"] if arm == "B6" and spec["archive_enabled"] else 0
        for task in spec["tasks"]:
            observed, actual = task["observed"], task["heldout"]
            if arm == "B0":
                policy = "last"
            elif arm == "B3":
                policy = "linear"
            elif arm == "B6" and spec["archive_enabled"]:
                policy = capsule["policy"]
            else:
                local = learn(observed)
                calls += local["forecast_calls"]
                policy = local["policy"]
            forecast = predict(policy, observed, len(actual))
            calls += 1
            errors = [abs(a * 1000 - b) for a, b in zip(actual, forecast)]
            rows.append(
                {
                    "task_id": task["id"],
                    "policy": policy,
                    "predictions_milli": forecast,
                    "actual_milli": [item * 1000 for item in actual],
                    "absolute_errors_milli": errors,
                    "error_milli": sum(errors),
                    "max_error_milli": max(errors),
                }
            )
        arms[arm] = {
            "tasks": rows,
            "error_milli": sum(row["error_milli"] for row in rows),
            "forecast_calls": calls,
            "max_error_milli": max(row["max_error_milli"] for row in rows),
        }
    control, treatment = arms["B5"], arms["B6"]
    gain = control["error_milli"] - treatment["error_milli"]
    extra_calls = treatment["forecast_calls"] - control["forecast_calls"]
    compute_calls = sum(arm["forecast_calls"] for arm in arms.values())
    if not spec["archive_enabled"]:
        compute_calls += capsule["training_forecast_calls"]
    # Charge one complete validator replay, including every baseline, to the trial.
    cost = (extra_calls + compute_calls) * spec["call_cost_milli"] + spec["coordination_cost_milli"]
    return {
        "spec_sha256": digest(spec),
        "capability": capsule,
        "arms": arms,
        "execution_accounting": {"forecast_calls_per_compute": compute_calls, "creation_compute_passes": 2},
        "metrics": {
            "raw_gain_milli": gain,
            "additional_forecast_calls": extra_calls,
            "validator_forecast_calls": compute_calls,
            "modeled_overhead_milli": cost,
            "advantage_before_human_milli": gain - cost,
            "risk_passed": treatment["max_error_milli"] <= spec["risk_limit_milli"],
            "task_wins": sum(a["error_milli"] < b["error_milli"] for a, b in zip(treatment["tasks"], control["tasks"])),
        },
        "baseline_profile": "manuscript-rsi-p60; B6 is this experiment's treatment",
        "unmeasured_baselines": ["B1 incumbent", "B2 adjacent domain", "B4 strongest single agent"],
        "evidence_contact": {
            "level": "E2",
            "meaning": "executed bounded local computation",
            "E3": "pending independent replay",
            "E4": "pending independent replay and stress",
            "E5": "pending external validation or outcomes",
        },
    }


def run(spec: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter_ns()
    core = compute(spec)
    if canonical(compute(spec)) != canonical(core):  # pragma: no cover - deterministic replay invariant
        raise ValueError("Initial validator replay differs")
    elapsed = max(1, (time.perf_counter_ns() - start) // 1_000_000)
    payload = {
        "schema": PROTOCOL + ".run",
        "spec": spec,
        "core": core,
        "observations": {
            "wall_ms": elapsed,
            "source": "local-monotonic-clock",
            "energy_wh": None,
            "creation_forecast_calls": 2 * core["execution_accounting"]["forecast_calls_per_compute"],
        },
    }
    return {**payload, "sha256": digest(payload), "review": None}


def verify(report: dict[str, Any]) -> dict[str, Any]:
    fields(report, "schema spec core observations sha256 review")
    canonical(report)
    if report["schema"] != PROTOCOL + ".run" or canonical(compute(report["spec"])) != canonical(report["core"]):
        raise ValueError("Computed results or capability differ from replay")
    fields(report["observations"], "wall_ms source energy_wh creation_forecast_calls")
    if (
        report["observations"]["creation_forecast_calls"]
        != 2 * report["core"]["execution_accounting"]["forecast_calls_per_compute"]
    ):
        raise ValueError("Creation work count differs from replay")
    integer(report["observations"]["wall_ms"], 1, 86_400_000)
    if report["observations"]["source"] != "local-monotonic-clock" or report["observations"]["energy_wh"] is not None:
        raise ValueError("Invalid timing observations")
    payload = {key: value for key, value in report.items() if key not in {"sha256", "review"}}
    if digest(payload) != report["sha256"]:
        raise ValueError("Run digest mismatch")
    review = report["review"]
    if review is not None:
        fields(review, "run_sha256 decision reviewer reason control_ms treatment_ms timing_source")
        if review["run_sha256"] != report["sha256"] or review["decision"] not in {"accept", "reject", "repair"}:
            raise ValueError("Stale or invalid review")
        for key in ("reviewer", "reason"):
            if not isinstance(review[key], str) or not review[key].strip() or len(review[key]) > 500:
                raise ValueError("Review needs a bounded identity and reason")
        for key in ("control_ms", "treatment_ms"):
            integer(review[key], 1, 86_400_000)
        if review["timing_source"] not in {"operator-reported", "browser-elapsed"}:
            raise ValueError("Unsupported review timing provenance")
    return decision(report)


def decision(report: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the local claim separately from the paper's broader promotion gate."""
    review = report["review"]
    human = (
        None
        if review is None
        else divide(
            (review["treatment_ms"] - review["control_ms"]) * report["spec"]["human_cost_milli_per_second"], 1000
        )
    )
    adjusted = None if human is None else report["core"]["metrics"]["advantage_before_human_milli"] - human
    accepted = bool(
        review
        and review["decision"] == "accept"
        and adjusted is not None
        and adjusted > 0
        and report["core"]["metrics"]["raw_gain_milli"] > 0
        and report["core"]["metrics"]["risk_passed"]
        and report["spec"]["archive_enabled"]
    )
    return {
        "replay": "verified",
        "human_overhead_milli": human,
        "adjusted_advantage_milli": adjusted,
        "bounded_transfer": "accepted" if accepted else "hold",
        "manuscript_promotion": "hold",
        "missing": [
            "B1/B2/B4 comparisons",
            "independent validation",
            "measured multi-agent scaling",
            "delayed real-world outcomes",
            "calibrated alpha-WU",
        ],
        "scope": "Disclosed synthetic forecasting tasks; not external economic alpha or general intelligence",
    }


def review_run(
    report: dict[str, Any],
    verdict: str,
    reviewer: str,
    reason: str,
    control_ms: int,
    treatment_ms: int,
    timing_source: str = "operator-reported",
) -> dict[str, Any]:
    verify(report)
    result = parse(canonical(report))
    result["review"] = {
        "run_sha256": report["sha256"],
        "decision": verdict,
        "reviewer": reviewer,
        "reason": reason,
        "control_ms": control_ms,
        "treatment_ms": treatment_ms,
        "timing_source": timing_source,
    }
    verify(result)
    return result


def docket_files(report: dict[str, Any]) -> dict[str, str]:
    """Export the manuscript's complete directory contract, including missing evidence."""
    outcome = verify(report)
    core, spec = report["core"], report["spec"]

    def render(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"

    files = {
        "00_manifest.md": f"# Evidence Docket\n\nProtocol: {PROTOCOL}\n\nRun: {report['sha256']}\n\n"
        f"Manuscript SHA-256: {MANUSCRIPT_SHA256}\n\nLocal replay verifies computation, not independence.\n",
        "01_claims_matrix.md": "# Claims\n\n| Claim | Status |\n|---|---|\n"
        f"| Bounded future-task transfer | {outcome['bounded_transfer']} |\n"
        "| General RSI, economic alpha, external validation | Unproven |\n"
        "| Manuscript promotion | HOLD: missing comparators, scaling and external evidence |\n",
        "02_environment.md": "# Environment\n\nPython 3.11–3.13 or modern browser/Node 22; integer arithmetic.\n"
        "No network, LLM, tools or settlement used by the experiment. Public synthetic fixtures; "
        "not blinded. Wall time is an observation, not independently attested.\n",
        "03_benchmark_tasks/spec.json": render(spec),
        "04_baselines/comparison.json": render(
            {"profile": core["baseline_profile"], "arms": core["arms"], "not_measured": core["unmeasured_baselines"]}
        ),
        "05_agialpha_runs/run.json": render(report),
        "06_proof_bundles/capability.json": render(core["capability"]),
        "07_replay_logs/replay.json": render(
            {
                "spec_sha256": core["spec_sha256"],
                "core_sha256": digest(core),
                "method": "recompute all predictions",
                "independent": False,
            }
        ),
        "08_cost_ledgers/costs.json": render(
            {
                "metrics": core["metrics"],
                "observations": report["observations"],
                "human_review": report["review"],
                "assumed_rates": {
                    key: spec[key]
                    for key in ("call_cost_milli", "human_cost_milli_per_second", "coordination_cost_milli")
                },
                "unit": "modeled milliunits, not currency",
                "tokens": 0,
                "tool_calls": 0,
                "training_cost": "all A selection calls charged to B6; no amortization",
                "unmeasured": ["energy", "monetary compute cost", "active human attention"],
                "execution_accounting": core["execution_accounting"],
                "replay_and_baseline_work": "creation includes all baselines and one charged full replay; later UI preparation, exports and replays are outside this timing",
            }
        ),
        "09_safety_ledgers/safety.json": render(
            {
                "risk_limit_milli": spec["risk_limit_milli"],
                "risk_passed": core["metrics"]["risk_passed"],
                "network": False,
                "execution": "fixed arithmetic only",
                "real_world_risk": "not measured",
                "rollback": core["capability"]["rollback"],
            }
        ),
        "10_validator_reports/review.json": render(
            {"review": report["review"], "independent": False, "evidence_contact": core["evidence_contact"]}
        ),
        "11_alpha_wu_calibration/status.json": render(
            {"status": "uncalibrated", "alpha_WU": None, "reason": "No external reference workload or verifier"}
        ),
        "12_summary_tables/outcome.json": render(outcome),
        "05_agialpha_runs/action_reason_trace.json": render(
            [
                {
                    "action": "freeze",
                    "reason": "Prevent future answers entering policy selection",
                    "evidence": core["capability"]["sha256"],
                },
                {
                    "action": "compare",
                    "reason": "Measure future tasks against disclosed baselines",
                    "evidence": core["spec_sha256"],
                },
                {
                    "action": "gate",
                    "reason": "Require accepted review, positive adjusted gain and bounded forecast error",
                    "evidence": outcome,
                },
            ]
        ),
    }
    files["checksums.json"] = render(
        {name: hashlib.sha256(value.encode()).hexdigest() for name, value in files.items()}
    )
    return files


def export_docket(report: dict[str, Any]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(docket_files(report).items()):
            archive.writestr(name, content)
    return stream.getvalue()


def verify_docket(data: bytes) -> dict[str, Any]:
    """Read fixed in-memory paths; reject tampering, duplicate entries and zip bombs."""
    if len(data) > MAX_BYTES * 3:
        raise ValueError("Docket is too large")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        info = archive.infolist()
        if len(info) > 20 or len({item.filename for item in info}) != len(info):
            raise ValueError("Invalid docket entries")
        if any(item.file_size > MAX_BYTES for item in info) or sum(item.file_size for item in info) > MAX_BYTES * 3:
            raise ValueError("Docket expands beyond the size limit")
        report = parse(archive.read("05_agialpha_runs/run.json").decode())
        expected = docket_files(report)
        if set(archive.namelist()) != set(expected):
            raise ValueError("Docket paths differ from the canonical contract")
        if any(archive.read(name).decode() != content for name, content in expected.items()):
            raise ValueError("Docket content differs from replay")
    return verify(report)
