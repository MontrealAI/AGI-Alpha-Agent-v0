# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import ast
import time
from collections import Counter, defaultdict
from pathlib import PurePosixPath

from dossier import MAX_BYTES, MAX_NODES, _constraints, _module_dynamic, content_id

SCHEMA = "consumer-call-assessment/v1"
MAX_CALLS = 50_000


def _module(path):
    path = str(path).replace("\\", "/")
    if path.endswith(".py"):
        parts = list(PurePosixPath(path).with_suffix("").parts)
        if parts and parts[0] == "src":
            parts.pop(0)
        if parts and parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)
    return path.replace("/", ".")


def _parse(source):
    if len(source.encode()) > MAX_BYTES or "\x00" in source:
        return None, "source-bound"
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError) as exc:
        return None, type(exc).__name__
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        return None, "ast-node-limit"
    return tree, None


def _relative(node, module, package):
    if not node.level:
        return node.module or ""
    parts = module.split(".") if package else module.split(".")[:-1]
    if node.level > len(parts):
        return None
    prefix = parts[:len(parts) - node.level + 1]
    return ".".join(prefix + ((node.module or "").split(".") if node.module else []))


class _Bindings(ast.NodeVisitor):
    def __init__(self, body, module, package, parameters=(), allow_guards=False):
        self.names = defaultdict(list)
        self.dynamic = False
        self.module, self.package = module, package
        self.direct = set(id(n) for n in body)
        if allow_guards:
            for node in body:
                if isinstance(node, ast.Try) and node.handlers and not node.orelse and not node.finalbody and all(isinstance(n, (ast.Import, ast.ImportFrom)) for n in node.body) and all(h.body and isinstance(h.body[-1], ast.Raise) for h in node.handlers):
                    self.direct.update(id(n) for n in node.body)
        for name in parameters:
            self.names[name].append({"kind": "other", "line": 0})
        for node in body:
            self.visit(node)

    def _add(self, name, node, **item):
        self.names[name].append({"kind": "other", "line": getattr(node, "lineno", 0), **item})

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self._add(node.id, node)

    def visit_Attribute(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            root = node.value
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                self._add(root.id, node)
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self._add(name, node, kind="import" if id(node) in self.direct else "other",
                      module=alias.name if alias.asname else name, attrs=(), imported=alias.name)

    def visit_ImportFrom(self, node):
        module = _relative(node, self.module, self.package)
        for alias in node.names:
            if alias.name == "*":
                self.dynamic = True
                continue
            self._add(alias.asname or alias.name, node,
                      kind="import" if id(node) in self.direct and module else "other",
                      module=module, attrs=(alias.name,), imported=None)

    def visit_FunctionDef(self, node):
        self._add(node.name, node, kind="function" if id(node) in self.direct else "other")
        for expr in node.decorator_list + node.args.defaults + [d for d in node.args.kw_defaults if d]:
            self.visit(expr)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._add(node.name, node, kind="class" if id(node) in self.direct else "other")
        for expr in node.decorator_list + node.bases + [k.value for k in node.keywords]:
            self.visit(expr)

    def visit_Lambda(self, node):
        for expr in node.args.defaults + [d for d in node.args.kw_defaults if d]:
            self.visit(expr)

    def visit_ListComp(self, node):
        for expr in ast.walk(node):
            if isinstance(expr, ast.NamedExpr):
                self.visit(expr.target)

    visit_SetComp = visit_ListComp
    visit_DictComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval", "globals", "locals"}:
            self.dynamic = True
        self.generic_visit(node)

    def visit_Global(self, node):
        for name in node.names:
            self._add(name, node)

    visit_Nonlocal = visit_Global

    def visit_ExceptHandler(self, node):
        if node.name:
            self._add(node.name, node)
        self.generic_visit(node)

    def visit_MatchAs(self, node):
        if node.name:
            self._add(node.name, node)
        self.generic_visit(node)

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node):
        if node.rest:
            self._add(node.rest, node)
        self.generic_visit(node)


def _literal_all(tree):
    assignments = [n for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "__all__"]
    stores = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == "__all__" and isinstance(n.ctx, (ast.Store, ast.Del))]
    mutations = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "__all__"]
    permitted_loads = {id(second.iter) for first, second in zip(tree.body, tree.body[1:]) if _metadata_pair(first, second)}
    other_loads = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == "__all__" and isinstance(n.ctx, ast.Load) and id(n) not in permitted_loads]
    if len(assignments) != 1 or len(stores) != 1 or mutations or other_loads:
        return None
    value = assignments[0].value
    if not isinstance(value, (ast.List, ast.Tuple)) or not all(isinstance(x, ast.Constant) and isinstance(x.value, str) for x in value.elts):
        return None
    return sorted(set(x.value for x in value.elts))


