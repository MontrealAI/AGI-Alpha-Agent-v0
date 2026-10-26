# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
from collections import OrderedDict
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
import sys
from typing import Any

MAX_SOURCE_BYTES = 1_000_000
MAX_AST_NODES = 100_000
MAX_PARAMETERS = 64
MAX_PROBES = 100_000_000
CACHE_BYTE_LIMIT = 16_000_000
CACHE_ENTRY_LIMIT = 64
SCHEMA = "agialpha-call-shape-conventional/v1"
_DYNAMIC = {"exec", "eval", "globals", "locals"}
_CACHE: OrderedDict[tuple[str, ...], dict[str, Any]] = OrderedDict()


def clear_cache() -> None:
    _CACHE.clear()


def cache_info() -> dict[str, int]:
    return {"entries": len(_CACHE), "source_bytes": sum(row["source_bytes"] for row in _CACHE.values())}


def _targets(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [n for part in node.elts for n in _targets(part)]
    if isinstance(node, ast.Starred):
        return _targets(node.value)
    if isinstance(node, (ast.Attribute, ast.Subscript)):
        return _targets(node.value)
    return []


def _constructor_info(node: ast.ClassDef) -> tuple[ast.FunctionDef | None, list[str]]:
    direct: list[ast.FunctionDef] = []
    bindings: list[str] = []
    issues: list[str] = []
    if node.decorator_list:
        issues.append("decorated-class")
    if len(node.bases) > 1 or node.keywords:
        issues.append("multiple-bases-or-class-keywords")

    def visit(child: ast.AST, nested: bool = False) -> None:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if child.name == "__init__":
                bindings.append("conditional" if nested else "direct")
                if isinstance(child, ast.FunctionDef) and not nested:
                    direct.append(child)
                else:
                    issues.append("constructor-not-direct-synchronous-function")
            return
        if isinstance(child, ast.Lambda):
            return
        if isinstance(child, (ast.Import, ast.ImportFrom)):
            for alias in child.names:
                if alias.name == "*" or (alias.asname or alias.name.split(".")[0]) == "__init__":
                    bindings.append("import")
        if isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete, ast.NamedExpr)):
            targets = child.targets if isinstance(child, (ast.Assign, ast.Delete)) else [child.target]
            if any("__init__" in _targets(target) for target in targets):
                bindings.append("assignment-or-deletion")
        if isinstance(child, (ast.For, ast.AsyncFor)) and "__init__" in _targets(child.target):
            bindings.append("loop-binding")
        if isinstance(child, (ast.With, ast.AsyncWith)) and any(item.optional_vars is not None and "__init__" in _targets(item.optional_vars) for item in child.items):
            bindings.append("with-binding")
        if isinstance(child, ast.ExceptHandler) and child.name == "__init__":
            bindings.append("exception-binding")
        if isinstance(child, (ast.MatchAs, ast.MatchStar)) and child.name == "__init__":
            bindings.append("pattern-binding")
        if isinstance(child, ast.MatchMapping) and child.rest == "__init__":
            bindings.append("pattern-binding")
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id in _DYNAMIC:
            issues.append("dynamic-class-body")
        branch = nested or isinstance(child, (ast.If, ast.Try, ast.TryStar, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Match))
        for part in ast.iter_child_nodes(child):
            visit(part, branch)

    for statement in node.body:
        visit(statement)
    if bindings != ["direct"] or len(direct) != 1:
        issues.append("constructor-not-one-direct-definition")
    selected = direct[-1] if direct else None
    if selected is not None and selected.decorator_list:
        issues.append("decorated-constructor")
    return selected, issues


