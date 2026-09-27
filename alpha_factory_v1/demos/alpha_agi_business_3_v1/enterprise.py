# SPDX-License-Identifier: Apache-2.0
"""Reproducible enterprise allocation, evidence and unsubmitted Ascension jobs."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any

SCHEMA = "agialpha.business3.scenario.v1"
REPORT_SCHEMA = "agialpha.business3.dossier.v1"
MAX_INPUT_BYTES = 256_000
MAX_REPORT_BYTES = 2_000_000
SECTORS = ("finance", "biotech", "materials", "policy", "energy", "manufacturing", "logistics", "research", "quantum")
POLICY_BOUNDS = {
    "budgetUsd": (0, 1_000_000_000),
    "staffDays": (0, 100_000),
    "reviewMinutes": (0, 100_000),
    "jobBudgetTokens": (0, 10_000_000),
    "maxProjects": (0, 16),
    "maxPerSector": (1, 16),
    "discountBps": (0, 10_000),
    "benefitHaircutBps": (0, 10_000),
    "costOverrunBps": (0, 10_000),
    "minEvidenceBps": (0, 10_000),
    "minDownsideNpvUsd": (-1_000_000_000, 1_000_000_000),
}
PROJECT_BOUNDS = {
    "costUsd": (1, 100_000_000),
    "staffDays": (1, 100_000),
    "reviewMinutes": (1, 100_000),
    "bountyTokens": (1, 1_000_000),
    "durationDays": (1, 90),
    "evidenceBps": (0, 10_000),
}
SCOPE = (
    "Deterministic planning over supplied assumptions, not investment execution or a prediction guarantee. "
    "All jobs are unsubmitted; evidence needs independent review. No wallet, mint, trade or payment is performed. "
    "USD project capital and AGIALPHA job bounties are separate budgets without an assumed exchange rate."
)


def canonical(value: Any) -> bytes:
    """Encode the bounded integer-only schema for portable SHA-256 commitments."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def parse(data: bytes, limit: int = MAX_INPUT_BYTES) -> Any:
    """Reject duplicate keys, non-finite values, oversized data and invalid UTF-8."""
    if len(data) > limit:
        raise ValueError(f"Input exceeds {limit:,} bytes")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON value: {value}")

    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("Input must be bounded UTF-8 JSON") from exc


def read_json(path: Path, limit: int = MAX_INPUT_BYTES) -> Any:
    with path.open("rb") as source:
        return parse(source.read(limit + 1), limit)


