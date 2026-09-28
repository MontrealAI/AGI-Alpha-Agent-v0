# SPDX-License-Identifier: Apache-2.0
"""Bounded, reproducible governance review; no approval or execution authority."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

SCHEMA = "agialpha.governance.scenario.v1"
REPORT_SCHEMA = "agialpha.governance.dossier.v1"
MAX_BYTES = 256_000
BPS = 10_000
FEMTO = 10**15
SCOPE = (
    "Conditional arithmetic over supplied assumptions. This dossier is not an authenticated vote, "
    "a proof of unique equilibrium, a calibrated safety certificate or permission to execute. "
    "All verification jobs are unsubmitted; independent validators must review the sources, identities and policy."
)
BOUNDS = {
    "incentives": {
        "reward": (1, 100_000),
        "temptation": (2, 100_000),
        "punishment": (0, 99_999),
        "discountBps": (0, 9_999),
        "detectionBps": (0, 10_000),
        "stake": (0, 100_000),
    },
    "risk": {"perActionFemto": (0, FEMTO), "actions": (1, 10**12), "budgetFemto": (0, FEMTO)},
    "policy": {
        "quorumBps": (1, 10_000),
        "supportBps": (5_001, 10_000),
        "minStakeTokens": (1, 1_000_000),
        "jobBountyTokens": (1, 1_000_000),
    },
    "upgrade": {
        "queuedAt": (0, 8_000_000_000_000),
        "now": (0, 8_000_000_000_000),
        "delaySeconds": (604_800, 31_536_000),
    },
}
GATES = (
    (
        "identity",
        "Independent identities",
        "Verify each eligible validator's ENS ownership, controlling principal and stake at the proposal snapshot; reject shared controllers.",
    ),
    (
        "credits",
        "Quadratic credit budget",
        "Recompute every eligible ballot cost as votes squared; verify credit issuance and signed ballots against the proposal snapshot.",
    ),
    (
        "quorum",
        "Participation quorum",
        "Verify the complete eligible electorate and participation count against the frozen governance registry.",
    ),
    (
        "mandate",
        "Support threshold",
        "Verify signed positive and negative vote totals, strict majority and the declared support threshold.",
    ),
    (
        "incentives",
        "Conditional deterrence",
        "Validate payoffs, monitoring and enforceable slashing; independently derive the stated grim-trigger incentive condition and test deviations.",
    ),
    (
        "risk",
        "Aggregate risk budget",
        "Calibrate the per-action failure upper bound for the stated action envelope; independently check the union bound against the total budget.",
    ),
    (
        "timelock",
        "Upgrade waiting period",
        "Verify the proposal's on-chain queue timestamp, governance delay and canonical chain time at execution.",
    ),
    (
        "policy",
        "Policy commitment",
        "Review the exact proposed policy bytes, confirm their SHA-256 commitment and match the approved governance policy commitment.",
    ),
    (
        "pause",
        "Emergency stop",
        "Verify the authoritative pause state and independently exercise stop, rollback and recovery before authorizing execution.",
    ),
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def parse(data: bytes) -> Any:
    """Reject ambiguous keys, non-finite numbers, excess depth and oversized imports."""
    if len(data) > MAX_BYTES:
        raise ValueError(f"Input exceeds {MAX_BYTES} bytes")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON value: {value}")

    def depth(value: Any, level: int = 0) -> None:
        if level > 24:
            raise ValueError("JSON nesting is too deep")
        if isinstance(value, dict):
            for item in value.values():
                depth(item, level + 1)
        elif isinstance(value, list):
            for item in value:
                depth(item, level + 1)

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
        depth(value)
        return value
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("Input must be bounded UTF-8 JSON") from exc


def read_json(path: Path) -> Any:
    with path.open("rb") as stream:
        return parse(stream.read(MAX_BYTES + 1))


def keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} must contain exactly: {', '.join(sorted(expected))}")


def integer(value: Any, low: int, high: int, label: str) -> None:
    if type(value) not in (int, float) or not low <= value <= high or int(value) != value:
        raise ValueError(f"{label} must be an integer from {low} through {high}")


def text(value: Any, label: str, maximum: int = 160) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must be nonempty text of at most {maximum} characters")
    if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError(f"{label} contains invalid Unicode or control characters")


def validate(source: Any) -> dict[str, Any]:
    """Validate every supplied field before evaluating gates; never coerce booleans."""
    keys(source, {"schema", "id", "title", "note", "incentives", "risk", "policy", "upgrade", "validators"}, "Scenario")
    if source["schema"] != SCHEMA:
        raise ValueError("Unsupported governance scenario schema")
    if not isinstance(source["id"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", source["id"]):
        raise ValueError("Scenario id must use 1–40 lowercase letters, digits or hyphens, starting with a letter")
    text(source["title"], "Title")
    text(source["note"], "Source note", 500)
    for section, fields in BOUNDS.items():
        extras = {"paused", "proposedPolicyHash", "expectedPolicyHash"} if section == "upgrade" else set()
        keys(source[section], set(fields) | extras, section)
        for field, (low, high) in fields.items():
            integer(source[section][field], low, high, f"{section}.{field}")
    i, u = source["incentives"], source["upgrade"]
    if not i["temptation"] > i["reward"] > i["punishment"]:
        raise ValueError("Payoffs must satisfy temptation > reward > punishment")
    if u["now"] < u["queuedAt"]:
        raise ValueError("Current time cannot precede the queue timestamp")
    if type(u["paused"]) is not bool:
        raise ValueError("Paused must be a boolean")
    for name in ("proposedPolicyHash", "expectedPolicyHash"):
        if not isinstance(u[name], str) or not re.fullmatch(r"[0-9a-f]{64}", u[name]):
            raise ValueError(f"{name} must be 64 lowercase hexadecimal characters")
    validators = source["validators"]
    if not isinstance(validators, list) or not 1 <= len(validators) <= 64:
        raise ValueError("Use 1–64 validator records")
    names = set()
    for v in validators:
        keys(v, {"name", "controller", "credits", "votes", "stakeTokens", "eligible"}, "Validator")
        if not isinstance(v["name"], str) or not re.fullmatch(
            r"[a-z][a-z0-9-]{0,39}\.alpha\.club\.agi\.eth", v["name"]
        ):
            raise ValueError("Validator names must be lowercase name.alpha.club.agi.eth")
        if v["name"] in names:
            raise ValueError("Duplicate validator name")
        names.add(v["name"])
        if not isinstance(v["controller"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", v["controller"]):
            raise ValueError("Controller ids must use 1–40 lowercase letters, digits or hyphens")
        integer(v["credits"], 0, 1_000_000, "Voting credits")
        integer(v["votes"], -1000, 1000, "Votes")
        integer(v["stakeTokens"], 0, 1_000_000, "Validator stake")
        if type(v["eligible"]) is not bool:
            raise ValueError("Eligible must be a boolean")
    # Normalize integer-valued JSON numbers identically to JavaScript's Number representation.
    result: dict[str, Any] = json.loads(canonical(source))
    for section, fields in BOUNDS.items():
        for field in fields:
            result[section][field] = int(result[section][field])
    for v in result["validators"]:
        for field in ("credits", "votes", "stakeTokens"):
            v[field] = int(v[field])
    return result


def evaluate(source: Any) -> dict[str, Any]:
    """Recompute all gates using integers; a passing model still requires review."""
    source = validate(source)
    i, r, p, u = (source[name] for name in ("incentives", "risk", "policy", "upgrade"))
    electorate = [v for v in source["validators"] if v["eligible"] and v["stakeTokens"] >= p["minStakeTokens"]]
    controllers = [v["controller"] for v in electorate]
    duplicates = sorted({c for c in controllers if controllers.count(c) > 1})
    invalid = [v["name"] for v in electorate if v["votes"] ** 2 > v["credits"]]
    ballots = [v for v in electorate if v["votes"] != 0 and v["votes"] ** 2 <= v["credits"]]
    yes = sum(max(0, v["votes"]) for v in ballots)
    no = sum(max(0, -v["votes"]) for v in ballots)
    margin = (
        i["reward"] * BPS**2
        - (BPS - i["discountBps"]) * (i["temptation"] * BPS - i["detectionBps"] * i["stake"])
        - i["discountBps"] * (i["detectionBps"] * i["punishment"] + (BPS - i["detectionBps"]) * i["reward"])
    )
    exposure = r["perActionFemto"] * r["actions"]
    bound = min(FEMTO, exposure)
    unlock = u["queuedAt"] + u["delaySeconds"]
    passed = {
        "identity": bool(electorate) and not duplicates,
        "credits": not invalid,
        "quorum": bool(electorate) and len(ballots) * BPS >= len(electorate) * p["quorumBps"],
        "mandate": yes > no and yes * BPS >= (yes + no) * p["supportBps"],
        "incentives": margin >= 0,
        "risk": bound <= r["budgetFemto"],
        "timelock": u["now"] >= unlock,
        "policy": u["proposedPolicyHash"] == u["expectedPolicyHash"],
        "pause": not u["paused"],
    }
    gates = [{"id": gid, "title": title, "passed": passed[gid], "nextStep": step} for gid, title, step in GATES]
    input_hash = digest(source)
    jobs = [
        {
            "goal": f"Governance verification: {title}. Input SHA-256: {input_hash}",
            "successMetric": step,
            "bounty": str(p["jobBountyTokens"] * 10**18),
            "duration": 604800,
            "priceWeight": 5000,
        }
        for _, title, step in GATES
    ]
    result = {
        "status": "REVIEW_REQUIRED" if all(passed.values()) else "BLOCKED",
        "inputSha256": input_hash,
        "gates": gates,
        "ballot": {
            "eligible": len(electorate),
            "participants": len(ballots),
            "yes": yes,
            "no": no,
            "creditsSpent": sum(v["votes"] ** 2 for v in ballots),
            "duplicateControllers": duplicates,
            "overBudget": invalid,
        },
        "incentives": {
            "marginNumerator": str(margin),
            "marginDenominator": BPS**2,
            "condition": "R >= (1-delta)*(T-detection*stake) + delta*(detection*P+(1-detection)*R)",
        },
        "risk": {
            "exposureFemto": str(exposure),
            "unionBoundFemto": bound,
            "maxPerActionFemto": r["budgetFemto"] // r["actions"],
        },
        "upgrade": {"unlockAt": unlock, "secondsRemaining": max(0, unlock - u["now"])},
        "jobs": jobs,
        "reservedBountyTokens": len(jobs) * p["jobBountyTokens"],
        "scope": SCOPE,
    }
    report = {"schema": REPORT_SCHEMA, "input": source, "result": result}
    return {**report, "sha256": digest(report)}


def verify(report: Any) -> dict[str, Any]:
    """Never trust an imported status or checksum without recomputing every output."""
    keys(report, {"schema", "input", "result", "sha256"}, "Dossier")
    expected = evaluate(report["input"])
    if canonical(report) != canonical(expected):
        raise ValueError("Dossier differs from recomputation; supplied results are not trusted")
    return expected


def markdown_text(value: str) -> str:
    """Keep supplied text literal in portable Markdown, including HTML and links."""
    return re.sub(r"([\\`*_{}\[\]<>()#+.!|])", r"\\\1", value)


def brief(report: dict[str, Any]) -> str:
    source, result = report["input"], report["result"]
    lines = [
        f"# {markdown_text(source['title'])}",
        "",
        f"Status: {result['status']}",
        f"Source note: {markdown_text(source['note'])}",
        "",
    ]
    for gate in result["gates"]:
        lines += [
            f"- {'PASS (model)' if gate['passed'] else 'BLOCKED'}: {gate['title']}",
            f"  Review: {gate['nextStep']}",
        ]
    lines += [
        "",
        f"Unsubmitted verification bounties: {result['reservedBountyTokens']} AGIALPHA.",
        "",
        "Model: infinite repeated play, stationary payoffs and public detection probability, risk-neutral agents, "
        "and no false positives. A detected unilateral deviation is slashed once and triggers credible grim-trigger "
        "punishment; an undetected deviation returns to cooperation. It is a conditional incentive check, not uniqueness.",
        "Risk: min(1, action count × per-action upper bound). No independence assumption or unverified mitigation credit.",
        "The supplied identity roster, risk bounds, policy hashes and clock still need authoritative verification.",
        "",
        SCOPE,
        "",
        f"Dossier SHA-256: {report['sha256']}",
        "",
    ]
    return "\n".join(lines)


def artifacts(report: dict[str, Any]) -> dict[str, bytes]:
    report = verify(report)
    values = {
        "scenario.json": canonical(report["input"]) + b"\n",
        "dossier.json": canonical(report) + b"\n",
        "jobs.json": canonical(report["result"]["jobs"]) + b"\n",
        "review-brief.md": brief(report).encode("utf-8"),
    }
    values["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(values.items())
    ).encode()
    return values


def write_bundle(report: dict[str, Any], root: Path) -> Path:
    """Retain prior runs; reject altered, partial or symlinked content-addressed runs."""
    values = artifacts(report)
    root.mkdir(parents=True, exist_ok=True)
    target: Path = root / report["sha256"]
    try:
        target.mkdir()
    except FileExistsError:
        if target.is_symlink() or not target.is_dir() or {p.name for p in target.iterdir()} != set(values):
            raise ValueError("Existing run is incomplete or altered; choose a new output directory") from None
        if any((target / name).is_symlink() or (target / name).read_bytes() != data for name, data in values.items()):
            raise ValueError("Existing run differs from the dossier; choose a new output directory") from None
        return target
    for name, data in values.items():
        with (target / name).open("xb") as stream:
            stream.write(data)
    return target
