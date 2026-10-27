# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

from conventional import DECL, Extractor, Provider, Ref, Target, imported

BASE_SHA256 = "9abab6a52c56426e27580ad2919a8a29bfab6324f4e31625315f4433aceb0c45"


def import_module(node: ast.ImportFrom, module: str, package: bool) -> str:
    probe = ast.ImportFrom(module=node.module, names=[ast.alias(name="_export_probe")], level=node.level)
    return imported(probe, module, package)["_export_probe"].rsplit(".", 1)[0]


class SourceProvider(Provider):
    def __init__(self, raw: dict[str, Any], side: str, trees: dict[str, ast.Module], roots: tuple[str, ...]):
        super().__init__(raw, side, trees, roots)
        self.side = side
        self.choice_names: dict[str, str] = {}
        self.conditional: set[str] = set()
        self.proven_absent: set[str] = set()
        self.export_cache: dict[str, set[str] | None] = {}

    def register(self, token: str, name: str) -> None:
        self.choice_names[token] = name

    def expand_choice(self, name: str) -> str:
        for token, replacement in self.choice_names.items():
            if name == token or name.startswith(token + "."):
                return replacement + name[len(token):]
        return name

    def exports(self, module: str, seen: frozenset[str] = frozenset()) -> set[str] | None:
        if module in self.export_cache:
            return self.export_cache[module]
        if module not in self.modules or module in seen or module in self.ambiguous:
            return None
        ident, tree = self.modules[module]
        aliases: dict[str, str] = {}
        values: dict[str, list[str] | None] = {}
        public: set[str] = set()
        unknown_star = False
        package = self.raw["sources"][ident]["path"].endswith("/__init__.py")

        def strings(node: ast.AST | None) -> list[str] | None:
            if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                return [n.value for n in node.elts] if all(isinstance(n, ast.Constant) and isinstance(n.value, str) for n in node.elts) else None
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                left, right = strings(node.left), strings(node.right)
                return left + right if left is not None and right is not None else None
            if isinstance(node, ast.Name):
                if node.id in values:
                    return values[node.id]
                target = aliases.get(node.id)
                if target and target.endswith(".__all__"):
                    exported = self.exports(target.rsplit(".", 1)[0], seen | {module})
                    return sorted(exported) if exported is not None else None
            return None

        for node in tree.body:
            if isinstance(node, DECL):
                public.add(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                mapping = imported(node, module, package)
                aliases.update(mapping)
                public.update(mapping)
                if isinstance(node, ast.ImportFrom) and any(n.name == "*" for n in node.names):
                    names = self.exports(import_module(node, module, package), seen | {module})
                    if names is None:
                        unknown_star = True
                    else:
                        public.update(names)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                    if isinstance(target, ast.Name):
                        public.add(target.id)
                        values[target.id] = strings(node.value)
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
                addition = strings(node.value)
                values[name] = values.get(name, []) + addition if isinstance(node.op, ast.Add) and values.get(name) is not None and addition is not None else None
        result = set(values["__all__"]) if values.get("__all__") is not None else (
            None if "__all__" in values or unknown_star else {n for n in public if not n.startswith("_")})
        self.export_cache[module] = result
        return result

    def _definition(self, ident: str, node: ast.AST, first: str, tail: str) -> Target | None:
        symbol, decorated = first, bool(node.decorator_list)
        for part in tail.split(".") if tail else []:
            if not isinstance(node, ast.ClassDef) or node.keywords or len(node.bases) > 1:
                return None
            matches = [n for n in node.body if isinstance(n, DECL) and n.name == part]
            if len(matches) != 1:
                return None
            node = matches[0]
            symbol += "." + part
            decorated |= bool(node.decorator_list)
        return Target(ident, symbol, "class" if isinstance(node, ast.ClassDef) else "function", decorated)

    def _exact(self, name: str, seen: frozenset[str]) -> Target | None:
        candidates: set[Target] = set()
        for module in sorted((m for m in self.modules if name.startswith(m + ".")), key=len, reverse=True):
            if module in self.ambiguous:
                continue
            ident, tree = self.modules[module]
            first, _, tail = name[len(module) + 1:].partition(".")
            package = self.raw["sources"][ident]["path"].endswith("/__init__.py")
            uncertain = False
            definitions = [n for n in tree.body if isinstance(n, DECL) and n.name == first]
            if len(definitions) > 1:
                self.proven_absent.add(name)
                return None
            for node in tree.body:
                target = None
                if isinstance(node, DECL) and node.name == first:
                    target = self._definition(ident, node, first, tail)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    mapping = imported(node, module, package)
                    if first in mapping:
                        target = self.resolve(mapping[first] + ("." + tail if tail else ""), seen | {name})
                    elif isinstance(node, ast.ImportFrom) and any(n.name == "*" for n in node.names):
                        origin = import_module(node, module, package)
                        exported = self.exports(origin)
                        if exported is None:
                            uncertain = True
                        elif first in exported:
                            target = self.resolve(origin + "." + first + ("." + tail if tail else ""), seen | {name})
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    for dest in node.targets if isinstance(node, ast.Assign) else [node.target]:
                        if isinstance(dest, ast.Name) and dest.id == first:
                            if isinstance(node.value, ast.Name):
                                target = self.resolve(module + "." + node.value.id + ("." + tail if tail else ""), seen | {name})
                            elif isinstance(node.value, ast.Attribute):
                                expr = ast.unparse(node.value)
                                target = self.resolve(module + "." + expr + ("." + tail if tail else ""), seen | {name})
                            else:
                                uncertain = True
                if target is not None:
                    candidates.add(target)
            if len(candidates) == 1 and not uncertain:
                return next(iter(candidates))
            if len(candidates) > 1:
                return None
            dynamic = any(isinstance(n, (ast.If, ast.Try, ast.TryStar, ast.For, ast.While, ast.With, ast.Match))
                          or isinstance(n, DECL) and n.name == '__getattr__'
                          or isinstance(n, ast.Expr) and not isinstance(n.value, ast.Constant)
                          for n in tree.body)
            if not candidates and not uncertain and not dynamic:
                self.proven_absent.add(name)
                return None
        return None

    def _unique(self, name: str) -> Target | None:
        candidates: set[Target] = set()
        invalid = False
        for module, (ident, tree) in self.modules.items():
            if module in self.ambiguous or not any(module == r or module.startswith(r + ".") for r in self.roots):
                continue
            def walk(nodes: list[ast.stmt], prefix: str = "", decorated: bool = False) -> None:
                nonlocal invalid
                names = [n.name for n in nodes if isinstance(n, DECL)]
                for node in nodes:
                    if not isinstance(node, DECL):
                        continue
                    symbol = prefix + node.name
                    if name.endswith("." + symbol):
                        if names.count(node.name) != 1:
                            invalid = True
                            continue
                        candidates.add(Target(ident, symbol, "class" if isinstance(node, ast.ClassDef) else "function", decorated or bool(node.decorator_list)))
                    if isinstance(node, ast.ClassDef) and not node.keywords and len(node.bases) <= 1:
                        walk(node.body, symbol + ".", decorated or bool(node.decorator_list))
            walk(tree.body)
        return next(iter(candidates)) if len(candidates) == 1 and not invalid else None

    def resolve(self, name: str, seen: frozenset[str] = frozenset()) -> Target | None:
        name = self.expand_choice(name)
        if name in self.cache:
            return self.cache[name]
        if not name or name in seen or len(seen) > 24:
            return None
        target = self._exact(name, seen)
        if target is None and name not in self.proven_absent:
            target = self._unique(name)
            if target is not None:
                self.conditional.add(name)
        self.cache[name] = target
        return target

    def available_import(self, node: ast.Import | ast.ImportFrom) -> bool | None:
        if isinstance(node, ast.Import):
            relevant = [n.name for n in node.names if any(n.name == r or n.name.startswith(r + ".") for r in self.roots)]
            if not relevant:
                return None
            return all(any(m == n or m.startswith(n + ".") for m in self.modules) for n in relevant)
        if node.level or node.module is None or any(n.name == "*" for n in node.names):
            return None
        if not any(node.module == r or node.module.startswith(r + ".") for r in self.roots):
            return None
        resolved = [self.resolve(node.module + "." + n.name) for n in node.names]
        if all(t is not None for t in resolved):
            return True
        names = [node.module + "." + n.name for n in node.names]
        if any(self._unique(name) is None for name in names):
            return False
        return None


class ExtractorV2(Extractor):
    def __init__(self, raw: dict[str, Any]):
        base = Path(__file__).with_name("conventional.py")
        if hashlib.sha256(base.read_bytes()).hexdigest() != BASE_SHA256:
            raise ValueError("frozen conventional base identity changed")
        super().__init__(raw)
        self.providers = {side: SourceProvider(raw, side, self.trees, self.roots) for side in ("before", "after")}
        self.choice_count = 0

    def import_branch(self, node: ast.Try, env: dict[str, Ref]) -> bool:
        if not node.body or not all(isinstance(n, (ast.Import, ast.ImportFrom)) for n in node.body):
            return False
        if node.orelse or node.finalbody or len(node.handlers) != 1:
            return False
        handler = node.handlers[0]
        names = ([handler.type.id] if isinstance(handler.type, ast.Name) else
                 [n.id for n in handler.type.elts if isinstance(n, ast.Name)] if isinstance(handler.type, ast.Tuple) else [])
        if not names or any(n not in {"ImportError", "ModuleNotFoundError"} for n in names):
            return False
        if not handler.body or not all(isinstance(n, (ast.Import, ast.ImportFrom)) for n in handler.body):
            return False
        mappings = {}
        for side, provider in self.providers.items():
            availability = [provider.available_import(n) for n in node.body]
            if any(v is None for v in availability):
                return False
            chosen = node.body if all(availability) else handler.body
            values = {}
            for statement in chosen:
                values.update(imported(statement))
            mappings[side] = values
        locals_ = set(mappings["before"]) | set(mappings["after"])
        for local in locals_:
            names_by_side = {side: mappings[side].get(local) for side in ("before", "after")}
            if not all(names_by_side.values()):
                env[local] = Ref(dependent=True, uncertain="import fallback lacks a common local binding")
                continue
            if names_by_side["before"] == names_by_side["after"]:
                name = names_by_side["before"]
                env[local] = Ref(name, self.dependent(name))
                continue
            token = "@captured-import-" + str(self.choice_count)
            self.choice_count += 1
            for side, provider in self.providers.items():
                provider.register(token, names_by_side[side])
            env[local] = Ref(token, any(self.dependent(n) for n in names_by_side.values()))
        return True

    def body(self, nodes: list[ast.stmt], env: dict[str, Ref], scope: str = "", cls: str | None = None) -> None:
        for node in nodes:
            if isinstance(node, ast.Try) and self.import_branch(node, env):
                continue
            super().body([node], env, scope, cls)

    def run(self) -> dict[str, Any]:
        result = super().run()
        for claim in result["claims"]:
            claim["explanation"] = (
                "Conventional static source mapping, including explicit exports and source-backed unique-target hypotheses. "
                "Import availability, fallback selection and receiver dispatch are conditional on the captured sources and "
                "standard import behavior; runtime identity is unproved unless the unchanged downstream verifier proves it. "
                "Inspected dependency source was not executed."
            )
        result["provenance"] = {
            "mode": "conventional-static-v2",
            "baseSha256": BASE_SHA256,
            "targetPolicy": "Unique source-backed declared targets are hypotheses; ambiguity stays unresolved.",
        }
        return result


def extract(raw: dict[str, Any]) -> dict[str, Any]:
    return ExtractorV2(raw).run()


if __name__ == "__main__":
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

