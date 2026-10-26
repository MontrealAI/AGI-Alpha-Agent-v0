# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/product"))
from contrib.upgrade_decision import core


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def scope_nodes(raw: dict[str, Any]) -> list[ast.AST]:
    source = raw["sources"][raw["consumer"]["source"]]
    tree = core.parse(source["text"])
    result = []
    for name in raw["consumer"]["scopeSymbols"]:
        current: ast.AST = tree
        for part in name.split("."):
            matches = [
                n
                for n in getattr(current, "body", [])
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == part
            ]
            if len(matches) != 1:
                raise ValueError("scope symbol must identify one captured definition")
            current = matches[0]
        result.append(current)
    return result


def scoped_calls(raw: dict[str, Any]) -> dict[tuple[int, int, str], ast.Call]:
    return {
        (n.lineno, n.col_offset, ast.unparse(n.func)): n
        for scope in scope_nodes(raw)
        for n in ast.walk(scope)
        if isinstance(n, ast.Call)
    }


def validate_raw(raw: dict[str, Any]) -> None:
    if raw.get("schema") != "alpha-transfer-raw-task/v1":
        raise ValueError("unsupported raw task schema")
    if not isinstance(raw.get("sources"), dict) or not 2 <= len(raw["sources"]) <= 24:
        raise ValueError("bounded captured public sources required")
    if not isinstance(raw.get("dependency", {}).get("importRoots"), list):
        raise TypeError("dependency roots required")
    for source in raw["sources"].values():
        if core.sha(source["text"].encode()) != source["sha256"]:
            raise ValueError("raw source identity mismatch")
        core.parse(source["text"])
    for side in ("before", "after"):
        if not raw["providerSides"][side] or any(k not in raw["sources"] for k in raw["providerSides"][side]):
            raise ValueError("captured provider source IDs required")
    scope_nodes(raw)


def compile_extraction(
    raw: dict[str, Any], extraction: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    validate_raw(raw)
    if extraction.get("schema") != "alpha-transfer-extraction/v1" or extraction.get("inputSha256") != digest(raw):
        raise ValueError("extraction is not bound to this exact raw input")
    claims, unresolved = extraction.get("claims"), extraction.get("unresolved")
    if not isinstance(claims, list) or not isinstance(unresolved, list) or not 1 <= len(claims) + len(unresolved) <= 24:
        raise ValueError("select 1–24 relevant calls or explicit unresolved calls")
    all_calls, seen, calls = scoped_calls(raw), set(), []
    for index, entry in enumerate([*claims, *unresolved]):
        location = (entry["line"], entry["column"], entry["callee"])
        if type(entry["line"]) is not int or type(entry["column"]) is not int or location in seen:
            raise ValueError("duplicate or invalid source call location")
        seen.add(location)
        node = all_calls.get(location)
        if node is None or ast.unparse(node.func) != entry["callee"]:
            raise ValueError("model-selected call is not present within the captured scope")
        if index >= len(claims):
            if not isinstance(entry.get("reason"), str) or not 1 <= len(entry["reason"]) <= 2000:
                raise ValueError("unresolved call needs an explicit evidence gap")
            continue
        for side in ("before", "after"):
            target = entry[side]
            if target["source"] not in raw["providerSides"][side]:
                raise ValueError("target is outside the frozen provider side")
            if not isinstance(target["symbol"], str) or not core.SYMBOL.fullmatch(target["symbol"]):
                raise ValueError("invalid captured declaration selector")
            body = core.parse(raw["sources"][target["source"]]["text"]).body
            selected: ast.AST | None = None
            for part in target["symbol"].split("."):
                matches = [
                    n
                    for n in body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == part
                ]
                if len(matches) != 1:
                    raise ValueError("selected declaration is absent or ambiguous")
                selected = matches[0]
                body = getattr(selected, "body", [])
            if not isinstance(selected, (ast.FunctionDef, ast.AsyncFunctionDef)):
                raise TypeError("select an explicit captured function or initializer")
        explanation = entry.get("explanation", "")
        if not isinstance(explanation, str) or len(explanation) > 1500:
            raise ValueError("bounded source mapping explanation required")
        calls.append(
            {
                "id": f'call-{entry["line"]}-{entry["column"]}',
                "consumer": raw["consumer"]["source"],
                "line": entry["line"],
                "column": entry["column"],
                "callee": entry["callee"],
                "before": entry["before"],
                "after": entry["after"],
                "mapping": {"kind": "direct-import", "explanation": explanation},
            }
        )
    if not calls:
        return None, unresolved
    pack = {
        "schema": core.SCHEMA,
        "id": raw["id"],
        "title": raw["title"],
        "purpose": raw["purpose"],
        "sources": raw["sources"],
        "calls": calls,
        "historicalEvidence": [],
        "recordedChecks": [],
    }
    trees = core.validate(pack)
    for item in pack["calls"]:
        if not core.direct_mapping(pack, trees, item, core.select_call(trees[item["consumer"]], item)):
            item["mapping"]["kind"] = "declared-target"
    return pack, unresolved


def assess_extraction(raw: dict[str, Any], extraction: dict[str, Any]) -> dict[str, Any]:
    pack, unresolved = compile_extraction(raw, extraction)
    record = core.assess(pack) if pack else None
    action = record["nextAction"] if record else "REVIEW_UNRESOLVED_SCOPE"
    if unresolved and action != "HOLD_UPDATE_AND_TEST":
        action = "REVIEW_UNRESOLVED_SCOPE"
    return {
        "schema": "alpha-transfer-intake-result/v1",
        "inputSha256": digest(raw),
        "extractionSha256": digest(extraction),
        "request": pack,
        "coreRecord": record,
        "unresolvedIntake": unresolved,
        "nextAction": action,
        "scope": raw["consumer"],
        "completeScopeAccepted": None,
        "scopeAcceptance": "Independent fresh-scope audit required; selected-call verification does not establish completeness.",
        "productionApproved": False,
        "actualCollectionsUsd": 0,
        "limits": [
            "Inert argument binding and explicit source gaps, not behavior, security or deployment approval.",
            "Model proposed targets are hypotheses; declared targets retain unproved-dispatch qualifications.",
            "Historical public source work packages are not observed customer orders.",
            "Complete model, authoring, customer-effort and upkeep costs remain unknown.",
        ],
    }
