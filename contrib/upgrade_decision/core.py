# SPDX-License-Identifier: Apache-2.0
"""Source-grounded call contracts; inspected source is never executed."""

from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
import re
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

SCHEMA = "alpha-upgrade-call-request/v1"
CAPABILITY = "source-linked-call-contract/v1"
MAX_PACK_BYTES = 750_000
STAGES = ("preparation", "planning", "execution", "verification", "correction", "packaging", "reporting", "recovery")
IDENT = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
SYMBOL = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\Z", re.ASCII)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def mission_key(pack: dict[str, Any]) -> str:
    if pack.get("schema") == "alpha-component-delivery-input/v1":
        files = pack["files"]
        decision = load(files["decision.json"]["text"].encode())
        contract = load(files["evidence/component-contract.json"]["text"].encode())
        profiles = load(files["evidence/component-projections.json"]["text"].encode())
        profile = next(p for p in profiles["profiles"] if p["id"] == "native-fastapi-bridge-v2")
        environments = [
            load(files[name]["text"].encode())
            for name in ("evidence/baseline-bridge-environment.json", "evidence/target-environment.json")
        ]
        identity = {
            "offering": "native-component-review/v1",
            "consumer": sorted((s["upstream_path"], s["sha256"]) for s in contract["sources"]),
            "requirements": contract["cases"],
            "projectionImports": profile["imports_ast_sha256"],
            "before": decision["before_versions"],
            "after": decision["after_versions"],
            "environments": [
                {
                    "python": env["python"],
                    "wheels": sorted((w["name"], w["version"], w["sha256"]) for w in env["wheels"]),
                }
                for env in environments
            ],
        }
    else:
        calls = []
        for call in pack["calls"]:
            calls.append(
                {
                    "consumer": {k: pack["sources"][call["consumer"]][k] for k in ("repository", "path", "sha256")},
                    "line": call["line"],
                    "column": call["column"],
                    "callee": call["callee"],
                    "before": {
                        "source": {
                            k: pack["sources"][call["before"]["source"]][k] for k in ("repository", "path", "sha256")
                        },
                        "symbol": call["before"]["symbol"],
                    },
                    "after": {
                        "source": {
                            k: pack["sources"][call["after"]["source"]][k] for k in ("repository", "path", "sha256")
                        },
                        "symbol": call["after"]["symbol"],
                    },
                }
            )
        identity = {"offering": "selected-call-contract/v1", "calls": sorted(calls, key=canonical)}
    return sha(canonical(identity))


