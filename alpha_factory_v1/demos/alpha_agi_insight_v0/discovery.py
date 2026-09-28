# SPDX-License-Identifier: Apache-2.0
"""Exact, bounded opportunity screening and review planning over supplied evidence."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

SCHEMA = "agialpha.insight.scenario.v1"
REPORT_SCHEMA = "agialpha.insight.dossier.v1"
MAX_BYTES = 1_000_000
METRICS = ("demand", "feasibility", "readiness", "advantage")
SCOPE = (
    "Priority scores describe supplied assumptions, not forecast probabilities or economic value. "
    "Source coverage records supplied excerpts, not authenticated evidence. Selected opportunities require "
    "independent review. Nova-Seed drafts are plaintext, unminted and unfunded; jobs are unsubmitted."
)


def canonical(value: Any) -> bytes:
    def normalize(item: Any) -> Any:
        if isinstance(item, float) and math.isfinite(item) and item.is_integer():
            return int(item)
        if isinstance(item, list):
            return [normalize(v) for v in item]
        if isinstance(item, dict):
            return {key: normalize(v) for key, v in item.items()}
        return item

    return json.dumps(
        normalize(value), ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def parse(data: bytes) -> Any:
    if len(data) > MAX_BYTES:
        raise ValueError(f"Input exceeds {MAX_BYTES} bytes")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON keys are not accepted")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ValueError("Non-finite JSON numbers are not accepted")

    def bounded(value: Any, depth: int = 0) -> None:
        if depth > 24:
            raise ValueError("JSON nesting exceeds 24 levels")
        if isinstance(value, dict):
            for key, item in value.items():
                bounded(key, depth + 1)
                bounded(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                bounded(item, depth + 1)
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Non-finite JSON numbers are not accepted")
        elif isinstance(value, str) and any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ValueError("Invalid Unicode")

    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
        bounded(result)
        return result
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


def text(value: Any, label: str, maximum: int = 240) -> None:
    if (
        not isinstance(value, str)
        or not value.strip(
            " \t\n\r\v\f\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
        )
        or len(value.encode("utf-8", errors="replace")) > maximum
    ):
        raise ValueError(f"{label} must be nonempty text of at most {maximum} UTF-8 bytes")
    if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError(f"{label} contains a control character or invalid Unicode")


def identifier(value: Any) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", value):
        raise ValueError("IDs require 1–40 lowercase letters, digits or hyphens, starting with a letter")


def validate(source: Any) -> dict[str, Any]:
    keys(source, {"schema", "id", "title", "note", "weights", "policy", "sources", "opportunities"}, "Scenario")
    if source["schema"] != SCHEMA:
        raise ValueError("Unsupported Insight scenario schema")
    identifier(source["id"])
    text(source["title"], "Title", 160)
    text(source["note"], "Source note", 600)
    keys(source["weights"], set(METRICS), "Weights")
    for value in source["weights"].values():
        integer(value, 0, 10_000, "Weight")
    if sum(source["weights"].values()) != 10_000:
        raise ValueError("Weights must sum to 10000 basis points")
    policy = source["policy"]
    keys(policy, {"reviewMinutes", "minScoreBps", "minCoverageBps", "jobBountyTokens"}, "Policy")
    for field, low, high in (
        ("reviewMinutes", 0, 2400),
        ("minScoreBps", 0, 10_000),
        ("minCoverageBps", 0, 10_000),
        ("jobBountyTokens", 1, 1_000_000),
    ):
        integer(policy[field], low, high, field)
    sources = source["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 32:
        raise ValueError("Provide 1–32 source excerpts")
    source_ids: set[str] = set()
    for item in sources:
        keys(item, {"id", "title", "url", "excerpt", "kind"}, "Source")
        identifier(item["id"])
        if item["id"] in source_ids:
            raise ValueError("Duplicate source id")
        source_ids.add(item["id"])
        text(item["title"], "Source title", 160)
        text(item["excerpt"], "Source excerpt", 1200)
        text(item["url"], "Source URL", 500)
        if not re.fullmatch(r"https://[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?(?:[/#?][^\s\\\ufeff]*)?", item["url"]):
            raise ValueError(
                "Sources require HTTPS hostnames without credentials or explicit ports; URLs are never fetched"
            )
        if item["kind"] not in ("synthetic", "public-excerpt"):
            raise ValueError("Source kind must be synthetic or public-excerpt")
    opportunities = source["opportunities"]
    if not isinstance(opportunities, list) or not 1 <= len(opportunities) <= 24:
        raise ValueError("Provide 1–24 opportunities")
    ids: set[str] = set()
    for item in opportunities:
        keys(
            item,
            {"id", "sector", "title", "thesis", "goal", "successMetric", "reviewMinutes", "signals"},
            "Opportunity",
        )
        identifier(item["id"])
        if item["id"] in ids:
            raise ValueError("Duplicate opportunity id")
        ids.add(item["id"])
        for field, size in (("sector", 80), ("title", 160), ("thesis", 500), ("goal", 240), ("successMetric", 400)):
            text(item[field], field, size)
        integer(item["reviewMinutes"], 1, 2400, "Review minutes")
        keys(item["signals"], set(METRICS), "Signals")
        for signal in item["signals"].values():
            keys(signal, {"low", "base", "high", "source"}, "Signal")
            for field in ("low", "base", "high"):
                integer(signal[field], 0, 10_000, "Signal " + field)
            if not signal["low"] <= signal["base"] <= signal["high"]:
                raise ValueError("Each signal must satisfy low <= base <= high")
            if not isinstance(signal["source"], str) or signal["source"] not in source_ids | {""}:
                raise ValueError("Signal source must identify a supplied excerpt or be empty")
    result: dict[str, Any] = json.loads(canonical(source))
    for group in (result["weights"], result["policy"]):
        for field in group:
            group[field] = int(group[field])
    for item in result["opportunities"]:
        item["reviewMinutes"] = int(item["reviewMinutes"])
        for signal in item["signals"].values():
            for field in ("low", "base", "high"):
                signal[field] = int(signal[field])
    return result


def evaluate(source: Any) -> dict[str, Any]:
    source = validate(source)
    weights, policy = source["weights"], source["policy"]
    input_hash = digest(source)
    rows = []
    for item in source["opportunities"]:
        signals = item["signals"]
        scores = {level: sum(weights[m] * signals[m][level] for m in METRICS) for level in ("low", "base", "high")}
        coverage = sum(weights[m] for m in METRICS if signals[m]["source"])
        reasons = []
        if coverage < policy["minCoverageBps"]:
            reasons.append("Missing supplied source coverage")
        if scores["low"] < policy["minScoreBps"] * 10_000:
            reasons.append("Conservative priority below threshold")
        rows.append(
            {
                "id": item["id"],
                "title": item["title"],
                "sector": item["sector"],
                "scores": scores,
                "scoreDenominator": 10_000,
                "coverageBps": coverage,
                "reviewMinutes": item["reviewMinutes"],
                "eligible": not reasons,
                "reasons": reasons,
                "missingSignals": [m for m in METRICS if not signals[m]["source"]],
            }
        )
    rows.sort(key=lambda row: (-row["scores"]["low"], -row["scores"]["base"], row["id"]))
    # Exact 0/1 knapsack: every opportunity may consume review capacity once.
    choices: dict[int, tuple[int, tuple[str, ...]]] = {0: (0, ())}
    for row in sorted(rows, key=lambda row: row["id"]):
        if not row["eligible"]:
            continue
        for minutes, (score, ids) in list(choices.items()):
            cost = minutes + row["reviewMinutes"]
            if cost > policy["reviewMinutes"]:
                continue
            candidate = (score + row["scores"]["low"], ids + (row["id"],))
            previous = choices.get(cost)
            if (
                previous is None
                or candidate[0] > previous[0]
                or (candidate[0] == previous[0] and candidate[1] < previous[1])
            ):
                choices[cost] = candidate
    used, (objective, selected) = min(choices.items(), key=lambda x: (-x[1][0], x[0], x[1][1]))
    for row in rows:
        row["selected"] = row["id"] in selected
        row["status"] = (
            "REVIEW_REQUIRED" if row["selected"] else "CAPACITY_DEFERRED" if row["eligible"] else "EVIDENCE_REQUIRED"
        )
    jobs = []
    drafts = []
    by_id = {item["id"]: item for item in source["opportunities"]}
    for row in rows:
        item = by_id[row["id"]]
        goal = f"Verify Insight {item['id']}. Input SHA-256: {input_hash}. {item['goal']}"
        job = {
            "goal": goal,
            "successMetric": item["successMetric"],
            "bounty": str(policy["jobBountyTokens"] * 10**18),
            "duration": 604800,
            "priceWeight": 5000,
        }
        jobs.append(job)
        if row["selected"]:
            body = {
                "schema": "agialpha.insight.nova-seed-draft.v1",
                "opportunityId": item["id"],
                "inputSha256": input_hash,
                "foresightGenome": item,
                "sources": [s for s in source["sources"] if s["id"] in {v["source"] for v in item["signals"].values()}],
                "fusionPlanJobs": [job],
                "state": "UNREVIEWED_PLAINTEXT_DRAFT",
                "scope": SCOPE,
            }
            drafts.append({**body, "sha256": digest(body)})
    best = rows[0]
    rival = max((row["scores"]["high"] for row in rows[1:]), default=-1)
    result = {
        "status": "REVIEW_REQUIRED" if selected else "NO_REVIEW_PORTFOLIO",
        "inputSha256": input_hash,
        "ranking": rows,
        "selectedIds": list(selected),
        "reviewMinutesUsed": used,
        "reviewMinutesRemaining": policy["reviewMinutes"] - used,
        "objectiveNumerator": objective,
        "objectiveDenominator": 10_000,
        "rankSeparation": best["scores"]["low"] > rival,
        "rankSeparationMeaning": "Top conservative score exceeds every rival optimistic score; supplied intervals are not confidence intervals.",
        "jobs": jobs,
        "novaSeedDrafts": drafts,
        "unsubmittedBountyTokens": len(jobs) * policy["jobBountyTokens"],
        "scope": SCOPE,
    }
    report = {"schema": REPORT_SCHEMA, "input": source, "result": result}
    return {**report, "sha256": digest(report)}


def verify(report: Any) -> dict[str, Any]:
    keys(report, {"schema", "input", "result", "sha256"}, "Dossier")
    expected = evaluate(report["input"])
    if canonical(report) != canonical(expected):
        raise ValueError("Dossier differs from recomputation; imported scores and selections are not trusted")
    return expected


def literal(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>()#+.!|])", r"\\\1", value)


def hundredths(value: int, divisor: int = 1) -> str:
    units = value // divisor
    return f"{units // 100}.{units % 100:02d}"


def brief(report: dict[str, Any]) -> str:
    source, result = report["input"], report["result"]
    lines = [
        f"# {literal(source['title'])}",
        "",
        result["status"],
        "",
        literal(source["note"]),
        "",
        f"Review capacity: {result['reviewMinutesUsed']} / {source['policy']['reviewMinutes']} minutes.",
        "",
        "| Opportunity | Conservative priority / 100 | Supplied coverage | Decision |",
        "|---|---:|---:|---|",
    ]
    for row in result["ranking"]:
        lines.append(
            f"| {literal(row['title'])} | {hundredths(row['scores']['low'], 10000)} | {hundredths(row['coverageBps'])}% | {row['status']} |"
        )
    lines += [
        "",
        "Selection maximizes the sum of conservative priority numerators within supplied review capacity.",
        "It does not maximize profit or establish evidence quality. Ties use lower review time, then lexical IDs.",
        "",
        f"Unsubmitted job bounties: {result['unsubmittedBountyTokens']} AGIALPHA.",
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
        "nova-seeds.json": canonical(report["result"]["novaSeedDrafts"]) + b"\n",
        "review-brief.md": brief(report).encode("utf-8"),
    }
    values["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(values.items())
    ).encode()
    return values


def write_bundle(report: dict[str, Any], root: Path) -> Path:
    values = artifacts(report)
    root.mkdir(parents=True, exist_ok=True)
    target: Path = root / str(report["sha256"])
    try:
        target.mkdir()
    except FileExistsError:
        if target.is_symlink() or not target.is_dir() or {p.name for p in target.iterdir()} != set(values):
            raise ValueError("Existing run is incomplete or altered; choose a new output directory") from None
        if any(
            (target / name).is_symlink() or not (target / name).is_file() or (target / name).read_bytes() != data
            for name, data in values.items()
        ):
            raise ValueError("Existing run differs; choose a new output directory") from None
        return target
    for name, data in values.items():
        with (target / name).open("xb") as stream:
            stream.write(data)
    return target