def _metadata_pair(first, second):
    if not isinstance(first, ast.Assign) or len(first.targets) != 1 or not isinstance(first.targets[0], ast.Name):
        return False
    value = first.value
    if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name) or value.func.id != "locals" or value.args or value.keywords:
        return False
    if not isinstance(second, ast.For) or not isinstance(second.target, ast.Name) or not isinstance(second.iter, ast.Name) or second.iter.id != "__all__" or second.orelse or len(second.body) != 1:
        return False
    branch = second.body[0]
    if not isinstance(branch, ast.If) or branch.orelse or len(branch.body) != 1 or not isinstance(branch.test, ast.UnaryOp) or not isinstance(branch.test.op, ast.Not):
        return False
    check = branch.test.operand
    if not isinstance(check, ast.Call) or not isinstance(check.func, ast.Attribute) or not isinstance(check.func.value, ast.Name) or check.func.value.id != second.target.id or check.func.attr != "startswith" or len(check.args) != 1 or not isinstance(check.args[0], ast.Constant) or check.args[0].value != "__" or check.keywords:
        return False
    expr = branch.body[0]
    call = expr.value if isinstance(expr, ast.Expr) else None
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != "setattr" or len(call.args) != 3 or call.keywords:
        return False
    obj, field, label = call.args
    return isinstance(obj, ast.Subscript) and isinstance(obj.value, ast.Name) and obj.value.id == first.targets[0].id and isinstance(obj.slice, ast.Name) and obj.slice.id == second.target.id and isinstance(field, ast.Constant) and field.value == "__module__" and isinstance(label, ast.Constant) and isinstance(label.value, str)


def _candidate_namespace(tree):
    clean, metadata = [], []
    i = 0
    while i < len(tree.body):
        node = tree.body[i]
        if i + 1 < len(tree.body) and _metadata_pair(node, tree.body[i + 1]):
            metadata.append({"line": node.lineno, "end_line": tree.body[i + 1].end_lineno, "kind": "declared-export-module-metadata-write"})
            i += 2
            continue
        if not (isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names)):
            clean.append(node)
        i += 1
    return ast.Module(body=clean, type_ignores=[]), metadata


