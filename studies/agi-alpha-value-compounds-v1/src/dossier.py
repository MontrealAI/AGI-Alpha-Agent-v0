# SPDX-License-Identifier: Apache-2.0
"""Static signature containment with inspectable call-shape counterexamples."""
from __future__ import annotations

import ast
import hashlib
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "call-compatibility-dossier/v1"
MAX_BYTES = 1_000_000
MAX_NODES = 100_000
MAX_PARAMETERS = 64


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def content_id(source: str) -> str:
    return hashlib.sha256(source.encode()).hexdigest()


def _bound_names(node: ast.AST) -> set[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {node.name}
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return {a.asname or a.name.split(".")[0] for a in node.names}
    if isinstance(node, ast.Lambda):
        return set()
    names = {node.id} if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)) else set()
    if isinstance(node, (ast.MatchAs, ast.MatchStar, ast.ExceptHandler)) and node.name:
        names.add(node.name)
    if isinstance(node, ast.MatchMapping) and node.rest:
        names.add(node.rest)
    for child in ast.iter_child_nodes(node):
        names.update(_bound_names(child))
    return names


def _active_dynamic(node: ast.AST) -> bool:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
        return False
    if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval", "globals", "locals"}:
        return True
    return any(_active_dynamic(child) for child in ast.iter_child_nodes(node))


def _module_dynamic(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
            return True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__getattr__":
            return True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if _active_dynamic(node):
            return True
    return False


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    a = node.args
    positional = list(a.posonlyargs) + list(a.args)
    default_start = len(positional) - len(a.defaults)
    parameters = []
    for i, arg in enumerate(positional):
        default = None if i < default_start else ast.unparse(a.defaults[i - default_start])
        parameters.append({"name": arg.arg, "kind": "posonly" if i < len(a.posonlyargs) else "poskw",
                           "required": i < default_start, "default": default})
    if a.vararg:
        parameters.append({"name": a.vararg.arg, "kind": "varpos", "required": False, "default": None})
    for arg, default in zip(a.kwonlyargs, a.kw_defaults):
        parameters.append({"name": arg.arg, "kind": "kwonly", "required": default is None,
                           "default": None if default is None else ast.unparse(default)})
    if a.kwarg:
        parameters.append({"name": a.kwarg.arg, "kind": "varkw", "required": False, "default": None})
    if len(parameters) > MAX_PARAMETERS:
        raise ValueError("PARAMETER_LIMIT")
    return {"parameters": parameters, "async": isinstance(node, ast.AsyncFunctionDef)}


def extract(source: str) -> dict[str, Any]:
    raw = source.encode()
    if len(raw) > MAX_BYTES or "\x00" in source:
        return {"status": "unresolved", "reason": "SOURCE_BOUND", "functions": {}, "source_sha256": content_id(source)}
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError) as exc:
        return {"status": "unresolved", "reason": type(exc).__name__, "functions": {}, "source_sha256": content_id(source)}
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        return {"status": "unresolved", "reason": "AST_NODE_LIMIT", "functions": {}, "source_sha256": content_id(source)}
    bindings = Counter(name for node in tree.body for name in _bound_names(node))
    direct = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")}
    conditional = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        conditional.update(n.name for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_"))
    dynamic = _module_dynamic(tree)
    functions = {}
    for name in sorted(direct):
        node = direct.get(name)
        reasons = []
        if dynamic:
            reasons.append("dynamic-module")
        if name in conditional:
            reasons.append("conditional-definition")
        if bindings[name] != 1:
            reasons.append("rebound-or-duplicate")
        if node is not None and node.decorator_list:
            reasons.append("decorated-definition")
        item = {"name": name, "line": getattr(node, "lineno", None), "end_line": getattr(node, "end_lineno", None),
                "status": "unresolved" if reasons else "supported", "reasons": reasons}
        if node is not None and not reasons:
            try:
                item["signature"] = _signature(node)
            except ValueError as exc:
                item.update(status="unresolved", reasons=[str(exc)])
        functions[name] = item
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef) and not n.name.startswith("_")]:
        constructors = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "__init__"]
        if not constructors:
            continue
        node = constructors[-1]
        if isinstance(node, ast.AsyncFunctionDef):
            continue
        reasons = []
        class_bindings = Counter(name for child in cls.body for name in _bound_names(child))
        if dynamic:
            reasons.append("dynamic-module")
        if bindings[cls.name] != 1 or class_bindings["__init__"] != 1:
            reasons.append("rebound-or-duplicate")
        if cls.decorator_list or node.decorator_list:
            reasons.append("decorated-definition")
        if cls.keywords or len(cls.bases) > 1:
            reasons.append("metaclass-or-multiple-bases")
        if any(_active_dynamic(child) for child in cls.body):
            reasons.append("dynamic-class")
        name = cls.name + ".__init__"
        item = {"name": name, "line": node.lineno, "end_line": node.end_lineno,
                "status": "unresolved" if reasons else "supported", "reasons": reasons,
                "kind": "constructor-unbound", "implicit_receiver": 1}
        if not reasons:
            try:
                item["signature"] = _signature(node)
            except ValueError as exc:
                item.update(status="unresolved", reasons=[str(exc)])
        functions[name] = item
    aliases = sorted({a.asname or a.name.split(".")[0] for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom)) for a in node.names})
    blocked = sorted({name for name in bindings if name not in direct or bindings[name] != 1} | conditional)
    return {"status": "parsed", "reason": None, "functions": functions, "bound_names": sorted(bindings),
            "blocked_names": blocked, "imported_names": aliases, "dynamic": dynamic, "source_sha256": hashlib.sha256(raw).hexdigest()}