def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def load(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_PACK_BYTES:
        raise ValueError("public source pack exceeds its byte bound")
    value = json.loads(
        raw, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON"))
    )
    if not isinstance(value, dict):
        raise TypeError("object source pack required")
    return value


def exact(value: Any, keys: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("missing or unsupported fields")


class Meter:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        wall, cpu = time.perf_counter_ns(), time.process_time_ns()
        status = "completed"
        try:
            yield
        except BaseException:
            status = "failed"
            raise
        finally:
            self.rows.append(
                {
                    "stage": name,
                    "status": status,
                    "wallNs": time.perf_counter_ns() - wall,
                    "cpuNs": time.process_time_ns() - cpu,
                    "basis": "measured",
                }
            )


def parse(text: str) -> ast.Module:
    if len(text.encode()) > 250_000 or "\x00" in text:
        raise ValueError("source exceeds its inert parse bound")
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise ValueError("unparseable Python source") from exc
    if sum(1 for _ in ast.walk(tree)) > 35_000:
        raise ValueError("source exceeds its AST bound")
    return tree


def validate(pack: dict[str, Any]) -> dict[str, ast.Module]:
    exact(pack, {"schema", "id", "title", "purpose", "sources", "calls", "historicalEvidence", "recordedChecks"})
    if pack["schema"] != SCHEMA or not isinstance(pack["id"], str) or not IDENT.fullmatch(pack["id"]):
        raise ValueError("unsupported request identity")
    for name in ("title", "purpose"):
        if not isinstance(pack[name], str) or not 1 <= len(pack[name]) <= 1000 or any(ord(c) < 32 for c in pack[name]):
            raise ValueError("invalid offering description")
    if not isinstance(pack["sources"], dict) or not 2 <= len(pack["sources"]) <= 24:
        raise ValueError("supply 2–24 captured public sources")
    trees = {}
    total = 0
    for ident, source in pack["sources"].items():
        if not isinstance(ident, str) or not IDENT.fullmatch(ident):
            raise ValueError("invalid source identity")
        exact(source, {"repository", "commit", "path", "sha256", "text"})
        repo, commit, path, text = (source[n] for n in ("repository", "commit", "path", "text"))
        if not isinstance(repo, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("only captured public GitHub source is supported")
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("exact source commit required")
        if (
            not isinstance(path, str)
            or not re.fullmatch(r"[A-Za-z0-9_./-]+\.py", path)
            or any(p in {"", ".", ".."} for p in path.split("/"))
        ):
            raise ValueError("ordinary relative Python source path required")
        if not isinstance(text, str) or sha(text.encode()) != source["sha256"]:
            raise ValueError("source digest does not match captured bytes")
        total += len(text.encode())
        if total > 650_000:
            raise ValueError("combined source limit exceeded")
        trees[ident] = parse(text)
    calls = pack["calls"]
    if not isinstance(calls, list) or not 1 <= len(calls) <= 24:
        raise ValueError("select 1–24 exact calls")
    seen = set()
    for call in calls:
        exact(call, {"id", "consumer", "line", "column", "callee", "before", "after", "mapping"})
        if not isinstance(call["id"], str) or not IDENT.fullmatch(call["id"]) or call["id"] in seen:
            raise ValueError("duplicate or invalid call identity")
        seen.add(call["id"])
        if not isinstance(call["callee"], str) or not 1 <= len(call["callee"]) <= 300:
            raise ValueError("exact captured callee expression required")
        if (
            call["consumer"] not in trees
            or type(call["line"]) is not int
            or not 1 <= call["line"] <= 100_000
            or type(call["column"]) is not int
            or not 0 <= call["column"] <= 10_000
        ):
            raise ValueError("invalid captured consumer location")
        for side in ("before", "after"):
            target = call[side]
            exact(target, {"source", "symbol"})
            if (
                target["source"] not in trees
                or not isinstance(target["symbol"], str)
                or not SYMBOL.fullmatch(target["symbol"])
            ):
                raise ValueError("unsupported declaration selector")
        exact(call["mapping"], {"kind", "explanation"})
        if (
            call["mapping"]["kind"] not in {"direct-import", "declared-target"}
            or not isinstance(call["mapping"]["explanation"], str)
            or len(call["mapping"]["explanation"]) > 1500
        ):
            raise ValueError("unsupported source relationship")
    evidence = pack["historicalEvidence"]
    if not isinstance(evidence, list) or len(evidence) > 8:
        raise ValueError("bounded historical references required")
    for row in evidence:
        exact(row, {"url", "statement"})
        if (
            not isinstance(row["url"], str)
            or not re.fullmatch(r"https://(?:github\.com|www\.starlette\.io)/[^\s<>\"]{1,800}", row["url"])
            or not isinstance(row["statement"], str)
            or len(row["statement"]) > 1500
        ):
            raise ValueError("unsupported historical reference")
    if not isinstance(pack["recordedChecks"], list) or len(pack["recordedChecks"]) > 4:
        raise ValueError("bounded recorded-check list required")
    for check in pack["recordedChecks"]:
        exact(check, {"id", "method", "reference", "sourceHashes", "result"})
        if not isinstance(check["id"], str) or not IDENT.fullmatch(check["id"]):
            raise ValueError("invalid recorded-check identity")
        if any(not isinstance(check[k], str) or not 1 <= len(check[k]) <= 2000 for k in ("method", "reference")):
            raise ValueError("recorded check needs method and provenance")
        if (
            check["sourceHashes"] != {ident: s["sha256"] for ident, s in pack["sources"].items()}
            or len(canonical(check["result"])) > 40000
        ):
            raise ValueError("recorded check is not bound to these exact sources")
    return trees


def citation(pack: dict[str, Any], ident: str, start: int, end: int) -> dict[str, Any]:
    source = pack["sources"][ident]
    return {
        "sourceId": ident,
        "sha256": source["sha256"],
        "line": start,
        "endLine": end,
        "url": f"https://github.com/{source['repository']}/blob/{source['commit']}/{source['path']}#L{start}-L{end}",
    }


def select_call(tree: ast.Module, item: dict[str, Any]) -> ast.Call:
    found = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and n.lineno == item["line"]
        and n.col_offset == item["column"]
        and ast.unparse(n.func) == item["callee"]
    ]
    if len(found) != 1:
        raise ValueError("selected consumer call is absent or ambiguous")
    return found[0]


def declaration(tree: ast.Module, symbol: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    parts = symbol.split(".")
    body = tree.body
    selected: Any = None
    for index, part in enumerate(parts):
        nodes = [
            n for n in body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == part
        ]
        if len(nodes) != 1:
            raise ValueError("declaration is not one direct definition")
        selected = nodes[0]
        if selected.decorator_list:
            raise ValueError("decorated declarations require runtime verification")
        if index < len(parts) - 1:
            if not isinstance(selected, ast.ClassDef) or selected.keywords or len(selected.bases) > 1:
                raise ValueError("unsupported class or declaration nesting")
            body = selected.body
    if not isinstance(selected, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise TypeError("select the direct function or explicit __init__ declaration")
    if len(selected.args.posonlyargs) + len(selected.args.args) + len(selected.args.kwonlyargs) > 64:
        raise ValueError("parameter limit exceeded")
    return selected


def call_shape(call: ast.Call, *, bound_receiver: bool = False) -> dict[str, Any]:
    if any(isinstance(arg, ast.Starred) for arg in call.args) or any(kw.arg is None for kw in call.keywords):
        raise ValueError("expanded arguments require runtime verification")
    names = [kw.arg for kw in call.keywords]
    if len(names) != len(set(names)):
        raise ValueError("duplicate call keyword")
    return {
        "positionalCount": len(call.args) + int(bound_receiver),
        "keywordNames": sorted(names),
        "implicitReceiver": int(bound_receiver),
    }


def selected_shape(call: ast.Call, item: dict[str, Any]) -> dict[str, Any]:
    """Keep unsupported constructor/descriptor dispatch unresolved."""
    symbols = [item[side]["symbol"] for side in ("before", "after")]
    if any("." in symbol for symbol in symbols):
        # The captured historical path is an explicitly bound super initializer.
        # Class calls, unbound initializers and other descriptors need a separate
        # dispatch proof; two binders sharing a guessed receiver cannot supply it.
        if not (
            all(symbol.endswith(".__init__") for symbol in symbols)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "__init__"
            and isinstance(call.func.value, ast.Call)
            and isinstance(call.func.value.func, ast.Name)
            and call.func.value.func.id == "super"
            and not call.func.value.args
            and not call.func.value.keywords
        ):
            raise ValueError("constructor or descriptor receiver dispatch requires runtime verification")
        return call_shape(call, bound_receiver=True)
    return call_shape(call)


def metadata(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    args = node.args
    parameters = []
    positional = [*args.posonlyargs, *args.args]
    required = len(positional) - len(args.defaults)
    for index, param in enumerate(positional):
        parameters.append(
            {
                "name": param.arg,
                "kind": "POSITIONAL_ONLY" if index < len(args.posonlyargs) else "POSITIONAL_OR_KEYWORD",
                "required": index < required,
            }
        )
    if args.vararg:
        parameters.append({"name": args.vararg.arg, "kind": "VAR_POSITIONAL", "required": False})
    for param, default in zip(args.kwonlyargs, args.kw_defaults):
        parameters.append({"name": param.arg, "kind": "KEYWORD_ONLY", "required": default is None})
    if args.kwarg:
        parameters.append({"name": args.kwarg.arg, "kind": "VAR_KEYWORD", "required": False})
    return {"parameters": parameters}


def constraint_accepts(sig: dict[str, Any], shape: dict[str, Any]) -> bool:
    params = sig["parameters"]
    positional = [p for p in params if p["kind"] in {"POSITIONAL_ONLY", "POSITIONAL_OR_KEYWORD"}]
    count, names = shape["positionalCount"], set(shape["keywordNames"])
    if count > len(positional) and not any(p["kind"] == "VAR_POSITIONAL" for p in params):
        return False
    filled = {p["name"] for p in positional[:count] if p["kind"] == "POSITIONAL_OR_KEYWORD"}
    if filled & names:
        return False
    allowed = {p["name"] for p in params if p["kind"] in {"POSITIONAL_OR_KEYWORD", "KEYWORD_ONLY"}}
    if names - allowed and not any(p["kind"] == "VAR_KEYWORD" for p in params):
        return False
    for index, param in enumerate(positional):
        if param["required"] and index >= count and (param["kind"] == "POSITIONAL_ONLY" or param["name"] not in names):
            return False
    return all(not p["required"] or p["name"] in names for p in params if p["kind"] == "KEYWORD_ONLY")


def signature_accepts(node: ast.FunctionDef | ast.AsyncFunctionDef, shape: dict[str, Any]) -> bool:
    args = node.args
    params: list[inspect.Parameter] = []
    positional = [*args.posonlyargs, *args.args]
    required = len(positional) - len(args.defaults)
    for index, arg in enumerate(positional):
        kind = (
            inspect.Parameter.POSITIONAL_ONLY
            if index < len(args.posonlyargs)
            else inspect.Parameter.POSITIONAL_OR_KEYWORD
        )
        params.append(inspect.Parameter(arg.arg, kind, default=inspect.Parameter.empty if index < required else None))
    if args.vararg:
        params.append(inspect.Parameter(args.vararg.arg, inspect.Parameter.VAR_POSITIONAL))
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        params.append(
            inspect.Parameter(
                arg.arg, inspect.Parameter.KEYWORD_ONLY, default=inspect.Parameter.empty if default is None else None
            )
        )
    if args.kwarg:
        params.append(inspect.Parameter(args.kwarg.arg, inspect.Parameter.VAR_KEYWORD))
    try:
        inspect.Signature(params).bind(*([None] * shape["positionalCount"]), **dict.fromkeys(shape["keywordNames"]))
        return True
    except TypeError:
        return False


def direct_mapping(pack: dict[str, Any], trees: dict[str, ast.Module], item: dict[str, Any], call: ast.Call) -> bool:
    if item["mapping"]["kind"] != "direct-import":
        return False
    expression = ast.unparse(call.func)
    root = expression.split(".")[0]
    tree = trees[item["consumer"]]
    imports = []
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                if (alias.asname or alias.name.split(".")[0]) == root:
                    imports.append((alias.asname or alias.name.split(".")[0], alias.name))
        elif isinstance(statement, ast.ImportFrom) and statement.level == 0:
            for alias in statement.names:
                if (alias.asname or alias.name) == root:
                    imports.append((alias.asname or alias.name, (statement.module or "") + "." + alias.name))
    if len(imports) != 1:
        return False
    local, qualified = imports[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == root and isinstance(node.ctx, (ast.Store, ast.Del)):
            return False
        if isinstance(node, ast.arg) and node.arg == root:
            return False
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == root:
            return False
        if isinstance(node, (ast.Global, ast.Nonlocal)) and root in node.names:
            return False
        if isinstance(node, (ast.MatchAs, ast.MatchStar, ast.ExceptHandler)) and node.name == root:
            return False
        if isinstance(node, ast.MatchMapping) and node.rest == root:
            return False
        if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, (ast.Store, ast.Del)):
            value: Any = node.value
            while isinstance(value, (ast.Attribute, ast.Subscript)):
                value = value.value
            if isinstance(value, ast.Name) and value.id == root:
                return False
        if (
            isinstance(node, (ast.Import, ast.ImportFrom))
            and node not in tree.body
            and any((alias.asname or alias.name.split(".")[0]) == root for alias in node.names)
        ):
            return False
        if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
            return False
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"exec", "eval", "globals", "locals", "setattr", "delattr"}
        ):
            return False
    resolved = qualified + expression[len(local) :]
    for side in ("before", "after"):
        target = item[side]
        path = pack["sources"][target["source"]]["path"]
        module = path[:-3].replace("/", ".")
        module = module.removeprefix("src.")
        module = module.removesuffix(".__init__")
        symbol = target["symbol"]
        symbol = symbol.removesuffix(".__init__")
        if resolved != module + "." + symbol:
            return False
        target_tree = trees[target["source"]]
        target_root = symbol.split(".")[0]
        for node in ast.walk(target_tree):
            if isinstance(node, ast.Name) and node.id == target_root and isinstance(node.ctx, (ast.Store, ast.Del)):
                return False
            if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
                return False
            if isinstance(node, (ast.Import, ast.ImportFrom)) and any(
                (a.asname or a.name.split(".")[0]) == target_root for a in node.names
            ):
                return False
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"exec", "eval", "globals", "locals", "setattr", "delattr"}
            ):
                return False
    return True


def create(pack: dict[str, Any], trees: dict[str, ast.Module], *, conventional: bool = False) -> dict[str, Any]:
    rows = []
    for item in pack["calls"]:
        row: dict[str, Any] = {
            "id": item["id"],
            "status": "UNRESOLVED",
            "beforeAccepts": None,
            "afterAccepts": None,
            "mapping": item["mapping"],
            "evidence": [],
            "reason": None,
        }
        try:
            call = select_call(trees[item["consumer"]], item)
            shape = selected_shape(call, item)
            row["callShape"] = shape
            row["snippet"] = ast.get_source_segment(pack["sources"][item["consumer"]]["text"], call)
            row["evidence"].append(citation(pack, item["consumer"], call.lineno, call.end_lineno or call.lineno))
            for side in ("before", "after"):
                target = item[side]
                fn = declaration(trees[target["source"]], target["symbol"])
                row[side + "Signature"] = metadata(fn)
                row[side + "Accepts"] = (
                    signature_accepts(fn, shape) if conventional else constraint_accepts(metadata(fn), shape)
                )
                row["evidence"].append(citation(pack, target["source"], fn.lineno, fn.end_lineno or fn.lineno))
            row["mappingVerified"] = direct_mapping(pack, trees, item, call)
            row["status"] = (
                "BINDING_CONFLICT"
                if row["beforeAccepts"] is True and row["afterAccepts"] is False
                else (
                    "BINDING_PRESERVED"
                    if row["beforeAccepts"] is True and row["afterAccepts"] is True
                    else "UNRESOLVED"
                )
            )
            if not row["mappingVerified"]:
                row["qualification"] = (
                    "Conditional on the declared target; runtime dispatch/import identity is unproved."
                )
            else:
                row["qualification"] = (
                    "Direct captured import under standard imports, successful argument evaluation and no runtime monkeypatching."
                )
        except (ValueError, TypeError, RecursionError) as exc:
            row["reason"] = str(exc)
        rows.append(row)
    return {
        "schema": "alpha-upgrade-decision/v1",
        "capability": CAPABILITY,
        "id": pack["id"],
        "title": pack["title"],
        "purpose": pack["purpose"],
        "inputSha256": sha(canonical(pack)),
        "calls": rows,
        "sourceInventory": [
            {"id": ident, **{k: v for k, v in row.items() if k != "text"}}
            for ident, row in sorted(pack["sources"].items())
        ],
        "historicalEvidence": pack["historicalEvidence"],
        "recordedChecks": pack["recordedChecks"],
        "customerAcceptance": "unknown",
        "productionApproved": False,
        "limits": [
            "Selected calls and inert argument binding only; not full application, dependency security or release approval.",
            "A declared target is a conditional source relationship, not proof of runtime dispatch.",
            "An accepted binding does not establish behavior, values, types, imports or successful argument evaluation.",
            "Unselected calls and runtime monkeypatching remain unassessed. Source origin is supplied by the public-input curator; hashes bind bytes, not authorship.",
        ],
    }


def critique(pack: dict[str, Any], record: dict[str, Any]) -> list[dict[str, Any]]:
    allegations = []
    actual = {row["id"] for row in record["calls"]}
    for item in pack["calls"]:
        if item["id"] not in actual:
            allegations.append({"call": item["id"], "kind": "missing-selected-call", "evidence": "request.calls"})
    for row in record["calls"]:
        if row["status"] != "UNRESOLVED" and not row.get("mappingVerified"):
            allegations.append({"call": row["id"], "kind": "dispatch-unproved", "evidence": row["evidence"][0]})
    return allegations


def verify(pack: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    trees = validate(pack)
    checks = []
    if record.get("inputSha256") != sha(canonical(pack)):
        checks.append({"call": None, "kind": "input-identity", "substantiated": True})
    if "missionKey" in record and record["missionKey"] != mission_key(pack):
        checks.append({"call": None, "kind": "underlying-mission-identity", "substantiated": True})
    expected_inventory = [
        {"id": ident, **{k: v for k, v in row.items() if k != "text"}} for ident, row in sorted(pack["sources"].items())
    ]
    if record.get("sourceInventory") != expected_inventory or any(
        record.get(k) != pack[k] for k in ("id", "title", "purpose", "historicalEvidence", "recordedChecks")
    ):
        checks.append({"call": None, "kind": "record-source-or-purpose", "substantiated": True})
    rows = {row["id"]: row for row in record["calls"]}
    if set(rows) != {c["id"] for c in pack["calls"]} or len(rows) != len(record["calls"]):
        checks.append({"call": None, "kind": "selected-call-coverage", "substantiated": True})
    for item in pack["calls"]:
        row = rows.get(item["id"])
        if row is None:
            continue
        try:
            call = select_call(trees[item["consumer"]], item)
            shape = selected_shape(call, item)
            expected = []
            for side in ("before", "after"):
                target = item[side]
                fn = declaration(trees[target["source"]], target["symbol"])
                if signature_accepts(fn, shape) != row[side + "Accepts"] or metadata(fn) != row[side + "Signature"]:
                    checks.append({"call": item["id"], "kind": side + "-binding-or-signature", "substantiated": True})
                expected.append(citation(pack, target["source"], fn.lineno, fn.end_lineno or fn.lineno))
            if (
                row.get("callShape") != shape
                or row.get("snippet") != ast.get_source_segment(pack["sources"][item["consumer"]]["text"], call)
                or row.get("evidence")
                != [citation(pack, item["consumer"], call.lineno, call.end_lineno or call.lineno), *expected]
            ):
                checks.append({"call": item["id"], "kind": "source-witness", "substantiated": True})
            expected_status = (
                "BINDING_CONFLICT"
                if row["beforeAccepts"] is True and row["afterAccepts"] is False
                else (
                    "BINDING_PRESERVED"
                    if row["beforeAccepts"] is True and row["afterAccepts"] is True
                    else "UNRESOLVED"
                )
            )
            if expected_status != row["status"] or row.get("mappingVerified") != direct_mapping(
                pack, trees, item, call
            ):
                checks.append({"call": item["id"], "kind": "classification-or-dispatch", "substantiated": True})
        except (ValueError, TypeError, RecursionError, KeyError) as exc:
            if row.get("status") != "UNRESOLVED" or row.get("reason") != str(exc):
                checks.append({"call": item["id"], "kind": "unsupported-call", "substantiated": True})
    if "nextAction" in record:
        conflict = any(row["status"] == "BINDING_CONFLICT" for row in record["calls"])
        unresolved = any(row["status"] == "UNRESOLVED" or not row.get("mappingVerified") for row in record["calls"])
        expected_action = (
            "HOLD_UPDATE_AND_TEST"
            if conflict
            else "REVIEW_UNRESOLVED_SCOPE" if unresolved else "RUN_BEHAVIOR_AND_SECURITY_CHECKS"
        )
        if record["nextAction"] != expected_action:
            checks.append({"call": None, "kind": "unsupported-next-action", "substantiated": True})
    return {
        "method": "Fresh source parse and Python inspect.Signature.bind, without executing inspected code; same author/process, not organizational independence.",
        "accepted": not checks,
        "defects": checks,
        "selectedCalls": len(pack["calls"]),
    }


def assess(pack: dict[str, Any], *, conventional: bool = False) -> dict[str, Any]:
    pack = load(canonical(pack))
    meter = Meter()
    with meter.stage("preparation"):
        trees = validate(pack)
    with meter.stage("planning"):
        plan = {
            "selectedCalls": len(pack["calls"]),
            "sourceFiles": len(pack["sources"]),
            "networkRequests": 0,
            "sourceExecution": False,
        }
    with meter.stage("execution"):
        record = create(pack, trees, conventional=conventional)
        record["boundedPlan"] = plan
        record["missionKey"] = mission_key(pack)
    with meter.stage("verification"):
        allegations = critique(pack, record)
        verification = verify(pack, record)
    with meter.stage("correction"):
        corrections = []
        if verification["defects"]:
            original = copy.deepcopy(record)
            record = create(pack, trees, conventional=True)
            corrections.append(
                {
                    "defects": verification["defects"],
                    "original": original,
                    "method": "Recompute with standard Signature.bind; no substantive input changed.",
                }
            )
            verification = verify(pack, record)
        for allegation in allegations:
            allegation["disposition"] = (
                "supported limitation retained; no runtime-break claim is made"
                if allegation["kind"] == "dispatch-unproved"
                else "checked against the complete selected-call set"
            )
    with meter.stage("reporting"):
        conflict = any(row["status"] == "BINDING_CONFLICT" for row in record["calls"])
        unresolved = any(row["status"] == "UNRESOLVED" or not row.get("mappingVerified") for row in record["calls"])
        record.update(
            nextAction=(
                "HOLD_UPDATE_AND_TEST"
                if conflict
                else "REVIEW_UNRESOLVED_SCOPE" if unresolved else "RUN_BEHAVIOR_AND_SECURITY_CHECKS"
            ),
            engineeringAcceptance=verification["accepted"],
            review={
                "creator": "Source-linked call-contract construction",
                "critic": allegations,
                "verifier": verification,
                "corrections": corrections,
            },
        )
        final_verification = verify(pack, record)
        record["engineeringAcceptance"] = final_verification["accepted"]
        record["review"]["finalVerification"] = final_verification
    record["resources"] = {
        "stages": meter.rows,
        "runtimeModelCalls": {"value": 0, "basis": "measured"},
        "networkRequests": {"value": 0, "basis": "measured"},
        "inputBytes": {"value": len(canonical(pack)), "basis": "measured"},
        "python": sys.version,
        "unknown": [
            "research and authoring inference/billing",
            "caller preparation, transport, journal, transmission and final packaging overhead",
            "setup/integration/upkeep",
            "customer effort and matched human duration",
            "currency costs and available surplus",
        ],
    }
    return record


def main() -> None:
    raw = sys.stdin.buffer.read(MAX_PACK_BYTES + 1)
    try:
        request = load(raw)
        result = assess(request)
        sys.stdout.buffer.write(canonical(result))
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        sys.stdout.buffer.write(
            canonical(
                {
                    "refused": True,
                    "reason": str(exc),
                    "inputSha256": sha(raw),
                    "cost": "unknown; failed attempt remains charged by the parent transport",
                }
            )
        )


if __name__ == "__main__":
    main()