class _Producer:
    def __init__(self, files, candidate=False):
        self.modules = {}
        self.errors = []
        self.candidate = candidate
        for path, source in sorted(files.items()):
            module = _module(path)
            tree, reason = _parse(source)
            entry = {"path": path, "sha256": content_id(source), "reason": reason, "all": _literal_all(tree) if tree else None,
                     "bindings": _Bindings(tree.body, module, str(path).endswith("__init__.py"), allow_guards=candidate) if tree else None,
                     "stars": [n for n in tree.body if isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names)] if tree else [], "metadata": []}
            if tree and (_module_dynamic(tree) or entry["bindings"].dynamic):
                entry["reason"] = "wildcard-or-dynamic-producer-module"
                if candidate and entry["all"] is not None:
                    cleaned, metadata = _candidate_namespace(tree)
                    candidate_bindings = _Bindings(cleaned.body, module, str(path).endswith("__init__.py"), allow_guards=True)
                    if not _module_dynamic(cleaned) and not candidate_bindings.dynamic:
                        entry.update(reason=None, bindings=candidate_bindings, metadata=metadata)
            if module in self.modules:
                entry["reason"] = "duplicate-module-path"
            self.modules[module] = entry
            if entry["reason"]:
                self.errors.append({"path": path, "module": module, "reason": entry["reason"]})

    def resolve(self, module, attrs, chain=(), seen=frozenset()):
        key = (module, tuple(attrs))
        if key in seen or len(chain) >= 32:
            return {"reason": "alias-cycle-or-depth-bound", "chain": list(chain)}
        entry = self.modules.get(module)
        step = {"module": module, "attributes": list(attrs), "source_sha256": entry["sha256"] if entry else None}
        chain = (*chain, step)
        if entry is None or entry["reason"]:
            return {"reason": entry["reason"] if entry else "producer-module-source-unavailable", "chain": list(chain)}
        if not attrs:
            return {"reason": "module-is-not-a-direct-callable", "chain": list(chain)}
        name, rest = attrs[0], tuple(attrs[1:])
        bindings = list(entry["bindings"].names.get(name, []))
        if self.candidate and entry["stars"]:
            proof = []
            for star in entry["stars"]:
                target = _relative(star, module, str(entry["path"]).endswith("__init__.py"))
                exported = self.modules.get(target)
                if exported is None or exported["all"] is None or exported["reason"]:
                    return {"reason": "wildcard-export-set-not-closed-in-supplied-source", "chain": list(chain)}
                proof.append({"module": target, "source_sha256": exported["sha256"], "literal_all": exported["all"]})
                if name in exported["all"]:
                    bindings.append({"kind": "import", "module": target, "attrs": (name,), "imported": None})
            step["closed_wildcard_export_sources"] = proof
            step["metadata_only_source_pattern"] = entry["metadata"]
            step["qualification"] = "syntactic-reexport-candidate-runtime-unproved"
        if len(bindings) != 1:
            return {"reason": "missing-or-ambiguous-producer-binding", "chain": list(chain)}
        binding = bindings[0]
        if binding["kind"] in {"function", "class"}:
            kind = binding["kind"]
            if (kind == "function" and not rest) or (kind == "class" and rest in ((), ("__init__",))):
                return {"module": module, "name": name if kind == "function" else name + ".__init__",
                        "implicit_receiver": int(kind == "class" and not rest), "kind": kind,
                        "source_sha256": entry["sha256"], "chain": list(chain), "reason": None}
            return {"reason": "method-or-attribute-outside-direct-scope", "chain": list(chain)}
        if binding["kind"] != "import":
            return {"reason": "producer-binding-not-an-explicit-import-or-declaration", "chain": list(chain)}
        target, parts = binding["module"], tuple(binding["attrs"])
        if target == module and len(parts) == 1 and target + "." + parts[0] in self.modules:
            target, parts = target + "." + parts[0], ()
        imported = binding.get("imported")
        full = ".".join((target, *parts, *rest))
        if imported and imported.startswith(target + ".") and full.startswith(imported + "."):
            target, parts, rest = imported, (), tuple(full[len(imported) + 1:].split("."))
        return self.resolve(target, (*parts, *rest), chain, seen | {key})


class _Scope:
    def __init__(self, body, module, package, parent=None, parameters=(), deferred=False, class_context=None, candidate=False, class_scope=False):
        self.candidate = candidate if parent is None else parent.candidate
        self.bindings = _Bindings(body, module, package, parameters, allow_guards=self.candidate)
        self.parent, self.deferred, self.class_context = parent, deferred, class_context
        self.module, self.package = module, package
        self.class_scope = class_scope

    def lookup(self, name, line, deferred=False):
        if self.bindings.dynamic:
            return None, "wildcard-or-dynamic-consumer-scope"
        candidates = self.bindings.names.get(name, [])
        if candidates:
            if len(candidates) != 1 or candidates[0]["kind"] != "import":
                return None, "shadowed-or-nonimport-consumer-name"
            binding = candidates[0]
            if binding["line"] > line and not deferred:
                return None, "call-precedes-import"
            return binding, None
        if self.parent:
            return self.parent.lookup(name, line, deferred or self.deferred)
        return None, "unresolved-consumer-name"

    def has_binding(self, name):
        if self.bindings.dynamic or name in self.bindings.names:
            return True
        return self.parent.has_binding(name) if self.parent else False


def _qualified(expr):
    parts = []
    while isinstance(expr, ast.Attribute):
        parts.append(expr.attr)
        expr = expr.value
    return (expr.id, tuple(reversed(parts))) if isinstance(expr, ast.Name) else None


def _reference(expr, scope, producer, line):
    qualified = _qualified(expr)
    if qualified is None:
        return {"reason": "dynamic-or-instance-call-target", "chain": []}
    name, rest = qualified
    binding, reason = scope.lookup(name, line)
    if reason:
        return {"reason": reason, "chain": []}
    module, attrs = binding["module"], tuple(binding["attrs"])
    full = ".".join((module, *attrs, *rest))
    imported = binding.get("imported")
    if imported and imported.startswith(module + ".") and full.startswith(imported + "."):
        module, attrs, rest = imported, (), tuple(full[len(imported) + 1:].split("."))
    return producer.resolve(module, (*attrs, *rest))