def _constraints(sig: dict[str, Any], n: int, universe: set[str]) -> tuple[set[str], set[str]] | None:
    params = sig["parameters"]
    positional = [p for p in params if p["kind"] in {"posonly", "poskw"}]
    if n > len(positional) and not any(p["kind"] == "varpos" for p in params):
        return None
    if any(p["kind"] == "posonly" and p["required"] for p in positional[n:]):
        return None
    assigned = {p["name"] for p in positional[:n] if p["kind"] == "poskw"}
    keywordable = {p["name"] for p in positional[n:] if p["kind"] == "poskw"}
    keywordable.update(p["name"] for p in params if p["kind"] == "kwonly")
    required = {p["name"] for p in positional[n:] if p["kind"] == "poskw" and p["required"]}
    required.update(p["name"] for p in params if p["kind"] == "kwonly" and p["required"])
    allowed = (set(universe) if any(p["kind"] == "varkw" for p in params) else keywordable) - assigned
    if not required <= allowed:
        return None
    return required, allowed


def compare_signatures(before: dict[str, Any], after: dict[str, Any] | None) -> dict[str, Any]:
    names = {p["name"] for sig in [before, after] if sig for p in sig["parameters"]}
    sentinel = "agi_extra_keyword"
    while sentinel in names:
        sentinel += "_"
    universe = names | {sentinel}
    positional_max = max(sum(p["kind"] in {"posonly", "poskw"} for p in s["parameters"]) for s in [before, after] if s)
    inspected = 0
    for n in range(positional_max + 2):
        old = _constraints(before, n, universe)
        inspected += 1
        if old is None:
            continue
        needed, allowed = old
        new = _constraints(after, n, universe) if after is not None else None
        if new is None or not new[0] <= needed or not needed <= new[1]:
            return {"status": "call_loss", "witness": {"positional_count": n, "keyword_names": sorted(needed)},
                    "reason": "old-minimal-call-rejected", "constraint_cases": inspected}
        extras = sorted(allowed - new[1])
        if extras:
            return {"status": "call_loss", "witness": {"positional_count": n, "keyword_names": sorted(needed | {extras[0]})},
                    "reason": "old-permitted-keyword-rejected", "constraint_cases": inspected}
    return {"status": "no_call_loss", "witness": None, "reason": "complete-signature-constraint-containment",
            "constraint_cases": inspected}


