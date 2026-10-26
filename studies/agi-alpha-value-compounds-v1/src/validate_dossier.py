# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import inspect
import itertools
import keyword
import time
from typing import Any

MAX_SOURCE_BYTES = 1_000_000
MAX_AST_NODES = 100_000
MAX_PARAMETERS = 64
DEFAULT_SHAPE_BUDGET = 1_000_000


class DeclarationInventory(ast.NodeVisitor):
    def __init__(self, *, module_level: bool = True) -> None:
        self.definitions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.bindings: Counter[str] = Counter()
        self.other_bindings: set[str] = set()
        self.excluded: set[str] = set()
        self.branch = 0
        self.dynamic = False
        self.module_level = module_level
        self.direct_classes: set[str] = set()

    def generic_visit(self, node: ast.AST) -> None:
        is_branch = isinstance(node, (ast.If, ast.Try, ast.TryStar, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Match))
        self.branch += int(is_branch)
        super().generic_visit(node)
        self.branch -= int(is_branch)

    def _define(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.bindings[node.name] += 1
        if self.module_level and node.name == "__getattr__":
            self.dynamic = True
        if self.branch:
            self.excluded.add(node.name)
        else:
            self.definitions[node.name] = node
        if node.decorator_list:
            self.excluded.add(node.name)

    visit_FunctionDef = _define
    visit_AsyncFunctionDef = _define

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.bindings[node.name] += 1
        self.other_bindings.add(node.name)
        if self.branch or node.name.startswith("_"):
            return
        self.direct_classes.add(node.name)
        child = DeclarationInventory(module_level=False)
        child.visit(ast.Module(body=node.body, type_ignores=[]))
        constructor = child.definitions.get("__init__")
        qualified = node.name + ".__init__"
        if isinstance(constructor, ast.FunctionDef):
            self.definitions[qualified] = constructor
        invalid = node.decorator_list or len(node.bases) > 1 or node.keywords or child.dynamic or not isinstance(constructor, ast.FunctionDef) or child.bindings["__init__"] != 1 or "__init__" in child.excluded or "__init__" in child.other_bindings
        if invalid:
            self.excluded.add(qualified)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def _bind_target(self, node: ast.AST) -> None:
        if isinstance(node, ast.Name):
            self.bindings[node.id] += 1
            self.other_bindings.add(node.id)
        elif isinstance(node, (ast.Attribute, ast.Subscript, ast.Starred)):
            self._bind_target(node.value)
        elif isinstance(node, (ast.List, ast.Tuple)):
            for item in node.elts:
                self._bind_target(item)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._bind_target(target)
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._bind_target(node.target)
        if node.value is not None:
            self.visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._bind_target(node.target)
        self.visit(node.value)

    def visit_Delete(self, node: ast.Delete) -> None:
        for target in node.targets:
            self._bind_target(target)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self._bind_target(node.target)
        self.visit(node.value)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.bindings[name] += 1
            self.other_bindings.add(name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                self.dynamic = True
            else:
                name = alias.asname or alias.name
                self.bindings[name] += 1
                self.other_bindings.add(name)

    def visit_For(self, node: ast.For | ast.AsyncFor) -> None:
        self._bind_target(node.target)
        self.generic_visit(node)

    visit_AsyncFor = visit_For

    def visit_With(self, node: ast.With | ast.AsyncWith) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self._bind_target(item.optional_vars)
        self.generic_visit(node)

    visit_AsyncWith = visit_With

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.bindings[node.name] += 1
            self.other_bindings.add(node.name)
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name:
            self.bindings[node.name] += 1
            self.other_bindings.add(node.name)
        self.generic_visit(node)

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
        if node.rest:
            self.bindings[node.rest] += 1
            self.other_bindings.add(node.rest)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval", "globals", "locals"}:
            self.dynamic = True
        self.generic_visit(node)


def _read_declarations(source: str) -> dict[str, Any]:
    if not isinstance(source, str) or len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        return {"functions": {}, "excluded": set(), "parent_excluded": set(), "error": "source-byte-bound", "dynamic": False}
    try:
        tree = ast.parse(source)
        if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
            raise ValueError("ast-node-bound")
    except (SyntaxError, ValueError, RecursionError) as exc:
        return {"functions": {}, "excluded": set(), "parent_excluded": set(), "error": str(exc), "dynamic": False}
    inventory = DeclarationInventory()
    inventory.visit(tree)
    exclusions = inventory.excluded | inventory.other_bindings | {name for name, count in inventory.bindings.items() if count != 1}
    public = {name: node for name, node in inventory.definitions.items() if not name.startswith("_")}
    for name, node in public.items():
        a = node.args
        if len(a.posonlyargs) + len(a.args) + len(a.kwonlyargs) + int(a.vararg is not None) + int(a.kwarg is not None) > MAX_PARAMETERS:
            exclusions.add(name)
    parent_excluded = {name for name, count in inventory.bindings.items() if name not in inventory.direct_classes or count != 1}
    return {"functions": public, "excluded": exclusions, "parent_excluded": parent_excluded, "error": None, "dynamic": inventory.dynamic}


def _safe_callable(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Any:
    args = node.args
    positional = args.posonlyargs + args.args
    required_count = len(positional) - len(args.defaults)
    fields = []
    for index, parameter in enumerate(positional):
        if not parameter.arg.isidentifier() or keyword.iskeyword(parameter.arg):
            raise ValueError("invalid parsed parameter identifier")
        fields.append(parameter.arg + ("=None" if index >= required_count else ""))
        if index + 1 == len(args.posonlyargs):
            fields.append("/")
    if args.vararg:
        fields.append("*" + args.vararg.arg)
    elif args.kwonlyargs:
        fields.append("*")
    for parameter, default in zip(args.kwonlyargs, args.kw_defaults):
        fields.append(parameter.arg + ("=None" if default is not None else ""))
    if args.kwarg:
        fields.append("**" + args.kwarg.arg)
    for parameter in [*args.kwonlyargs, *([args.vararg] if args.vararg else []), *([args.kwarg] if args.kwarg else [])]:
        if not parameter.arg.isidentifier() or keyword.iskeyword(parameter.arg):
            raise ValueError("invalid parsed parameter identifier")
    generated = "def _binding_test(" + ", ".join(fields) + "):\n    return None\n"
    namespace: dict[str, Any] = {"__builtins__": {}}
    exec(compile(generated, "<independent-generated-binding-stub>", "exec"), namespace)
    return namespace["_binding_test"]


def _metadata_signature(node: ast.FunctionDef | ast.AsyncFunctionDef | None) -> dict[str, Any] | None:
    if node is None:
        return None
    a = node.args
    pos = a.posonlyargs + a.args
    count_required = len(pos) - len(a.defaults)
    rows = []
    for index, arg in enumerate(pos):
        optional = index >= count_required
        rows.append({"name": arg.arg, "kind": "posonly" if index < len(a.posonlyargs) else "poskw", "required": not optional, "default": ast.unparse(a.defaults[index - count_required]) if optional else None})
    if a.vararg:
        rows.append({"name": a.vararg.arg, "kind": "varpos", "required": False, "default": None})
    for index, arg in enumerate(a.kwonlyargs):
        default = a.kw_defaults[index]
        rows.append({"name": arg.arg, "kind": "kwonly", "required": default is None, "default": ast.unparse(default) if default is not None else None})
    if a.kwarg:
        rows.append({"name": a.kwarg.arg, "kind": "varkw", "required": False, "default": None})
    return {"parameters": rows, "async": isinstance(node, ast.AsyncFunctionDef)}


def _call(fn: Any, positional_count: int, keyword_names: list[str], meter: dict[str, int]) -> bool:
    meter["stub_calls"] += 1
    if fn is None:
        return False
    try:
        fn(*([0] * positional_count), **dict.fromkeys(keyword_names, 0))
        return True
    except TypeError:
        return False


def exhaustive_relation(before_node: ast.FunctionDef | ast.AsyncFunctionDef, after_node: ast.FunctionDef | ast.AsyncFunctionDef | None, *, shape_budget: int = DEFAULT_SHAPE_BUDGET, mode: str = "auto") -> dict[str, Any]:
    if mode not in {"auto", "exhaustive"}:
        raise ValueError("validation mode must be auto or exhaustive")
    previous = _safe_callable(before_node)
    following = _safe_callable(after_node) if after_node is not None else None
    old_signature = inspect.signature(previous)
    new_signature = inspect.signature(following) if following is not None else None
    meter = {"stub_calls": 0, "shapes_examined": 0}
    if old_signature == new_signature:
        return {"status": "no_call_loss", "witness": None, "method": "identical generated binding signatures", "meter": meter}
    names = set(old_signature.parameters) | (set(new_signature.parameters) if new_signature is not None else set())
    fresh = "__independent_fresh_keyword__"
    while fresh in names:
        fresh += "_"
    universe = sorted(names | {fresh})
    kinds = {inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD}
    old_fixed = sum(p.kind in kinds for p in old_signature.parameters.values())
    new_fixed = sum(p.kind in kinds for p in new_signature.parameters.values()) if new_signature is not None else 0
    maximum = max(old_fixed, new_fixed) + 1
    complete_domain = (maximum + 1) * 2 ** len(universe)
    if mode == "auto" and complete_domain > shape_budget:
        parameters = list(old_signature.parameters.values())
        positionals = [p for p in parameters if p.kind in kinds]
        for n in range(maximum + 1):
            required = {p.name for i, p in enumerate(positionals) if i >= n and p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD and p.default is inspect.Parameter.empty}
            required.update(p.name for p in parameters if p.kind == inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty)
            for extra_name in [None, *[key for key in universe if key not in required]]:
                if meter["shapes_examined"] >= shape_budget:
                    return {"status": "unresolved", "reason": "independent-frontier-shape-bound", "witness": None, "domain_size": complete_domain, "meter": meter}
                keys = sorted(required | ({extra_name} if extra_name is not None else set()))
                meter["shapes_examined"] += 1
                before_ok = _call(previous, n, keys, meter)
                if extra_name is None and not before_ok:
                    break
                if before_ok and not _call(following, n, keys, meter):
                    return {"status": "call_loss", "witness": {"positional_count": n, "keyword_names": keys}, "method": "complete safe-stub frontier; large finite domain", "domain_size": complete_domain, "meter": meter}
        return {"status": "no_call_loss", "witness": None, "method": "complete safe-stub frontier; large finite domain", "domain_size": complete_domain, "meter": meter}
    for n in range(maximum + 1):
        for count in range(len(universe) + 1):
            for subset in itertools.combinations(universe, count):
                if meter["shapes_examined"] >= shape_budget:
                    return {"status": "unresolved", "reason": "independent-exhaustive-shape-bound", "witness": None, "domain_size": complete_domain, "meter": meter}
                meter["shapes_examined"] += 1
                keys = list(subset)
                if _call(previous, n, keys, meter) and not _call(following, n, keys, meter):
                    return {"status": "call_loss", "witness": {"positional_count": n, "keyword_names": keys}, "domain_size": complete_domain, "meter": meter}
    return {"status": "no_call_loss", "witness": None, "method": "exhaustive finite binding domain", "domain_size": complete_domain, "meter": meter}


def validate_dossier(before: str, after: str, module: str, report: dict[str, Any], *, shape_budget: int = DEFAULT_SHAPE_BUDGET, validation_mode: str = "auto") -> dict[str, Any]:
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    errors: list[str] = []
    unknowns: list[str] = []
    checks: list[dict[str, Any]] = []
    meter = {"stub_calls": 0, "shapes_examined": 0, "witnesses_checked": 0}
    old, new = _read_declarations(before), _read_declarations(after)
    expected_names = old["functions"].keys() | new["functions"].keys()
    if not isinstance(report, dict):
        return {"schema": "agialpha-call-shape-validation/v1", "accepted": False, "errors": ["report must be object"]}
    if report.get("module") != module:
        errors.append("module identity mismatch")
    if report.get("source_hashes") != {"before": hashlib.sha256(before.encode()).hexdigest(), "after": hashlib.sha256(after.encode()).hexdigest()}:
        errors.append("source hashes mismatch")
    if report.get("source_ids") != [hashlib.sha256(before.encode()).hexdigest(), hashlib.sha256(after.encode()).hexdigest()]:
        errors.append("consumer-adapter source identities mismatch")
    rows = report.get("functions")
    if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get("name"), str) for row in rows):
        return {"schema": "agialpha-call-shape-validation/v1", "accepted": False, "errors": errors + ["malformed function rows"]}
    names = [row["name"] for row in rows]
    if len(names) != len(set(names)) or set(names) != expected_names:
        errors.append("missing, extra, or duplicated direct function inventory")
    by_name = {row["name"]: row for row in rows}
    all_scope_complete = True
    for name in sorted(expected_names):
        row = by_name.get(name)
        if row is None:
            continue
        expected = "unresolved"
        reasons = []
        for side in (old, new):
            if side["error"] or side["dynamic"] or name in side["excluded"]:
                reasons.append("source scope unavailable or excluded")
            if name.endswith(".__init__") and name.split(".", 1)[0] in side["parent_excluded"]:
                reasons.append("parent class is rebound or unavailable")
        previous, following = old["functions"].get(name), new["functions"].get(name)
        if row.get("status") in {"call_loss", "no_call_loss", "added"}:
            for version, declaration in (("before", previous), ("after", following)):
                try:
                    if row.get(version + "_signature") != _metadata_signature(declaration):
                        errors.append(name + ": " + version + " signature metadata differs from source")
                except (ValueError, RecursionError):
                    errors.append(name + ": signature metadata could not be independently checked")
        relation = None
        previous_fn = following_fn = None
        if reasons:
            all_scope_complete = False
        elif previous is None:
            expected = "added"
        else:
            try:
                previous_fn = _safe_callable(previous)
                following_fn = _safe_callable(following) if following is not None else None
                relation = exhaustive_relation(previous, following, shape_budget=max(0, shape_budget - meter["shapes_examined"]), mode=validation_mode)
                for key in ("stub_calls", "shapes_examined"):
                    meter[key] += relation["meter"][key]
                expected = relation["status"]
                if expected == "unresolved":
                    unknowns.append(name + ": independent completeness exceeds shape budget")
            except (SyntaxError, ValueError, TypeError, RecursionError):
                reasons.append("safe stub could not represent declaration")
                all_scope_complete = False
        result: dict[str, Any] = {"name": name, "reported": row.get("status"), "independent_status": expected, "witness_valid": None}
        if relation is not None:
            result["independent_method"] = relation.get("method", "exhaustive finite binding domain")
            result["independent_witness"] = relation.get("witness")
            result["domain_size"] = relation.get("domain_size")
        if expected == "unresolved" and not reasons and relation is not None:
            if row.get("status") not in {"unresolved", "call_loss", "no_call_loss"}:
                errors.append(name + ": impossible reported status")
        elif row.get("status") != expected:
            errors.append(name + ": status differs from independent source relation")
        if row.get("status") == "call_loss":
            witness = row.get("witness")
            valid_shape = isinstance(witness, dict) and set(witness) == {"positional_count", "keyword_names"} and type(witness.get("positional_count")) is int and 0 <= witness["positional_count"] <= MAX_PARAMETERS + 1 and isinstance(witness.get("keyword_names"), list) and all(isinstance(key, str) for key in witness["keyword_names"]) and len(witness["keyword_names"]) <= 2 * MAX_PARAMETERS + 1 and len(set(witness["keyword_names"])) == len(witness["keyword_names"])
            valid = False
            if valid_shape and previous_fn is not None and not reasons:
                valid = _call(previous_fn, witness["positional_count"], witness["keyword_names"], meter) and not _call(following_fn, witness["positional_count"], witness["keyword_names"], meter)
            result["witness_valid"] = valid
            meter["witnesses_checked"] += 1
            if not valid:
                errors.append(name + ": invalid before-valid/after-invalid witness")
            elif expected == "unresolved" and not reasons:
                unknowns = [text for text in unknowns if not text.startswith(name + ":")]
                result["independent_status"] = "call_loss"
        elif row.get("witness") is not None:
            errors.append(name + ": non-breaking row carries witness")
        checks.append(result)
    expected_coverage = {"before_direct": len(old["functions"]), "after_direct": len(new["functions"]), "compared": sum(row.get("status") in {"call_loss", "no_call_loss"} for row in rows), "call_loss": sum(row.get("status") == "call_loss" for row in rows), "unresolved": sum(row.get("status") == "unresolved" for row in rows)}
    coverage = report.get("coverage")
    if not isinstance(coverage, dict) or any(type(coverage.get(k)) is not int or coverage[k] != v for k, v in expected_coverage.items()):
        errors.append("coverage counters do not reconcile")
    findings = report.get("findings")
    if not isinstance(findings, list) or any(not isinstance(row, dict) or not isinstance(row.get("name"), str) for row in findings):
        errors.append("findings must be a list of objects")
    else:
        finding_names = [row.get("name") for row in findings]
        breaking_names = {row["name"] for row in rows if row.get("status") == "call_loss"}
        if len(finding_names) != len(set(str(x) for x in finding_names)) or set(str(x) for x in finding_names) != breaking_names:
            errors.append("findings inventory differs from call-loss rows")
        for row in findings:
            if row.get("status") != "call_loss":
                errors.append("finding is not labeled call_loss")
            if row.get("name") in by_name and row.get("witness") != by_name[row["name"]].get("witness"):
                errors.append("finding witness differs from function row")
    inherent_partial = bool(old["error"] or new["error"] or old["dynamic"] or new["dynamic"] or expected_coverage["unresolved"])
    if report.get("status") != ("partial" if inherent_partial else "complete"):
        errors.append("overall status hides unresolved source scope")
    meter.update(cpu_seconds=time.process_time() - cpu_start, wall_seconds=time.perf_counter() - wall_start)
    return {"schema": "agialpha-call-shape-validation/v1", "module": module, "accepted": not errors and not unknowns, "report_correct": not errors, "scope_complete": all_scope_complete and not inherent_partial and not unknowns, "errors": errors, "unknowns": unknowns, "checks": checks, "meter": meter, "mode": validation_mode, "semantics": "Original source was parsed, never imported or executed; only reconstructed inert argument-binding stubs ran."}