def _target(call, scope, producer):
    target = call.func
    if isinstance(target, ast.Attribute) and target.attr == "__init__" and isinstance(target.value, ast.Call):
        sup = target.value
        context = scope.class_context
        if isinstance(sup.func, ast.Name) and sup.func.id == "super" and not sup.args and not sup.keywords:
            if scope.has_binding("super") or context is None:
                return {"reason": "super-context-or-binding-unresolved", "chain": []}
            cls, defining_scope, method = context
            if len(cls.bases) != 1 or cls.keywords or cls.decorator_list or method.decorator_list:
                return {"reason": "super-requires-one-undecorated-explicit-base", "chain": []}
            result = _reference(cls.bases[0], defining_scope, producer, cls.lineno)
            if result.get("kind") != "class":
                return {"reason": result.get("reason") or "base-is-not-a-direct-class", "chain": result.get("chain", [])}
            result["implicit_receiver"] = 1
            result["dispatch"] = "single-base-super-init-under-stated-mro-assumption"
            return result
    return _reference(target, scope, producer, call.lineno)


def _triage(call, scope, producer):
    expr, lookup_scope = call.func, scope
    if isinstance(expr, ast.Attribute) and expr.attr == "__init__" and isinstance(expr.value, ast.Call) and isinstance(expr.value.func, ast.Name) and expr.value.func.id == "super" and scope.class_context:
        cls, defining_scope, _ = scope.class_context
        if len(cls.bases) == 1:
            expr, lookup_scope = cls.bases[0], defining_scope
    qualified = _qualified(expr)
    if qualified is None:
        return {"category": "unattributed-call", "reason": "target-is-not-an-import-name-chain"}
    name, _ = qualified
    while lookup_scope is not None:
        bindings = lookup_scope.bindings.names.get(name, [])
        if bindings:
            imports = sorted({b["module"] for b in bindings if b.get("module")})
            roots = {m.split(".")[0] for m in producer.modules}
            relevant = [m for m in imports if m.split(".")[0] in roots]
            return {"category": "dependency-import-reference" if relevant else "other-import-reference" if imports else "unattributed-call",
                    "declared_import_modules": imports, "supplied_dependency_modules": relevant,
                    "binding_resolved": len(bindings) == 1 and bindings[0]["kind"] == "import",
                    "meaning": "Triage records a declared dependency import reference, not successful dispatch or impact."}
        lookup_scope = lookup_scope.parent
    return {"category": "unattributed-call", "reason": "no-import-binding-in-lexical-scope"}


def _shape(call):
    count = 0
    names = set()
    for arg in call.args:
        if isinstance(arg, ast.Starred):
            if not isinstance(arg.value, (ast.Tuple, ast.List)) or any(isinstance(x, ast.Starred) for x in arg.value.elts):
                return None, "dynamic-positional-expansion"
            count += len(arg.value.elts)
        else:
            count += 1
    for keyword in call.keywords:
        if keyword.arg is not None:
            current = {keyword.arg}
        elif isinstance(keyword.value, ast.Dict) and all(isinstance(k, ast.Constant) and isinstance(k.value, str) for k in keyword.value.keys):
            current = {k.value for k in keyword.value.keys}
        else:
            return None, "dynamic-keyword-expansion"
        if names & current:
            return None, "duplicate-keyword-across-arguments"
        names.update(current)
    return {"positional_count": count, "keyword_names": sorted(names)}, None


def _accepts(signature, shape, implicit):
    names = set(shape["keyword_names"])
    universe = names | {p["name"] for p in signature["parameters"]}
    constraints = _constraints(signature, shape["positional_count"] + implicit, universe)
    return constraints is not None and constraints[0] <= names <= constraints[1]


def _parameters(args):
    return [a.arg for a in [*args.posonlyargs, *args.args, *args.kwonlyargs, *([args.vararg] if args.vararg else []), *([args.kwarg] if args.kwarg else [])]]


def _lexical(scope):
    while scope is not None and scope.class_scope:
        scope = scope.parent
    return scope