def compare_facts(before: dict[str, Any], after: dict[str, Any], module: str) -> dict[str, Any]:
    functions = []
    module_unresolved = any(x["status"] != "parsed" or x.get("dynamic", False) for x in (before, after))
    for name in sorted(set(before["functions"]) | set(after["functions"])):
        old = before["functions"].get(name)
        new = after["functions"].get(name)
        row = {"name": name, "before_line": old.get("line") if old else None, "after_line": new.get("line") if new else None,
               "warnings": []}
        blocked = name in before.get("blocked_names", []) or name in after.get("blocked_names", [])
        inherited = name.endswith(".__init__") and any(name not in x["functions"] and name.split(".")[0] in x.get("bound_names", []) for x in (before, after))
        if module_unresolved or blocked or inherited:
            row.update(status="unresolved", witness=None, reason="module-or-binding-outside-supported-scope")
        elif old is None:
            row.update(status="added" if new["status"] == "supported" else "unresolved", witness=None,
                       reason="new-declaration" if new["status"] == "supported" else ",".join(new["reasons"]))
            if new["status"] == "supported":
                row["before_signature"] = None
                row["after_signature"] = new["signature"]
        elif old["status"] != "supported" or (new is not None and new["status"] != "supported"):
            row.update(status="unresolved", witness=None, reason=",".join((old.get("reasons", []) + (new.get("reasons", []) if new else []))))
        elif new is None and (name in after["bound_names"] or name.split(".")[0] in after["bound_names"] or after["dynamic"]):
            row.update(status="unresolved", witness=None, reason="new-binding-or-dynamic-export")
        else:
            row.update(compare_signatures(old["signature"], new["signature"] if new else None))
            row["before_signature"] = old["signature"]
            row["after_signature"] = new["signature"] if new else None
            if new is None:
                row["reason"] = "declaration-removed-no-resolved-replacement"
            else:
                if old["signature"]["async"] != new["signature"]["async"]:
                    row["warnings"].append("async-contract-changed-outside-binding-guarantee")
                a, b = old["signature"]["parameters"], new["signature"]["parameters"]
                if [(p["name"], p["default"]) for p in a] != [(p["name"], p["default"]) for p in b]:
                    row["warnings"].append("parameter-order-or-default-expression-changed-review-semantics")
        functions.append(row)
    counts = Counter(x["status"] for x in functions)
    return {"schema": SCHEMA, "module": module, "status": "partial" if module_unresolved or counts["unresolved"] else "complete", "functions": functions,
            "findings": [x for x in functions if x["status"] == "call_loss"],
            "coverage": {"before_direct": len(before["functions"]), "after_direct": len(after["functions"]),
                         "compared": counts["call_loss"] + counts["no_call_loss"], "call_loss": counts["call_loss"],
                         "unresolved": counts["unresolved"]},
            "source_ids": [before["source_sha256"], after["source_sha256"]],
            "source_hashes": {"before": before["source_sha256"], "after": after["source_sha256"]},
            "limits": ["Direct static declarations only; import aliases, methods, decorators and dynamic bindings are unresolved.",
                       "No-loss concerns argument binding only, not behavior, types, defaults, async contract or operational approval."]}


def compare_sources(before: str, after: str, module: str) -> dict[str, Any]:
    start, cpu = time.perf_counter_ns(), time.process_time_ns()
    result = compare_facts(extract(before), extract(after), module)
    result["meter"] = {"wall_ns": time.perf_counter_ns() - start, "cpu_ns": time.process_time_ns() - cpu,
                       "input_bytes": len(before.encode()) + len(after.encode()), "source_parses": 2,
                       "runtime_model_calls": 0, "network_requests": 0}
    return result


class SnapshotStore:
    """Reusable facts are content-addressed; persisted identities are checked on read."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.hits = self.misses = self.bytes_read = self.bytes_written = 0
        self.asset_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    def get(self, source: str) -> dict[str, Any]:
        identity = content_id(source)
        path = self.root / f"{identity}.json"
        if path.exists():
            raw = path.read_bytes()
            self.bytes_read += len(raw)
            entry = json.loads(raw)
            if entry.get("source_sha256") != identity or entry.get("asset_sha256") != self.asset_hash:
                raise ValueError("STALE_OR_WRONG_SNAPSHOT_IDENTITY")
            if entry.get("facts_sha256") != hashlib.sha256(canonical(entry.get("facts"))).hexdigest():
                raise ValueError("SNAPSHOT_INTEGRITY")
            self.hits += 1
            return entry["facts"]
        facts = extract(source)
        entry = {"source_sha256": identity, "asset_sha256": self.asset_hash, "facts": facts,
                 "facts_sha256": hashlib.sha256(canonical(facts)).hexdigest()}
        raw = canonical(entry)
        path.write_bytes(raw)
        self.misses += 1
        self.bytes_written += len(raw)
        return facts
