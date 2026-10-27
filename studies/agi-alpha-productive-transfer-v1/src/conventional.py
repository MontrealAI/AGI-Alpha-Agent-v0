# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

RAW_SCHEMA = "alpha-transfer-raw-task/v1"
OUT_SCHEMA = "alpha-transfer-extraction/v1"
FUNC = (ast.FunctionDef, ast.AsyncFunctionDef)
DECL = (*FUNC, ast.ClassDef)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


@dataclass(frozen=True)
class Ref:
    name: str = ""
    dependent: bool = False
    instance: bool = False
    uncertain: str = ""


@dataclass(frozen=True)
class Target:
    source: str
    symbol: str
    kind: str
    decorated: bool = False


def module_name(path: str, roots: tuple[str, ...]) -> str:
    parts = path[:-3].split("/")
    if parts[-1] == "__init__":
        parts.pop()
    if parts and parts[0] == "src":
        parts.pop(0)
    for i in range(len(parts)):
        dotted = ".".join(parts[i:])
        if any(dotted == root or dotted.startswith(root + ".") for root in roots):
            return dotted
    return ".".join(parts)


def dotted(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted(node.value)
        return prefix + "." + node.attr if prefix else None
    return None


def terminates(nodes: list[ast.stmt]) -> bool:
    if not nodes:
        return False
    last = nodes[-1]
    if isinstance(last, (ast.Raise, ast.Return)):
        return True
    return isinstance(last, ast.If) and terminates(last.body) and terminates(last.orelse)


def imported(node: ast.Import | ast.ImportFrom, module: str = "", package: bool = False) -> dict[str, str]:
    result = {}
    if isinstance(node, ast.Import):
        for item in node.names:
            result[item.asname or item.name.split(".")[0]] = item.name if item.asname else item.name.split(".")[0]
    else:
        parent = module.split(".") if package else module.split(".")[:-1]
        if node.level:
            keep = len(parent) - node.level + 1
            prefix = ".".join(parent[:max(0, keep)])
            base = ".".join(p for p in (prefix, node.module or "") if p)
        else:
            base = node.module or ""
        for item in node.names:
            if item.name != "*":
                result[item.asname or item.name] = ".".join(p for p in (base, item.name) if p)
    return result


class Provider:
    def __init__(self, raw: dict[str, Any], side: str, trees: dict[str, ast.Module], roots: tuple[str, ...]):
        self.modules: dict[str, tuple[str, ast.Module]] = {}
        self.ambiguous: set[str] = set()
        self.cache: dict[str, Target | None] = {}
        self.raw, self.roots = raw, roots
        for ident in raw["providerSides"][side]:
            source = raw["sources"][ident]
            mod = module_name(source["path"], roots)
            if mod in self.modules:
                self.ambiguous.add(mod)
            self.modules[mod] = ident, trees[ident]

    def resolve(self, name: str, seen: frozenset[str] = frozenset()) -> Target | None:
        if name in self.cache:
            return self.cache[name]
        if name in seen or len(seen) > 24:
            return None
        candidates = sorted((m for m in self.modules if name.startswith(m + ".")), key=len, reverse=True)
        for mod in candidates:
            if mod in self.ambiguous:
                continue
            ident, tree = self.modules[mod]
            remainder = name[len(mod) + 1:]
            first, _, tail = remainder.partition(".")
            bindings: list[tuple[str, Any]] = []
            for node in tree.body:
                if isinstance(node, DECL) and node.name == first:
                    bindings.append(("definition", node))
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    mapping = imported(node, mod, self.raw["sources"][ident]["path"].endswith("/__init__.py"))
                    if first in mapping:
                        bindings.append(("alias", mapping[first]))
                    if isinstance(node, ast.ImportFrom) and any(n.name == "*" for n in node.names):
                        bindings.append(("unknown", None))
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    if any(isinstance(t, ast.Name) and t.id == first for t in targets):
                        value = dotted(node.value) if node.value is not None else None
                        bindings.append(("local", value))
            if len(bindings) != 1:
                continue
            kind, value = bindings[0]
            target = None
            if kind == "alias":
                target = self.resolve(value + ("." + tail if tail else ""), seen | {name})
            elif kind == "local" and value:
                target = self.resolve(mod + "." + value + ("." + tail if tail else ""), seen | {name})
            elif kind == "definition":
                node, symbol, decorated = value, first, bool(value.decorator_list)
                if tail:
                    for part in tail.split("."):
                        if not isinstance(node, ast.ClassDef) or node.keywords or len(node.bases) > 1:
                            node = None
                            break
                        matches = [n for n in node.body if isinstance(n, DECL) and n.name == part]
                        if len(matches) != 1:
                            node = None
                            break
                        node = matches[0]
                        symbol += "." + part
                        decorated |= bool(node.decorator_list)
                if node is not None:
                    target = Target(ident, symbol, "class" if isinstance(node, ast.ClassDef) else "function", decorated)
            if target is not None:
                self.cache[name] = target
                return target
        self.cache[name] = None
        return None

    def declaration(self, ref: Ref) -> Target | None:
        target = self.resolve(ref.name)
        if target and target.kind == "class":
            return self.resolve(ref.name + ".__init__")
        return target


class Extractor:
    def __init__(self, raw: dict[str, Any]):
        if raw.get("schema") != RAW_SCHEMA:
            raise ValueError("unsupported raw task schema")
        self.raw = raw
        self.roots = tuple(raw["dependency"]["importRoots"])
        if not self.roots or not all(isinstance(r, str) and r for r in self.roots):
            raise ValueError("dependency import roots required")
        self.trees: dict[str, ast.Module] = {}
        for ident, source in raw["sources"].items():
            text = source["text"]
            if hashlib.sha256(text.encode()).hexdigest() != source["sha256"]:
                raise ValueError("captured source digest mismatch")
            if len(text.encode()) > 250000:
                raise ValueError("source exceeds parse bound")
            tree = ast.parse(text)
            if sum(1 for _ in ast.walk(tree)) > 35000:
                raise ValueError("source exceeds AST bound")
            self.trees[ident] = tree
        self.consumer = self.trees[raw["consumer"]["source"]]
        self.providers = {s: Provider(raw, s, self.trees, self.roots) for s in ("before", "after")}
        self.scopes = tuple(raw["consumer"]["scopeSymbols"])
        self.calls: dict[tuple[int, int], tuple[ast.Call, Ref]] = {}
        self.matched: set[str] = set()
        self.classes: dict[str, tuple[ast.ClassDef, list[Ref], dict[str, Ref]]] = {}

    def dependent(self, name: str) -> bool:
        return any(name == root or name.startswith(root + ".") for root in self.roots)

    def wanted(self, scope: str) -> bool:
        return any(scope == s or scope.startswith(s + ".") for s in self.scopes)

    def traversed(self, scope: str) -> bool:
        return self.wanted(scope) or any(s.startswith(scope + ".") for s in self.scopes)

    def ref(self, node: ast.AST | None, env: dict[str, Ref], cls: str | None) -> Ref:
        if isinstance(node, ast.Name):
            return env.get(node.id, Ref())
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id in {"self", "cls"} and cls in self.classes:
                attrs = self.classes[cls][2]
                if node.attr in attrs:
                    return attrs[node.attr]
                bases = self.classes[cls][1]
                if len(bases) == 1 and bases[0].dependent:
                    base = bases[0]
                    return replace(base, name=base.name + "." + node.attr, instance=True,
                                   uncertain=base.uncertain or "inherited receiver dispatch is conditional")
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "super":
                if cls in self.classes:
                    bases = self.classes[cls][1]
                    if len(bases) == 1 and bases[0].dependent:
                        reason = "" if not node.value.args and not node.value.keywords and node.attr == "__init__" else "unsupported super dispatch"
                        return replace(bases[0], name=bases[0].name + "." + node.attr, instance=True, uncertain=bases[0].uncertain or reason)
                return Ref(dependent=True, uncertain="superclass target is not one captured dependency base")
            base = self.ref(node.value, env, cls)
            return replace(base, name=base.name + "." + node.attr if base.name else "")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "getattr":
                base = self.ref(node.args[0], env, cls) if node.args else Ref()
                return Ref(dependent=base.dependent, uncertain="dynamic getattr dispatch")
            base = self.ref(node.func, env, cls)
            kinds = [p.resolve(base.name) for p in self.providers.values()] if base.name else []
            if kinds and all(t is not None and t.kind == "class" and not t.decorated for t in kinds):
                return replace(base, instance=True)
            return Ref(dependent=base.dependent, uncertain="return type of dependency call is unknown" if base.dependent else "")
        if isinstance(node, (ast.Subscript, ast.Await)):
            value = self.ref(node.value, env, cls)
            return Ref(dependent=value.dependent, uncertain="dynamic dependency value" if value.dependent else "")
        if node is not None:
            refs = [self.ref(n, env, cls) for n in ast.iter_child_nodes(node) if isinstance(n, ast.expr)]
            if any(r.dependent for r in refs):
                return Ref(dependent=True, uncertain="ambiguous dependency expression")
        return Ref()

    def expressions(self, node: ast.AST | None, env: dict[str, Ref], scope: str, cls: str | None) -> None:
        if node is None:
            return
        if isinstance(node, ast.Lambda):
            local = env.copy()
            for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs, node.args.vararg, node.args.kwarg]:
                if arg:
                    local[arg.arg] = Ref()
            self.expressions(node.body, local, scope, cls)
            return
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            local = env.copy()
            for generator in node.generators:
                self.expressions(generator.iter, local, scope, cls)
                value = self.ref(generator.iter, local, cls)
                self.assign(generator.target, Ref(dependent=value.dependent, uncertain="comprehension element has unknown identity"), local, cls)
                for condition in generator.ifs:
                    self.expressions(condition, local, scope, cls)
            if isinstance(node, ast.DictComp):
                self.expressions(node.key, local, scope, cls)
                self.expressions(node.value, local, scope, cls)
            else:
                self.expressions(node.elt, local, scope, cls)
            return
        if isinstance(node, ast.Call) and self.wanted(scope):
            ref = self.ref(node.func, env, cls)
            if ref.dependent:
                self.calls[(node.lineno, node.col_offset)] = node, ref
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                continue
            self.expressions(child, env, scope, cls)

    def local_bindings(self, node: ast.AST, inherited: dict[str, Ref]) -> dict[str, Ref]:
        found: dict[str, Ref] = {}
        globals_: set[str] = set()
        def visit(item: ast.AST) -> None:
            if isinstance(item, (ast.Global, ast.Nonlocal)):
                globals_.update(item.names)
                return
            if isinstance(item, DECL):
                found[item.name] = Ref()
                return
            if isinstance(item, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                return
            if isinstance(item, ast.Name) and isinstance(item.ctx, (ast.Store, ast.Del)):
                old = inherited.get(item.id, Ref())
                found[item.id] = Ref(dependent=old.dependent, uncertain="local binding not yet established")
            if isinstance(item, (ast.Import, ast.ImportFrom)):
                for local, full in imported(item).items():
                    found[local] = Ref(dependent=self.dependent(full), uncertain="local import not yet established")
            for child in ast.iter_child_nodes(item):
                visit(child)
        for statement in node.body:
            visit(statement)
        return {name: value for name, value in found.items() if name not in globals_}

    def assign(self, node: ast.AST, value: Ref, env: dict[str, Ref], cls: str | None) -> None:
        if isinstance(node, ast.Name):
            env[node.id] = value
        elif isinstance(node, (ast.Tuple, ast.List)):
            for part in node.elts:
                self.assign(part, Ref(dependent=value.dependent, uncertain="unpacked dependency value" if value.dependent else ""), env, cls)
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id in {"self", "cls"} and cls in self.classes:
                self.classes[cls][2][node.attr] = value
            else:
                root = node
                while isinstance(root, (ast.Attribute, ast.Subscript)):
                    root = root.value
                if isinstance(root, ast.Name) and env.get(root.id, Ref()).dependent:
                    env[root.id] = replace(env[root.id], uncertain="dependency object is mutated")

    def merge(self, original: dict[str, Ref], branches: list[dict[str, Ref]]) -> None:
        for key in set().union(*(set(b) for b in branches)):
            values = [b.get(key, Ref()) for b in branches]
            original[key] = values[0] if all(v == values[0] for v in values) else Ref(
                dependent=any(v.dependent for v in values), uncertain="control-flow dependent binding")

    def body(self, nodes: list[ast.stmt], env: dict[str, Ref], scope: str = "", cls: str | None = None) -> None:
        for node in nodes:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for local, full in imported(node).items():
                    env[local] = Ref(full, self.dependent(full))
                continue
            if isinstance(node, FUNC):
                sub = ".".join(p for p in (scope, node.name) if p)
                if sub in self.scopes:
                    self.matched.add(sub)
                if self.traversed(sub):
                    local = env.copy()
                    local.update(self.local_bindings(node, env))
                    for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs, node.args.vararg, node.args.kwarg]:
                        if arg:
                            annotation = self.ref(arg.annotation, env, cls)
                            local[arg.arg] = Ref(dependent=annotation.dependent, uncertain="annotated receiver lacks runtime identity" if annotation.dependent else "")
                    self.body(node.body, local, sub, cls)
                env[node.name] = Ref()
                continue
            if isinstance(node, ast.ClassDef):
                sub = ".".join(p for p in (scope, node.name) if p)
                if sub in self.scopes:
                    self.matched.add(sub)
                bases = [self.ref(n, env, cls) for n in node.bases]
                if node.decorator_list or node.keywords:
                    bases = [replace(b, uncertain="decorated or metaclass consumer") for b in bases]
                self.classes[sub] = node, bases, {}
                if self.traversed(sub):
                    self.body(node.body, env.copy(), sub, sub)
                env[node.name] = Ref()
                continue
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                self.expressions(node.value, env, scope, cls)
                value = self.ref(node.value, env, cls)
                for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                    self.assign(target, value, env, cls)
                continue
            if isinstance(node, ast.AugAssign):
                self.expressions(node.value, env, scope, cls)
                value = self.ref(node.target, env, cls)
                self.assign(node.target, replace(value, uncertain="augmented dependency assignment"), env, cls)
                continue
            if isinstance(node, ast.If):
                self.expressions(node.test, env, scope, cls)
                left, right = env.copy(), env.copy()
                self.body(node.body, left, scope, cls)
                self.body(node.orelse, right, scope, cls)
                surviving = [branch for branch, block in ((left, node.body), (right, node.orelse)) if not terminates(block)]
                if surviving:
                    self.merge(env, surviving)
                continue
            if isinstance(node, ast.Match):
                self.expressions(node.subject, env, scope, cls)
                branches = [env.copy()]
                for case in node.cases:
                    branch = env.copy()
                    for part in ast.walk(case.pattern):
                        if isinstance(part, (ast.MatchAs, ast.MatchStar)) and part.name:
                            branch[part.name] = Ref()
                        if isinstance(part, ast.MatchMapping) and part.rest:
                            branch[part.rest] = Ref()
                    self.expressions(case.guard, branch, scope, cls)
                    self.body(case.body, branch, scope, cls)
                    branches.append(branch)
                self.merge(env, branches)
                continue
            if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
                self.expressions(node.iter if isinstance(node, (ast.For, ast.AsyncFor)) else node.test, env, scope, cls)
                local = env.copy()
                if isinstance(node, (ast.For, ast.AsyncFor)):
                    self.assign(node.target, Ref(), local, cls)
                self.body(node.body, local, scope, cls)
                self.merge(env, [env.copy(), local])
                self.body(node.orelse, env, scope, cls)
                continue
            if isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    self.expressions(item.context_expr, env, scope, cls)
                    if item.optional_vars:
                        ref = self.ref(item.context_expr, env, cls)
                        self.assign(item.optional_vars, Ref(dependent=ref.dependent, uncertain="context-manager receiver needs runtime identity"), env, cls)
                self.body(node.body, env, scope, cls)
                continue
            if isinstance(node, (ast.Try, ast.TryStar)):
                branches = [env.copy()]
                self.body(node.body, branches[0], scope, cls)
                self.body(node.orelse, branches[0], scope, cls)
                for handler in node.handlers:
                    branch = env.copy()
                    if handler.name:
                        branch[handler.name] = Ref()
                    self.body(handler.body, branch, scope, cls)
                    if not terminates(handler.body):
                        branches.append(branch)
                self.merge(env, branches)
                self.body(node.finalbody, env, scope, cls)
                continue
            self.expressions(node, env, scope, cls)

    def run(self) -> dict[str, Any]:
        globals_: dict[str, Ref] = {}
        scopes, self.scopes = self.scopes, ()
        self.body(self.consumer.body, globals_)
        self.scopes = scopes
        for node in self.consumer.body:
            if isinstance(node, DECL):
                self.body([node], globals_.copy())
        if set(self.scopes) - self.matched:
            raise ValueError("selected consumer scope is absent")
        if len(self.calls) > 24:
            raise ValueError("dependency-relevant call count exceeds bound")
        claims, unresolved = [], []
        for _, (call, ref) in sorted(self.calls.items()):
            location = {"line": call.lineno, "column": call.col_offset, "callee": ast.unparse(call.func)}
            reason = ref.uncertain
            if any(isinstance(a, ast.Starred) for a in call.args) or any(k.arg is None for k in call.keywords):
                reason = "expanded arguments require runtime verification"
            targets = {side: p.declaration(ref) for side, p in self.providers.items()}
            if not reason and any(t is None for t in targets.values()):
                reason = "target is absent or ambiguous in captured provider declarations"
            if not reason and any(t.decorated for t in targets.values() if t):
                reason = "decorated declaration requires runtime verification"
            if reason:
                unresolved.append({**location, "reason": reason})
                continue
            explanation = "Static import and assignment resolution to captured declarations; no inspected source executed."
            if any("." in t.symbol for t in targets.values() if t):
                explanation += " Constructor or receiver mapping remains conditional on downstream dispatch verification."
            claims.append({**location, **{side: {"source": t.source, "symbol": t.symbol} for side, t in targets.items()},
                           "explanation": explanation})
        return {"schema": OUT_SCHEMA, "inputSha256": hashlib.sha256(canonical(self.raw)).hexdigest(),
                "claims": claims, "unresolved": unresolved, "provenance": {"mode": "conventional-static"}}


def extract(raw: dict[str, Any]) -> dict[str, Any]:
    return Extractor(raw).run()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output", nargs="?")
    args = parser.parse_args()
    result = extract(json.loads(Path(args.input).read_text()))
    rendered = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        Path(args.output).write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()