class _Calls(ast.NodeVisitor):
    def __init__(self, source, scope, emit):
        self.source, self.scope, self.emit = source, scope, emit
        self.class_definition = None

    def visit_Call(self, node):
        self.emit(node, self.scope)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        old = self.scope
        for expr in node.decorator_list + node.args.defaults + [d for d in node.args.kw_defaults if d]:
            self.visit(expr)
        for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs, *([node.args.vararg] if node.args.vararg else []), *([node.args.kwarg] if node.args.kwarg else [])]:
            if arg.annotation:
                self.visit(arg.annotation)
        if node.returns:
            self.visit(node.returns)
        context = None
        parent = old
        if self.class_definition is not None:
            cls, defining_scope = self.class_definition
            parent = _lexical(defining_scope)
            context = (cls, defining_scope, node)
        self.scope = _Scope(node.body, old.module, old.package, parent, _parameters(node.args), True, context)
        old_class, self.class_definition = self.class_definition, None
        for child in node.body:
            self.visit(child)
        self.scope, self.class_definition = old, old_class

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        old, old_class = self.scope, self.class_definition
        for expr in node.decorator_list + node.bases + [k.value for k in node.keywords]:
            self.visit(expr)
        self.scope = _Scope(node.body, old.module, old.package, _lexical(old), class_scope=True)
        self.class_definition = (node, old)
        for child in node.body:
            self.visit(child)
        self.scope, self.class_definition = old, old_class

    def visit_Lambda(self, node):
        old, old_class = self.scope, self.class_definition
        for expr in node.args.defaults + [d for d in node.args.kw_defaults if d]:
            self.visit(expr)
        self.scope = _Scope([node.body], old.module, old.package, _lexical(old), _parameters(node.args), True)
        self.class_definition = None
        self.visit(node.body)
        self.scope, self.class_definition = old, old_class

    def visit_ListComp(self, node):
        old, old_class = self.scope, self.class_definition
        targets = [g.target for g in node.generators]
        self.scope = _Scope(targets, old.module, old.package, _lexical(old))
        self.class_definition = None
        self.generic_visit(node)
        self.scope, self.class_definition = old, old_class

    visit_SetComp = visit_ListComp
    visit_DictComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp


def _assess_consumers(consumer_files, before_files, after_files, producer_reports, candidate):
    start, cpu = time.perf_counter_ns(), time.process_time_ns()
    before, after = _Producer(before_files, candidate), _Producer(after_files, candidate)
    reports, report_errors = {}, []
    for report in producer_reports:
        module = _module(report["module"])
        expected = [index.modules.get(module, {}).get("sha256") for index in (before, after)]
        if report.get("source_ids") != expected or None in expected or module in reports:
            report_errors.append({"module": module, "reason": "report-source-identity-or-uniqueness-failed"})
            reports[module] = None
        else:
            reports[module] = {row["name"]: row for row in report["functions"]}
    rows, files = [], []
    for item in consumer_files:
        path, source = item["path"], item["source"]
        tree, reason = _parse(source)
        file_record = {"path": path, "source_sha256": content_id(source), "status": "unresolved" if reason else "inspected", "reason": reason}
        files.append(file_record)
        if tree is None:
            continue
        file_record["source_call_nodes"] = sum(isinstance(n, ast.Call) for n in ast.walk(tree))
        file_start = len(rows)
        scope = _Scope(tree.body, _module(path), str(path).endswith("__init__.py"), candidate=candidate)

        def emit(call, current_scope):
            if len(rows) >= MAX_CALLS:
                file_record.update(status="partial", reason="global-call-bound")
                return
            mappings = [_target(call, current_scope, index) for index in (before, after)]
            shape, shape_reason = _shape(call)
            accepts, reasons, evidence = [], [], []
            for version, mapping in zip(("before", "after"), mappings):
                reason = mapping.get("reason")
                module_rows = reports.get(mapping.get("module"))
                declaration = module_rows.get(mapping.get("name")) if module_rows else None
                signature = declaration.get(version + "_signature") if declaration else None
                if reason is None and signature is None:
                    reason = "source-pinned-supported-signature-unavailable"
                if reason is None and declaration.get("status") not in {"call_loss", "no_call_loss"}:
                    reason = "declaration-outside-supported-binding-scope"
                if reason is None and shape_reason:
                    reason = shape_reason
                accepts.append(None if reason else _accepts(signature, shape, mapping["implicit_receiver"]))
                reasons.append(reason)
                evidence.append({"target": mapping, "signature": signature,
                                 "declaration_status": declaration.get("status") if declaration else None,
                                 "warnings": declaration.get("warnings", []) if declaration else []})
            status = "potential_break" if accepts == [True, False] else "preserved_binding" if accepts == [True, True] else "unresolved"
            if accepts[0] is False:
                reasons[0] = "call-already-rejected-by-before-signature"
            rows.append({"consumer_path": path, "line": call.lineno, "end_line": call.end_lineno,
                         "column": call.col_offset, "snippet": ast.get_source_segment(source, call),
                         "source_sha256": file_record["source_sha256"], "status": status,
                         "scope_triage": _triage(call, current_scope, before),
                         "before_accepts": accepts[0], "after_accepts": accepts[1], "call_shape": shape,
                         "before": evidence[0], "after": evidence[1], "unresolved_reasons": reasons,
                         "action": "Review the upgrade or pin decision and run a version-specific integration test." if status == "potential_break" else
                                   "Review unresolved source/dispatch and add a version-specific integration test." if status == "unresolved" else
                                   "Binding is preserved for this call shape; review behavioral changes and integration tests.",
                         "assumptions": ["Captured imports complete successfully with standard import behavior and no runtime monkeypatching.",
                                         "Argument expressions evaluate successfully; only argument binding is assessed.",
                                         "For constructors and super, the direct __init__ is used; __new__, metaclasses, MRO changes and runtime dispatch are outside scope.",
                                         "Deferred function bodies run after their enclosing imports complete."]})
        _Calls(source, scope, emit).visit(tree)
        file_record["inspected_calls"] = len(rows) - file_start
        file_record["unvisited_call_nodes"] = file_record["source_call_nodes"] - file_record["inspected_calls"]
        if file_record["unvisited_call_nodes"]:
            file_record.update(status="partial", reason=file_record["reason"] or "unsupported-scope-or-call-bound")
    counts = Counter(row["status"] for row in rows)
    triage = Counter(row["scope_triage"]["category"] for row in rows)
    return {"schema": SCHEMA, "status": "partial-static-assessment", "files": files, "calls": rows,
            "findings": [row for row in rows if row["status"] == "potential_break"],
            "coverage": {"consumer_files": len(files), "inspected_calls": len(rows),
                         "unvisited_call_nodes": sum(f.get("unvisited_call_nodes", 0) for f in files),
                         "scope_triage": dict(triage),
                         "potential_break": counts["potential_break"], "preserved_binding": counts["preserved_binding"], "unresolved": counts["unresolved"]},
            "producer_errors": {"before": before.errors, "after": after.errors, "reports": report_errors},
            "limits": ["Unresolved calls are not evidence of no impact; only direct source-grounded callable bindings are assessed.",
                       "Wildcards, dynamic exports, shadowed imports, instance methods and nonliteral expansions remain unresolved.",
                       "Input producer paths must be repository-relative Python module paths, not version-prefixed directories.",
                       "Call counts are code sites, not customer jobs or independent missions."],
            "meter": {"wall_ns": time.perf_counter_ns() - start, "cpu_ns": time.process_time_ns() - cpu,
                      "input_bytes": sum(len(s.encode()) for d in (before_files, after_files) for s in d.values()) + sum(len(f["source"].encode()) for f in consumer_files),
                      "source_parses": len(before_files) + len(after_files) + len(consumer_files), "runtime_model_calls": 0, "network_requests": 0, "source_execution": False}}