def _keys(value: Any, required: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(f"{label} must contain exactly: {', '.join(sorted(required))}")


def _text(value: Any, label: str, maximum: int = 160) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must be nonempty text of at most {maximum} characters")
    if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError(f"{label} contains a control character or invalid Unicode")


def _integer(value: Any, low: int, high: int, label: str) -> None:
    if type(value) not in (int, float) or not low <= value <= high or int(value) != value:
        raise ValueError(f"{label} must be an integer from {low} through {high}")


def validate(source: Any) -> dict[str, Any]:
    """Validate units, references and hard complexity limits before enumeration."""
    _keys(source, {"schema", "id", "title", "provenance", "policy", "projects"}, "Scenario")
    if source["schema"] != SCHEMA:
        raise ValueError("Unsupported Business 3 scenario schema")
    _text(source["id"], "Scenario id", 60)
    _text(source["title"], "Title")
    _keys(source["provenance"], {"kind", "note"}, "Provenance")
    if source["provenance"]["kind"] not in ("constructed", "supplied"):
        raise ValueError("Provenance kind must be constructed or supplied")
    _text(source["provenance"]["note"], "Provenance note", 500)
    _keys(source["policy"], set(POLICY_BOUNDS), "Policy")
    for key, (low, high) in POLICY_BOUNDS.items():
        _integer(source["policy"][key], low, high, key)
    projects = source["projects"]
    if not isinstance(projects, list) or not 1 <= len(projects) <= 16:
        raise ValueError("A scenario requires 1–16 projects")
    ids = set()
    for project in projects:
        _keys(
            project,
            set(PROJECT_BOUNDS) | {"id", "name", "sector", "cashflowsUsd", "sources", "requires", "excludes", "metric"},
            "Project",
        )
        if not isinstance(project["id"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", project["id"]):
            raise ValueError("Project ids must use 1–40 lowercase letters, digits or hyphens, starting with a letter")
        if project["id"] in ids:
            raise ValueError(f"Duplicate project id: {project['id']}")
        ids.add(project["id"])
        _text(project["name"], "Project name", 100)
        _text(project["metric"], "Success metric", 240)
        if len(project["metric"].encode("utf-8")) > 400:
            raise ValueError("Success metric must fit 400 UTF-8 bytes for the Ascension job")
        if project["sector"] not in SECTORS:
            raise ValueError(f"Sector must be one of: {', '.join(SECTORS)}")
        for key, (low, high) in PROJECT_BOUNDS.items():
            _integer(project[key], low, high, f"{project['id']}.{key}")
        if not isinstance(project["cashflowsUsd"], list) or len(project["cashflowsUsd"]) != 3:
            raise ValueError("Each project needs three annual net operating cash flows in whole USD")
        for cash in project["cashflowsUsd"]:
            _integer(cash, -100_000_000, 100_000_000, "Annual cash flow")
        if not isinstance(project["sources"], list) or not 1 <= len(project["sources"]) <= 8:
            raise ValueError("Every project needs 1–8 source descriptions")
        for note in project["sources"]:
            _text(note, "Source description", 300)
        for key in ("requires", "excludes"):
            values = project[key]
            if (
                not isinstance(values, list)
                or any(not isinstance(value, str) for value in values)
                or len(values) != len(set(values))
                or project["id"] in values
            ):
                raise ValueError(f"{key} must contain distinct other project ids")
    for project in projects:
        if not set(project["requires"] + project["excludes"]) <= ids:
            raise ValueError(f"Unknown dependency or exclusion in {project['id']}")
        if set(project["requires"]) & set(project["excludes"]):
            raise ValueError("A project cannot both require and exclude the same project")
    visiting: set[str] = set()
    visited: set[str] = set()
    by_id = {p["id"]: p for p in projects}

    def visit(pid: str) -> None:
        if pid in visiting:
            raise ValueError("Project dependencies must be acyclic")
        if pid in visited:
            return
        visiting.add(pid)
        for dependency in by_id[pid]["requires"]:
            visit(dependency)
        visiting.remove(pid)
        visited.add(pid)

    for pid in by_id:
        visit(pid)
    normalized = parse(canonical(source))
    normalized["policy"] = {key: int(value) for key, value in normalized["policy"].items()}
    normalized["projects"].sort(key=lambda p: p["id"])
    for project in normalized["projects"]:
        for key in PROJECT_BOUNDS:
            project[key] = int(project[key])
        project["cashflowsUsd"] = [int(value) for value in project["cashflowsUsd"]]
        project["requires"].sort()
        project["excludes"].sort()
    return normalized  # type: ignore[no-any-return]


def economics(project: dict[str, Any], policy: dict[str, int]) -> dict[str, int]:
    """Discount year-end cash flows with integer floors and explicit adverse shocks."""
    rate = 10_000 + policy["discountBps"]
    expected = sum(cash * 10_000**year // rate**year for year, cash in enumerate(project["cashflowsUsd"], 1))
    stressed = sum(
        (cash * (10_000 - policy["benefitHaircutBps"] if cash >= 0 else 10_000 + policy["benefitHaircutBps"]) // 10_000)
        * 10_000**year
        // rate**year
        for year, cash in enumerate(project["cashflowsUsd"], 1)
    )
    cost = (project["costUsd"] * (10_000 + policy["costOverrunBps"]) + 9999) // 10_000
    return {"expectedNpvUsd": expected - project["costUsd"], "downsideNpvUsd": stressed - cost, "stressedCostUsd": cost}


def _portfolio(indices: list[int], projects: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "projectIds": [projects[i]["id"] for i in indices],
        **{
            key: sum(projects[i][key] for i in indices)
            for key in ("costUsd", "staffDays", "reviewMinutes", "bountyTokens")
        },
        **{key: sum(rows[i][key] for i in indices) for key in ("expectedNpvUsd", "downsideNpvUsd", "stressedCostUsd")},
    }


def _fits(value: dict[str, Any], source: dict[str, Any]) -> bool:
    policy = source["policy"]
    chosen = set(value["projectIds"])
    selected = [p for p in source["projects"] if p["id"] in chosen]
    return (
        len(chosen) <= policy["maxProjects"]
        and value["stressedCostUsd"] <= policy["budgetUsd"]
        and value["staffDays"] <= policy["staffDays"]
        and value["reviewMinutes"] <= policy["reviewMinutes"]
        and value["bountyTokens"] <= policy["jobBudgetTokens"]
        and value["downsideNpvUsd"] >= policy["minDownsideNpvUsd"]
        and all(
            p["evidenceBps"] >= policy["minEvidenceBps"]
            and set(p["requires"]) <= chosen
            and not set(p["excludes"]) & chosen
            for p in selected
        )
        and all(sum(p["sector"] == sector for p in selected) <= policy["maxPerSector"] for sector in SECTORS)
    )


def _rank(value: dict[str, Any]) -> tuple[Any, ...]:
    return (
        -value["expectedNpvUsd"],
        -value["downsideNpvUsd"],
        value["stressedCostUsd"],
        value["staffDays"],
        value["reviewMinutes"],
        value["bountyTokens"],
        tuple(value["projectIds"]),
    )


def solve(source: Any) -> dict[str, Any]:
    """Find an exact feasible portfolio and bind all outputs to its normalized input."""
    source = validate(source)
    projects, policy = source["projects"], source["policy"]
    rows = [
        {"id": p["id"], **economics(p, policy), "evidenceEligible": p["evidenceBps"] >= policy["minEvidenceBps"]}
        for p in projects
    ]
    best: list[dict[str, Any]] = []
    feasible = 0
    for mask in range(1 << len(projects)):
        if mask.bit_count() > policy["maxProjects"]:
            continue
        indices = [i for i in range(len(projects)) if mask & (1 << i)]
        candidate = _portfolio(indices, projects, rows)
        if _fits(candidate, source):
            feasible += 1
            best.append(candidate)
            best.sort(key=_rank)
            del best[3:]
    selected = best[0] if best else None
    project_index = {p["id"]: i for i, p in enumerate(projects)}
    greedy_indices: set[int] = set()

    def closure(index: int) -> set[int]:
        result = {index}
        for pid in projects[index]["requires"]:
            result |= closure(project_index[pid])
        return result

    greedy = _portfolio([], projects, rows)
    for index in sorted(range(len(projects)), key=lambda i: (-rows[i]["expectedNpvUsd"], projects[i]["id"])):
        proposed = greedy_indices | closure(index)
        candidate = _portfolio(sorted(proposed), projects, rows)
        if _fits(candidate, source) and candidate["expectedNpvUsd"] > greedy["expectedNpvUsd"]:
            greedy, greedy_indices = candidate, proposed
    baseline = greedy if _fits(greedy, source) else None
    chosen = [p for p in projects if selected and p["id"] in selected["projectIds"]]
    jobs = [
        {
            "goal": f"Validate the business case and implementation plan for {p['id']}: {p['name']}",
            "successMetric": p["metric"],
            "bounty": str(p["bountyTokens"] * 10**18),
            "duration": p["durationDays"] * 86400,
            "priceWeight": 5000,
        }
        for p in chosen
    ]
    sensitivity = []
    for label, haircut, overrun in (
        ("Policy downside", policy["benefitHaircutBps"], policy["costOverrunBps"]),
        ("Benefits -50%, negative cash flows +50%, costs +25%", 5000, 2500),
        ("Benefits -75%, negative cash flows +75%, costs +50%", 7500, 5000),
    ):
        stress = {**policy, "benefitHaircutBps": haircut, "costOverrunBps": overrun}
        values = [economics(p, stress) for p in chosen]
        sensitivity.append(
            {
                "scenario": label,
                "benefitHaircutBps": haircut,
                "costOverrunBps": overrun,
                "npvUsd": sum(v["downsideNpvUsd"] for v in values),
                "capitalUsd": sum(v["stressedCostUsd"] for v in values),
                "budgetFits": bool(selected) and sum(v["stressedCostUsd"] for v in values) <= policy["budgetUsd"],
            }
        )
    roles = [
        {
            "role": role,
            "scope": "Deterministic sector analysis",
            "projectIds": [p["id"] for p in projects if p["sector"] == sector],
        }
        for role, sector in zip(
            (
                "Finance",
                "Biotech",
                "Materials",
                "Policy",
                "Energy",
                "Manufacturing",
                "Logistics",
                "Research",
                "Quantum",
            ),
            SECTORS,
        )
    ]
    roles.extend(
        [
            {
                "role": "Safety",
                "scope": "Input, resource, evidence and downside constraints; independent review still required",
                "projectIds": [p["id"] for p in chosen],
            },
            {
                "role": "Godel",
                "scope": "Exact recomputation and greedy comparison; no formal proof or autonomous model update",
                "projectIds": [p["id"] for p in chosen],
            },
        ]
    )
    result = {
        "status": (
            "NO_FEASIBLE_PORTFOLIO" if selected is None else "REVIEW_REQUIRED" if chosen else "HOLD_NO_POSITIVE_VALUE"
        ),
        "portfolio": selected,
        "alternatives": best[1:],
        "analysis": rows,
        "search": {
            "method": "Exhaustive subsets; maximum expected NPV under all declared constraints",
            "subsets": 1 << len(projects),
            "feasible": feasible,
        },
        "comparison": {
            "method": "Greedy standalone expected NPV with dependency closure",
            "portfolio": baseline,
            "upliftUsd": selected["expectedNpvUsd"] - baseline["expectedNpvUsd"] if selected and baseline else None,
        },
        "sensitivity": sensitivity,
        "roles": roles,
        "jobs": jobs,
        "settlementPreview": [
            {
                "projectId": p["id"],
                "grossBaseUnits": job["bounty"],
                "burnBaseUnits": str(int(job["bounty"]) // 100),
                "netBaseUnits": str(int(job["bounty"]) - int(job["bounty"]) // 100),
            }
            for p, job in zip(chosen, jobs)
        ],
        "approval": "UNREVIEWED",
        "scope": SCOPE,
    }
    body = {"schema": REPORT_SCHEMA, "input": source, "result": result}
    return {**body, "sha256": digest(body)}


def verify(report: Any) -> dict[str, Any]:
    """Recompute every field rather than trusting a hash supplied by its author."""
    _keys(report, {"schema", "input", "result", "sha256"}, "Dossier")
    rebuilt = solve(report["input"])
    if canonical(report) != canonical(rebuilt):
        raise ValueError("Dossier differs from recomputed input, decisions, jobs or commitment")
    return rebuilt


def brief(report: dict[str, Any]) -> str:
    """Render a plain-language decision brief with units and review boundaries."""
    source, result = report["input"], report["result"]
    selected = result["portfolio"]
    lines = [
        f"# {source['title']}",
        "",
        f"Status: {result['status']}",
        f"Evidence: {source['provenance']['kind']} — {source['provenance']['note']}",
        "",
    ]
    if selected:
        lines += [
            "Selected projects: " + (", ".join(selected["projectIds"]) or "none"),
            f"Three-year expected NPV: USD {selected['expectedNpvUsd']:,}",
            f"Policy-downside NPV: USD {selected['downsideNpvUsd']:,}",
            f"Capital including contingency: USD {selected['stressedCostUsd']:,} / {source['policy']['budgetUsd']:,}",
            f"Staff days: {selected['staffDays']} / {source['policy']['staffDays']}",
            f"Review minutes: {selected['reviewMinutes']} / {source['policy']['reviewMinutes']}",
            f"Unsubmitted job bounties: {selected['bountyTokens']:,} AGIALPHA / {source['policy']['jobBudgetTokens']:,}",
        ]
    else:
        lines += [
            "No subset meets all declared constraints. Change the inputs or reserve more resources before proceeding."
        ]
    lines += [
        "",
        "## Before implementation",
        "",
        "Independently verify the cited inputs and job success metrics. Review adverse scenarios. No project is funded or approved by this calculation.",
        "",
        "## Method",
        "",
        "Year-end cash flows over three years, no terminal value. Each discounted cash flow is floored to whole USD; adverse capital is rounded up. Negative cash flows worsen under the haircut. The optimizer reserves stressed capital, staff time, reviewer time and a separate AGIALPHA job budget.",
        "",
        result["scope"],
        "",
        f"Dossier SHA-256: {report['sha256']}",
        "",
    ]
    return "\n".join(lines)


def artifacts(report: dict[str, Any]) -> dict[str, bytes]:
    """Build a portable dossier and exact job specs accepted by ascension-compile."""
    verify(report)
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "project_id",
            "cost_usd",
            "stressed_cost_usd",
            "expected_npv_usd",
            "downside_npv_usd",
            "staff_days",
            "review_minutes",
            "bounty_agialpha",
        ]
    )
    selected = report["result"]["portfolio"]
    chosen = set(selected["projectIds"]) if selected else set()
    rows = {r["id"]: r for r in report["result"]["analysis"]}
    for p in report["input"]["projects"]:
        if p["id"] in chosen:
            r = rows[p["id"]]
            writer.writerow(
                [
                    p["id"],
                    p["costUsd"],
                    r["stressedCostUsd"],
                    r["expectedNpvUsd"],
                    r["downsideNpvUsd"],
                    p["staffDays"],
                    p["reviewMinutes"],
                    p["bountyTokens"],
                ]
            )
    seed = {
        "schema": "agialpha.business3.seed-draft.v1",
        "status": "UNMINTED_UNENCRYPTED",
        "dossierSha256": report["sha256"],
        "jobsSha256": digest(report["result"]["jobs"]),
        "note": "A content commitment for review, not an ERC-721 or encrypted secret. Compile jobs with alpha-agent ascension-compile; review the local-EVM protocol before deployment.",
    }
    values = {
        "scenario.json": canonical(report["input"]) + b"\n",
        "dossier.json": canonical(report) + b"\n",
        "jobs.json": canonical(report["result"]["jobs"]) + b"\n",
        "seed-draft.json": canonical(seed) + b"\n",
        "decision-brief.md": brief(report).encode("utf-8"),
        "selected-projects.csv": output.getvalue().encode("utf-8"),
    }
    values["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(values.items())
    ).encode()
    return values


def write_bundle(report: dict[str, Any], root: Path) -> Path:
    """Use a content-addressed directory; never overwrite existing or partial work."""
    values = artifacts(report)
    root.mkdir(parents=True, exist_ok=True)
    target: Path = root / report["sha256"]
    try:
        target.mkdir()
    except FileExistsError:
        if target.is_symlink() or not target.is_dir() or {p.name for p in target.iterdir()} != set(values):
            raise ValueError(
                "Existing run is incomplete or altered. Preserve it and choose a different output directory."
            ) from None
        if any((target / name).is_symlink() or (target / name).read_bytes() != data for name, data in values.items()):
            raise ValueError(
                "Existing run differs from the verified dossier. Choose a different output directory."
            ) from None
        return target
    for name, data in values.items():
        with (target / name).open("xb") as handle:
            handle.write(data)
    return target