def _scope(source: str) -> dict[str, Any]:
    if not isinstance(source, str) or len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        return {"functions": {}, "blocked": {}, "parent_blocks": {}, "error": "source-byte-bound", "dynamic": False}
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError) as exc:
        return {"functions": {}, "blocked": {}, "parent_blocks": {}, "error": type(exc).__name__, "dynamic": False}
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        return {"functions": {}, "blocked": {}, "parent_blocks": {}, "error": "ast-node-bound", "dynamic": False}
    definitions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    bindings: dict[str, list[str]] = {}
    blocked: dict[str, list[str]] = {}
    dynamic = False

    def bind(name: str, kind: str) -> None:
        bindings.setdefault(name, []).append(kind)

    def examine(node: ast.AST, conditional: bool = False) -> None:
        nonlocal dynamic
        if isinstance(node, ast.Lambda):
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bind(node.name, "conditional-definition" if conditional else "function")
            if node.name == "__getattr__":
                dynamic = True
            if not conditional:
                definitions[node.name] = node
                if node.decorator_list:
                    blocked.setdefault(node.name, []).append("decorated-definition")
            return
        if isinstance(node, ast.ClassDef):
            bind(node.name, "conditional-class" if conditional else "class")
            if not conditional and not node.name.startswith("_"):
                constructor, issues = _constructor_info(node)
                qualified = node.name + ".__init__"
                if constructor is not None:
                    definitions[qualified] = constructor
                if issues:
                    blocked[qualified] = issues
            return
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    dynamic = True
                else:
                    bind(alias.asname or (alias.name.split(".")[0] if isinstance(node, ast.Import) else alias.name), "import")
            return
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete, ast.NamedExpr)):
            targets = node.targets if isinstance(node, (ast.Assign, ast.Delete)) else [node.target]
            for target in targets:
                for name in _targets(target):
                    bind(name, "assignment-or-deletion")
        if isinstance(node, (ast.For, ast.AsyncFor)):
            for name in _targets(node.target):
                bind(name, "loop-binding")
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars:
                    for name in _targets(item.optional_vars):
                        bind(name, "with-binding")
        if isinstance(node, ast.ExceptHandler) and node.name:
            bind(node.name, "exception-binding")
        if isinstance(node, ast.MatchAs) and node.name:
            bind(node.name, "pattern-binding")
        if isinstance(node, ast.MatchStar) and node.name:
            bind(node.name, "pattern-binding")
        if isinstance(node, ast.MatchMapping) and node.rest:
            bind(node.rest, "pattern-binding")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _DYNAMIC:
            dynamic = True
        branch = conditional or isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try, ast.TryStar, ast.Match))
        for child in ast.iter_child_nodes(node):
            examine(child, branch)

    for statement in tree.body:
        examine(statement)
    for name, kinds in bindings.items():
        if kinds != ["function"]:
            blocked.setdefault(name, []).append("binding-not-one-direct-function:" + ",".join(kinds))
    public = {name: node for name, node in definitions.items() if not name.startswith("_")}
    for name, node in public.items():
        count = len(node.args.posonlyargs) + len(node.args.args) + len(node.args.kwonlyargs) + bool(node.args.vararg) + bool(node.args.kwarg)
        if count > MAX_PARAMETERS:
            blocked.setdefault(name, []).append("parameter-bound")
    parent_blocks = {name: ["parent-class-binding:" + ",".join(kinds)] for name, kinds in bindings.items() if kinds != ["class"]}
    return {"functions": public, "blocked": blocked, "parent_blocks": parent_blocks, "error": None, "dynamic": dynamic}


def _capture(source: str, module: str, meter: dict[str, Any], use_cache: bool) -> dict[str, Any]:
    raw = source.encode("utf-8")
    asset_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    try:
        griffe_version = importlib.metadata.version("griffelib")
    except importlib.metadata.PackageNotFoundError:
        griffe_version = "unavailable"
    key = (asset_sha, sys.version, griffe_version, module, hashlib.sha256(raw).hexdigest())
    if use_cache and key in _CACHE:
        meter["capture_cache_hits"] += 1
        _CACHE.move_to_end(key)
        return _CACHE[key]
    meter["capture_cache_misses"] += 1
    captured: dict[str, Any] = {"scope": _scope(source), "model": None, "snapshot": None, "source_bytes": len(raw), "griffe_version": griffe_version}
    if not captured["scope"]["error"]:
        try:
            import griffe
            model = griffe.visit(module, Path(module.replace(".", "/") + ".py"), source)
            captured.update(model=model, snapshot=json.loads(model.as_json()))
        except Exception as exc:
            captured["error"] = type(exc).__name__ + ": " + str(exc)
    if use_cache and len(raw) <= CACHE_BYTE_LIMIT:
        while _CACHE and (len(_CACHE) >= CACHE_ENTRY_LIMIT or cache_info()["source_bytes"] + len(raw) > CACHE_BYTE_LIMIT):
            _CACHE.popitem(last=False)
        _CACHE[key] = captured
    return captured