def assess_consumers(consumer_files, before_files, after_files, producer_reports):
    start, cpu = time.perf_counter_ns(), time.process_time_ns()
    strict = _assess_consumers(consumer_files, before_files, after_files, producer_reports, False)
    candidate = _assess_consumers(consumer_files, before_files, after_files, producer_reports, True)
    unresolved = {(r["consumer_path"], r["line"], r["column"]) for r in strict["calls"] if r["status"] == "unresolved"}
    candidates = [r for r in candidate["calls"] if r["status"] != "unresolved" and (r["consumer_path"], r["line"], r["column"]) in unresolved]
    for row in candidates:
        row["qualification"] = "syntactic-reexport-or-import-guard-candidate-runtime-unproved"
        row["assumptions"].append("Closed literal __all__ sets and recognized __module__ metadata writes describe intended exports; runtime export identity is unproved.")
        row["assumptions"].append("An import-only try block either succeeds or its exception handler raises; no runtime path was executed.")
    strict["syntactic_candidates"] = candidates
    strict["syntactic_candidate_findings"] = [r for r in candidates if r["status"] == "potential_break"]
    strict["candidate_coverage"] = dict(Counter(r["status"] for r in candidates))
    strict["candidate_limits"] = ["Candidate rows do not alter strict findings or strict unresolved counts.",
                                  "Every wildcard import must have captured source and a closed literal __all__; collisions remain unresolved.",
                                  "Candidate source traces require independent runtime/integration validation before an upgrade decision."]
    strict["meter"]["candidate_pass"] = candidate["meter"]
    strict["meter"]["source_parses"] += candidate["meter"]["source_parses"]
    strict["meter"].update(wall_ns=time.perf_counter_ns() - start, cpu_ns=time.process_time_ns() - cpu)
    return strict