def _stub(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Any:
    a = node.args
    args = ast.arguments(
        posonlyargs=[ast.arg(arg=p.arg) for p in a.posonlyargs],
        args=[ast.arg(arg=p.arg) for p in a.args],
        vararg=ast.arg(arg=a.vararg.arg) if a.vararg else None,
        kwonlyargs=[ast.arg(arg=p.arg) for p in a.kwonlyargs],
        kw_defaults=[None if d is None else ast.Constant(None) for d in a.kw_defaults],
        kwarg=ast.arg(arg=a.kwarg.arg) if a.kwarg else None,
        defaults=[ast.Constant(None) for _ in a.defaults],
    )
    fn = ast.FunctionDef(name="_shape_only", args=args, body=[ast.Return(ast.Constant(None))], decorator_list=[], returns=None, type_comment=None, type_params=[])
    safe_tree = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
    namespace: dict[str, Any] = {"__builtins__": {}}
    exec(compile(safe_tree, "<generated-call-shape-stub>", "exec"), namespace)
    return namespace["_shape_only"]


def _names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    a = node.args
    return [p.arg for p in a.posonlyargs + a.args + a.kwonlyargs] + ([a.vararg.arg] if a.vararg else []) + ([a.kwarg.arg] if a.kwarg else [])


def _fixed(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return len(node.args.posonlyargs) + len(node.args.args)


def _signature_metadata(node: ast.FunctionDef | ast.AsyncFunctionDef | None) -> dict[str, Any] | None:
    if node is None:
        return None
    args = node.args
    positional = args.posonlyargs + args.args
    defaults: list[ast.AST | None] = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    parameters = []
    for index, (parameter, default) in enumerate(zip(positional, defaults)):
        parameters.append({"name": parameter.arg, "kind": "posonly" if index < len(args.posonlyargs) else "poskw", "required": default is None, "default": None if default is None else ast.unparse(default)})
    if args.vararg is not None:
        parameters.append({"name": args.vararg.arg, "kind": "varpos", "required": False, "default": None})
    parameters.extend({"name": parameter.arg, "kind": "kwonly", "required": default is None, "default": None if default is None else ast.unparse(default)} for parameter, default in zip(args.kwonlyargs, args.kw_defaults))
    if args.kwarg is not None:
        parameters.append({"name": args.kwarg.arg, "kind": "varkw", "required": False, "default": None})
    return {"parameters": parameters, "async": isinstance(node, ast.AsyncFunctionDef)}


def _required_keywords(node: ast.FunctionDef | ast.AsyncFunctionDef, n: int) -> list[str]:
    a = node.args
    positional = a.posonlyargs + a.args
    required_until = len(positional) - len(a.defaults)
    result = [p.arg for i, p in enumerate(positional) if i >= n and i >= len(a.posonlyargs) and i < required_until]
    result.extend(p.arg for p, d in zip(a.kwonlyargs, a.kw_defaults) if d is None)
    return sorted(result)


def _warnings(old: ast.FunctionDef | ast.AsyncFunctionDef, new: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    warnings = ["Binding shape does not establish behavior, types, return values, or runtime exports."]
    if isinstance(old, ast.AsyncFunctionDef) != isinstance(new, ast.AsyncFunctionDef):
        warnings.append("async-kind-changed: outside binding guarantee")
    old_order = [p.arg for p in old.args.posonlyargs + old.args.args]
    new_order = [p.arg for p in new.args.posonlyargs + new.args.args]
    if old_order != new_order:
        warnings.append("positional-name-or-order-changed: inspect argument meaning")
    old_defaults = [ast.dump(x, include_attributes=False) if x is not None else None for x in old.args.defaults + old.args.kw_defaults]
    new_defaults = [ast.dump(x, include_attributes=False) if x is not None else None for x in new.args.defaults + new.args.kw_defaults]
    if old_defaults != new_defaults:
        warnings.append("default-expression-or-optionality-changed: values are not executed")
    return warnings


def compare_sources(before: str, after: str, module: str, *, use_cache: bool = True) -> dict[str, Any]:
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    before_hash = hashlib.sha256(before.encode()).hexdigest()
    after_hash = hashlib.sha256(after.encode()).hexdigest()
    functions: list[dict[str, Any]] = []
    meter = {"stub_calls": 0, "frontier_shapes": 0, "functions_considered": 0, "capture_cache_hits": 0, "capture_cache_misses": 0}
    before_capture = _capture(before, module, meter, use_cache)
    after_capture = _capture(after, module, meter, use_cache)
    old, new = before_capture["scope"], after_capture["scope"]
    griffe_info: dict[str, Any] = {"status": "not-run", "alerts": [], "snapshots": {}}
    if not old["error"] and not new["error"]:
        try:
            import griffe
            griffe_info["version"] = before_capture["griffe_version"]
            left, right = before_capture["model"], after_capture["model"]
            if left is None or right is None:
                raise ValueError("Static Griffe capture unavailable: " + str(before_capture.get("error", after_capture.get("error"))))
            griffe_info["snapshots"] = {"before": copy.deepcopy(before_capture["snapshot"]), "after": copy.deepcopy(after_capture["snapshot"])}
            griffe_info["status"] = "complete"
            try:
                for alert in griffe.find_breaking_changes(left, right):
                    griffe_info["alerts"].append({"kind": str(alert.kind), "path": alert.obj.path, "explanation": alert.explain(style=griffe.ExplanationStyle.MARKDOWN)})
            except Exception as exc:
                griffe_info["status"] = "partial"
                griffe_info["error"] = type(exc).__name__ + ": " + str(exc)
        except Exception as exc:
            griffe_info["status"] = "unavailable"
            griffe_info["error"] = type(exc).__name__ + ": " + str(exc)

    def accepted(fn: Any, n: int, keywords: list[str]) -> tuple[bool, str | None]:
        meter["stub_calls"] += 1
        if meter["stub_calls"] > MAX_PROBES:
            raise RuntimeError("stub-probe-bound")
        if fn is None:
            return False, "direct definition absent"
        try:
            fn(*([None] * n), **dict.fromkeys(keywords))
            return True, None
        except TypeError as exc:
            return False, str(exc)

    for name in sorted(old["functions"].keys() | new["functions"].keys()):
        meter["functions_considered"] += 1
        row: dict[str, Any] = {"name": name, "status": "unresolved", "witness": None, "before_signature": None, "after_signature": None}
        reasons = []
        for label, side in (("before", old), ("after", new)):
            if side["error"]:
                reasons.append(label + ":" + side["error"])
            if side["dynamic"]:
                reasons.append(label + ":dynamic-module")
            reasons.extend(label + ":" + reason for reason in side["blocked"].get(name, []))
            if name.endswith(".__init__"):
                reasons.extend(label + ":" + reason for reason in side["parent_blocks"].get(name.split(".", 1)[0], []))
        if reasons:
            row["reason"] = "; ".join(reasons)
            functions.append(row)
            continue
        previous, following = old["functions"].get(name), new["functions"].get(name)
        try:
            row["before_signature"] = _signature_metadata(previous)
            row["after_signature"] = _signature_metadata(following)
        except (ValueError, RecursionError):
            row["reason"] = "signature-metadata-unavailable"
            functions.append(row)
            continue
        if previous is None:
            row.update(status="added", reason="new direct definition; no prior binding obligation")
            functions.append(row)
            continue
        try:
            previous_stub = _stub(previous)
            following_stub = _stub(following) if following is not None else None
            names = set(_names(previous)) | (set(_names(following)) if following is not None else set())
            extra = "__agi_fresh_keyword__"
            while extra in names:
                extra += "_"
            universe = sorted(names | {extra})
            maximum = max(_fixed(previous), _fixed(following) if following is not None else 0) + 1
            row["domain"] = {"max_positional_count": maximum, "keyword_names": universe}
            row["warnings"] = _warnings(previous, following) if following is not None else ["Absence is local to direct definitions; package-level aliases and runtime exports are not established."]
            if name.endswith(".__init__"):
                row["warnings"].append("Unbound direct constructor includes self; class calls additionally depend on __new__, metaclass and MRO behavior.")
            row["status"] = "no_call_loss"
            row["reason"] = "complete minimal-plus-singleton frontier within declared signature model"
            for n in range(maximum + 1):
                required = _required_keywords(previous, n)
                baseline_ok, _ = accepted(previous_stub, n, required)
                if not baseline_ok:
                    continue
                shapes = [required] + [sorted(required + [key]) for key in universe if key not in required]
                for keys in shapes:
                    meter["frontier_shapes"] += 1
                    before_ok, _ = accepted(previous_stub, n, keys)
                    if not before_ok:
                        continue
                    after_ok, rejection = accepted(following_stub, n, keys)
                    if not after_ok:
                        row.update(status="call_loss", witness={"positional_count": n, "keyword_names": keys}, reason=rejection)
                        break
                if row["status"] == "call_loss":
                    break
        except (SyntaxError, ValueError, TypeError, RuntimeError, RecursionError) as exc:
            row.update(status="unresolved", witness=None, reason=type(exc).__name__ + ": " + str(exc))
        functions.append(row)

    unresolved = sum(row["status"] == "unresolved" for row in functions)
    partial = unresolved > 0 or bool(old["error"] or new["error"] or old["dynamic"] or new["dynamic"])
    meter.update(wall_seconds=time.perf_counter() - wall_start, cpu_seconds=time.process_time() - cpu_start, cache=cache_info())
    return {
        "schema": SCHEMA,
        "module": module,
        "source_hashes": {"before": before_hash, "after": after_hash},
        "source_ids": [before_hash, after_hash],
        "status": "partial" if partial else "complete",
        "scope": "Top-level direct non-underscore functions and qualified direct class.__init__ declarations; inert unbound Python argument binding only.",
        "functions": functions,
        "findings": [row for row in functions if row["status"] == "call_loss"],
        "coverage": {"before_direct": len(old["functions"]), "after_direct": len(new["functions"]), "compared": sum(row["status"] in {"call_loss", "no_call_loss"} for row in functions), "call_loss": sum(row["status"] == "call_loss" for row in functions), "unresolved": unresolved},
        "scope_exclusions": {"before": copy.deepcopy(old["blocked"]), "after": copy.deepcopy(new["blocked"])},
        "module_errors": {"before": old["error"], "after": new["error"]},
        "griffe_status": griffe_info["status"],
        "griffe_alerts": griffe_info["alerts"],
        "griffe": griffe_info,
        "meter": meter,
    }
