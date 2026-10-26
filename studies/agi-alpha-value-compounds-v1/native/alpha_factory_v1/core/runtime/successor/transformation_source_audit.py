# SPDX-License-Identifier: Apache-2.0
"""Bounded static source-package audit discovery, separate from native TI v1.

Only supplied UTF-8 Python text is parsed, never imported or executed. Git hashes
commit supplied bytes; remote provenance and permission remain operator claims.
Screening is syntactic and conservative, not proof of arbitrary runtime values;
the operator remains responsible for public, non-personal source classification.
The six program choices execute different algorithms. Evaluator revision is a
separate signed MeasurementLedger operation, never an optimizer action.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import itertools
import os
import re
import stat
import uuid
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from ..store import Conflict, Journal
from .measurement import KEY as MEASUREMENT_KEY
from .measurement import EvaluationInstrument, MeasurementLedger
from .protocol import Digest, StrictModel, canonical, digest
from .trust import SignedEnvelope
from .transformation import _engine_digest, assert_public_content

SCHEMA = "ti-source-package-audit/v1"
KEY = "@ti-source-audit:"
EXPOSURES = KEY + "exposures:v2"
MAX_EXPOSURES = 512
MAX_BLOB_EXPOSURES = 4096
MAX_SOURCE_AST_NODES = 12_000
AXES = ("indexed", "query_once", "dependency_queue", "fragments", "package_batch", "checked_handoff")
CATEGORIES = ("construction", "read", "query", "dependency", "production", "coordination", "check", "search")
COST_RULE = {
    "schema": "source-audit-logical-cost/v1",
    "read": "one per started64UTF8bytes per fact parse plus every explicit fact-parser AST-node visit",
    "construction": (
        "one per fact-bucket materialization/retention, import/symbol insertion attempt, "
        "captured-submodule membership and index entry"
    ),
    "query": "one per index lookup or examined sequential fact",
    "dependency": (
        "one per graph vertex/edge examination, membership test, set insertion/removal attempt and queue push/pop"
    ),
    "production": "one per canonical fragment byte and emitted report byte",
    "coordination": "one per job/proposal/CAS plus field-check bytes",
    "check": "reference parsing/closure work and compared report bytes",
    "search": "one per candidate and selection/comparator inspection",
    "excluded": [
        "Python allocation/CPU instructions",
        "schema validation/hashing/runtime binding",
        "journal signing/I/O",
        "human review",
        "energy",
        "money",
    ],
}


def _empty_source_value(value: ast.AST | None) -> bool:
    """Recognize the existing syntactically empty assignment placeholders."""
    return (
        value is None
        or (isinstance(value, ast.Constant) and value.value in (None, ""))
        or (
            isinstance(value, (ast.List, ast.Tuple, ast.Dict))
            and not getattr(value, "elts", getattr(value, "keys", []))
        )
    )


def _source_selector_names(selector: ast.AST) -> tuple[list[str], bool]:
    """Collect visible spellings and flag unresolved syntax without evaluation."""
    pending = [selector]
    names: list[str] = []
    unresolved = False
    index = 0
    while index < len(pending):
        if index >= MAX_SOURCE_AST_NODES:
            raise ValueError("source selector exceeds node bound")
        node = pending[index]
        index += 1
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
            pending.append(node.value)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                names.append(node.value)
            elif type(node.value) not in (type(None), bool, int, float, complex):
                unresolved = True
        elif isinstance(node, (ast.Tuple, ast.List)):
            pending.extend(node.elts)
        elif isinstance(node, ast.Slice):
            pending.extend(part for part in (node.lower, node.upper, node.step) if part is not None)
        else:
            unresolved = True
    return names, unresolved


def _selector_bindings(selector: ast.AST, value: ast.AST | None) -> Iterator[tuple[str, ast.AST | None]]:
    """Screen static selector spellings and refuse populated unresolved forms."""
    names, unresolved = _source_selector_names(selector)
    for name in names:
        yield name, value
    if unresolved and not _empty_source_value(value):
        raise ValueError("public-only source contains an unsupported populated key or selector")


def _literal_source_unpack(value: ast.AST) -> None:
    """Require explicit dictionary entries, checked by the enclosing AST walk."""
    if not isinstance(value, ast.Dict):
        raise ValueError("public-only source requires literal dictionary unpacking")


def _assignment_bindings(
    target: ast.AST, value: ast.AST | None, *, include_receivers: bool = False
) -> Iterator[tuple[str, ast.AST | None]]:
    """Find bounded write targets, optionally including visible receiver spellings."""
    pending = [(target, value, False)]
    visited = 0
    while pending:
        target, value, selector = pending.pop()
        visited += 1
        if visited > MAX_SOURCE_AST_NODES:
            raise ValueError("source assignment targets exceed node bound")
        if selector:
            yield from _selector_bindings(target, value)
        elif isinstance(target, ast.Name):
            yield target.id, value
        elif isinstance(target, ast.Attribute):
            yield target.attr, value
            if include_receivers:
                pending.append((target.value, value, False))
        elif isinstance(target, ast.Subscript):
            pending.append((target.slice, value, True))
            pending.append((target.value, value, False))
        elif isinstance(target, ast.Starred):
            pending.append((target.value, value, False))
        elif isinstance(target, (ast.Tuple, ast.List)):
            matching = (
                isinstance(value, (ast.Tuple, ast.List))
                and len(value.elts) == len(target.elts)
                and not any(isinstance(item, ast.Starred) for item in (*target.elts, *value.elts))
            )
            for index in range(len(target.elts) - 1, -1, -1):
                assigned = value.elts[index] if matching and isinstance(value, (ast.Tuple, ast.List)) else value
                pending.append((target.elts[index], assigned, False))


def _screen_source_assignments(
    source: str | bytes, depth: int = 0, *, _literal_budget: list[int] | None = None
) -> None:
    """Inspect populated Python credential keys/assignments without evaluating them."""
    budget = _literal_budget if _literal_budget is not None else [1_000_000]

    def literal_size(value: str | bytes) -> int:
        # Surrogate handling is size accounting only; the parser sees the original.
        return len(value) if isinstance(value, bytes) else len(value.encode("utf-8", "surrogatepass"))

    def consume(size: int) -> None:
        if size > 65_536 or size > budget[0]:
            raise ValueError("source literal screening exceeds its byte/work bound")
        budget[0] -= size

    consume(literal_size(source))
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("source must be bounded parseable Python") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_SOURCE_AST_NODES:
        raise ValueError("source AST exceeds node bound")
    if depth > 4:
        raise ValueError("source literal nesting exceeds public-content boundary")

    def inspect(name: str, value: ast.AST | None) -> None:
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        credential = key.endswith("token") or any(
            marker in key
            for marker in (
                "apikey",
                "password",
                "passwd",
                "privatekey",
                "seedphrase",
                "mnemonic",
                "passphrase",
                "authorization",
                "clientsecret",
                "signingkey",
                "secret",
                "credential",
            )
        )
        if credential and not _empty_source_value(value):
            raise ValueError("public-only source contains a populated credential-shaped assignment or key")

    def inspect_literal_pairs(argument: ast.AST) -> bool:
        """Screen explicit pair tables when constructors or iteration consume them."""
        if not isinstance(argument, (ast.List, ast.Tuple)) or any(
            not isinstance(pair, (ast.List, ast.Tuple)) or len(pair.elts) != 2 for pair in argument.elts
        ):
            return False
        for pair in argument.elts:
            assert isinstance(pair, (ast.List, ast.Tuple))
            for name, assigned_value in _selector_bindings(pair.elts[0], pair.elts[1]):
                inspect(name, assigned_value)
        return True

    iterable_seen: set[ast.AST] = set()

    def literal_sequence(argument: ast.AST) -> list[ast.expr] | None:
        reverse = False
        for _ in range(MAX_SOURCE_AST_NODES):
            if not isinstance(argument, ast.Call) or len(argument.args) != 1 or argument.keywords:
                break
            adapter = argument.func.id if isinstance(argument.func, ast.Name) else None
            if adapter not in {"iter", "list", "tuple", "reversed"}:
                break
            reverse ^= adapter == "reversed"
            argument = argument.args[0]
        else:
            raise ValueError("source iterable adapters exceed their node bound")
        if isinstance(argument, (ast.List, ast.Tuple)):
            return list(reversed(argument.elts)) if reverse else argument.elts
        return None

    def inspect_iterable_pairs(argument: ast.AST) -> None:
        """Screen visible literal pair data through wrappers without calling them."""
        pending = [argument]
        while pending:
            candidate = pending.pop()
            if candidate in iterable_seen:
                continue
            iterable_seen.add(candidate)
            if len(iterable_seen) > MAX_SOURCE_AST_NODES:
                raise ValueError("source iterable inspection exceeds its node bound")
            inspect_literal_pairs(candidate)
            if (
                isinstance(candidate, ast.Call)
                and isinstance(candidate.func, ast.Name)
                and candidate.func.id == "zip"
                and len(candidate.args) == 2
            ):
                selectors, values = (literal_sequence(item) for item in candidate.args)
                if selectors is not None and values is not None:
                    for selector, assigned in zip(selectors, values):
                        for name, assigned_value in _selector_bindings(selector, assigned):
                            inspect(name, assigned_value)
            pending.extend(ast.iter_child_nodes(candidate))

    literals: dict[ast.AST, str | bytes] = {}
    sizes: dict[ast.AST, int] = {}
    comprehension_inputs: set[ast.AST] = set()
    for literal in reversed(nodes):
        if isinstance(literal, (ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp)) or any(
            child in comprehension_inputs for child in ast.iter_child_nodes(literal)
        ):
            comprehension_inputs.add(literal)
        fold_value: str | bytes | None = None
        if isinstance(literal, ast.Constant) and isinstance(literal.value, (str, bytes)):
            fold_value = literal.value
        elif isinstance(literal, ast.BinOp):
            left, right = literals.get(literal.left), literals.get(literal.right)
            if isinstance(literal.op, ast.Mod) and left is not None:
                raise ValueError("public-only source refuses unsupported closed literal formatting")
            if isinstance(literal.op, ast.Add) and left is not None and right is not None:
                consume(sizes[literal.left] + sizes[literal.right])
                if isinstance(left, str) and isinstance(right, str):
                    fold_value = left + right
                elif isinstance(left, bytes) and isinstance(right, bytes):
                    fold_value = left + right
            elif isinstance(literal.op, ast.Mult):
                operand, count = (literal.left, literal.right) if left is not None else (literal.right, literal.left)
                repeated = literals.get(operand)
                if repeated is not None and isinstance(count, ast.Constant):
                    if type(count.value) not in (int,):
                        raise ValueError("source static literal repetition requires an exact integer")
                    assert isinstance(count.value, int)
                    if not 0 <= count.value <= 65_536:
                        raise ValueError("source literal repetition exceeds its bound")
                    consume(sizes[operand] * count.value)
                    fold_value = repeated * count.value
        elif isinstance(literal, ast.Call) and (
            (
                isinstance(literal.func, ast.Attribute)
                and literal.func.attr != "join"
                and (
                    literal.func.value in literals
                    or (
                        isinstance(literal.func.value, ast.Name)
                        and literal.func.value.id in {"str", "bytes"}
                        # These class/static factories do not take an instance receiver.
                        and literal.func.attr not in {"fromhex", "maketrans"}
                        and literal.args
                        and literal.args[0] in literals
                    )
                )
            )
            or (
                isinstance(literal.func, ast.Name)
                and literal.func.id == "format"
                and literal.args
                and literal.args[0] in literals
            )
        ):
            raise ValueError("public-only source refuses unsupported closed literal methods or formatting")
        elif isinstance(literal, ast.Call) and isinstance(literal.func, ast.Attribute) and literal.func.attr == "join":
            separator_node: ast.AST | None = None
            sequence_node: ast.AST | None = None
            if not literal.keywords and len(literal.args) == 1:
                separator_node, sequence_node = literal.func.value, literal.args[0]
            elif (
                not literal.keywords
                and len(literal.args) == 2
                and isinstance(literal.func.value, ast.Name)
                and literal.func.value.id in {"str", "bytes"}
            ):
                separator_node, sequence_node = literal.args
            separator = literals.get(separator_node) if separator_node is not None else None
            elements = literal_sequence(sequence_node) if sequence_node is not None else None
            if separator is not None and sequence_node in comprehension_inputs:
                raise ValueError("public-only source refuses unresolved comprehension inputs to literal joins")
            if separator is not None and elements is not None:
                joined = [literals.get(element) for element in elements]
                if all(type(piece) is type(separator) for piece in joined):
                    assert separator_node is not None
                    consume(
                        sum(sizes[element] for element in elements) + sizes[separator_node] * max(0, len(joined) - 1)
                    )
                    if isinstance(separator, str):
                        fold_value = separator.join(piece for piece in joined if isinstance(piece, str))
                    else:
                        fold_value = separator.join(piece for piece in joined if isinstance(piece, bytes))
        elif isinstance(literal, ast.FormattedValue) and isinstance(literals.get(literal.value), str):
            text = literals[literal.value]
            assert isinstance(text, str)
            if literal.format_spec is not None and literals.get(literal.format_spec) != "":
                raise ValueError("source static literal formatting requires an empty format specifier")
            if literal.conversion in (-1, 115):
                fold_value = text
            elif literal.conversion in (114, 97):
                consume(10 * len(text) + 2)
                fold_value = repr(text) if literal.conversion == 114 else ascii(text)
        elif isinstance(literal, ast.JoinedStr):
            pieces = [literals.get(part) for part in literal.values]
            if all(isinstance(part, str) for part in pieces):
                consume(sum(sizes[part] for part in literal.values))
                fold_value = "".join(part for part in pieces if isinstance(part, str))
        if fold_value is not None:
            literals[literal], sizes[literal] = fold_value, literal_size(fold_value)

    parents = {child: parent for parent in nodes for child in ast.iter_child_nodes(parent)}

    def mapping_reference(argument: ast.AST, call: ast.Call) -> bool:
        """Recognize named mapping copies; never infer contents or execute a guard."""
        if not isinstance(argument, ast.Name):
            return False
        inspect(argument.id, argument)
        scope: ast.AST = call
        while scope in parents and not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            scope = parents[scope]
        if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        for parameter in (*scope.args.posonlyargs, *scope.args.args, *scope.args.kwonlyargs):
            annotation = parameter.annotation
            if isinstance(annotation, ast.Subscript):
                annotation = annotation.value
            if (
                parameter.arg == argument.id
                and isinstance(annotation, ast.Name)
                and annotation.id in {"dict", "Mapping", "MutableMapping"}
            ):
                return True
        # A direct earlier rejecting type guard is also a visible mapping-copy
        # declaration. Only an OR member is independently necessary for admission.
        for statement in scope.body:
            if not isinstance(statement, ast.If) or statement.lineno >= call.lineno:
                continue
            if not statement.body or not isinstance(statement.body[-1], ast.Raise):
                continue
            checks = (
                statement.test.values
                if isinstance(statement.test, ast.BoolOp) and isinstance(statement.test.op, ast.Or)
                else [statement.test]
            )
            for check in checks:
                if (
                    isinstance(check, ast.Compare)
                    and len(check.ops) == len(check.comparators) == 1
                    and isinstance(check.ops[0], ast.IsNot)
                    and isinstance(check.comparators[0], ast.Name)
                    and check.comparators[0].id == "dict"
                    and isinstance(check.left, ast.Call)
                    and isinstance(check.left.func, ast.Name)
                    and check.left.func.id == "type"
                    and not check.left.keywords
                    and len(check.left.args) == 1
                    and isinstance(check.left.args[0], ast.Name)
                    and check.left.args[0].id == argument.id
                ):
                    return True
        return False

    type_alias_kind = getattr(ast, "TypeAlias", None)
    type_parameter_kinds = tuple(
        kind
        for kind in (getattr(ast, "TypeVar", None), getattr(ast, "ParamSpec", None), getattr(ast, "TypeVarTuple", None))
        if isinstance(kind, type)
    )

    for node in nodes:
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if key is None:
                    _literal_source_unpack(value)
                else:
                    for name, assigned_value in _selector_bindings(key, value):
                        inspect(name, assigned_value)
        elif isinstance(node, ast.DictComp):
            for name, assigned_value in _selector_bindings(node.key, node.value):
                inspect(name, assigned_value)
        elif isinstance(node, ast.Call):
            constructor = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else (node.func.attr if isinstance(node.func, ast.Attribute) else None)
            )
            for call_key, call_value in zip(node.args, node.args[1:]):
                if isinstance(call_key, (ast.Constant, ast.List, ast.Tuple)):
                    call_names, _ = _source_selector_names(call_key)
                    for call_name in call_names:
                        inspect(call_name, call_value)
            if constructor == "fromkeys":
                if node.keywords or len(node.args) not in (1, 2):
                    raise ValueError("public-only source requires explicit mapping key arguments")
                default: ast.AST | None = node.args[1] if len(node.args) == 2 else None
                if not isinstance(node.args[0], (ast.Constant, ast.List, ast.Tuple)) and not _empty_source_value(
                    default
                ):
                    raise ValueError("public-only source requires literal populated mapping keys")
                for name, assigned_value in _selector_bindings(node.args[0], default):
                    inspect(name, assigned_value)
            setters = {
                "setattr": (3,),
                "__setattr__": (2, 3),
                "setitem": (3,),
                "__setitem__": (2, 3),
                "setdefault": (1, 2),
            }
            if constructor in setters:
                if node.keywords or len(node.args) not in setters[constructor]:
                    raise ValueError("public-only source requires explicit setter arguments")
                setter_key = node.args[-2] if len(node.args) > 1 else node.args[0]
                setter_value: ast.AST | None = node.args[-1] if len(node.args) > 1 else None
                if not isinstance(setter_key, ast.Constant) and not _empty_source_value(setter_value):
                    raise ValueError("public-only source requires a literal populated setter key")
                for name, assigned_value in _selector_bindings(setter_key, setter_value):
                    inspect(name, assigned_value)
                receiver: ast.AST | None = None
                if constructor in {"setattr", "__setattr__", "setitem", "__setitem__"} and len(node.args) == 3:
                    receiver = node.args[0]
                elif constructor in {"__setattr__", "__setitem__", "setdefault"} and isinstance(
                    node.func, ast.Attribute
                ):
                    receiver = node.func.value
                if receiver is not None:
                    for name, assigned_value in _assignment_bindings(receiver, setter_value, include_receivers=True):
                        inspect(name, assigned_value)
            if constructor in {"dict", "OrderedDict", "defaultdict", "MappingProxyType", "update"}:
                for argument in node.args:
                    if isinstance(argument, ast.Dict) or _empty_source_value(argument):
                        continue
                    if constructor in {"dict", "OrderedDict", "MappingProxyType"} and mapping_reference(argument, node):
                        continue
                    if not inspect_literal_pairs(argument):
                        raise ValueError("public-only source requires literal mapping constructor entries")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            # Screen explicit receiving aliases conservatively. Unaliased and
            # wildcard imports retain their dependency-graph contract; an import
            # identifier alone does not establish populated credential data.
            # Imported runtime values and export names are not resolved here.
            for alias in node.names:
                if alias.asname is not None:
                    inspect(alias.asname, node)
        elif isinstance(node, ast.Match):
            for case in node.cases:
                for pattern in ast.walk(case.pattern):
                    if isinstance(pattern, (ast.MatchAs, ast.MatchStar)) and pattern.name is not None:
                        inspect(pattern.name, node.subject)
                    elif isinstance(pattern, ast.MatchMapping) and pattern.rest is not None:
                        inspect(pattern.rest, node.subject)
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            for name, _ in _assignment_bindings(node.optional_vars, node.context_expr, include_receivers=True):
                inspect(name, node.context_expr)
        elif isinstance(node, ast.ExceptHandler) and node.name is not None:
            inspect(node.name, node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Definition names bind populated callable objects independently of parameters.
            inspect(node.name, node)
        elif isinstance(node, ast.arg):
            # A declaration can receive a populated call argument even when its
            # default is empty. Refuse credential-shaped receiving interfaces;
            # do not infer call targets, runtime dispatch or external values.
            inspect(node.arg, node)
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            inspect_iterable_pairs(node.iter)
            # A target receives an element, not the entire iterable. Use the
            # complete iterable as the conservative populated-value boundary.
            for name, _ in _assignment_bindings(node.target, node.iter, include_receivers=True):
                inspect(name, node.iter)
        elif type_alias_kind is not None and isinstance(node, type_alias_kind):
            alias_target, alias_assigned = getattr(node, "name", None), getattr(node, "value", None)
            if not isinstance(alias_target, ast.AST) or not isinstance(alias_assigned, ast.AST):
                raise ValueError("source type alias requires an explicit AST binding")
            for name, assigned_value in _assignment_bindings(alias_target, alias_assigned, include_receivers=True):
                inspect(name, assigned_value)
        elif isinstance(node, type_parameter_kinds):
            parameter_name = getattr(node, "name", None)
            if not isinstance(parameter_name, str):
                raise ValueError("source type parameter requires an explicit name")
            for field in ("bound", "default_value"):
                declaration_value = getattr(node, field, None)
                if declaration_value is not None and not isinstance(declaration_value, ast.AST):
                    raise ValueError("source type parameter requires an explicit AST value")
                inspect(parameter_name, declaration_value)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for name, assigned_value in _assignment_bindings(target, node.value, include_receivers=True):
                    inspect(name, assigned_value)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            for name, assigned_value in _assignment_bindings(node.target, node.value, include_receivers=True):
                inspect(name, assigned_value)
        elif isinstance(node, ast.keyword):
            if node.arg is None:
                _literal_source_unpack(node.value)
            else:
                inspect(node.arg, node.value)
        # Folded calls also pass through their call-specific checks above.
        # Validate every cached result independently of the dispatch branch.
        if node in literals:
            text = literals[node]
            assert_public_content(text)
            consume(sizes[node])
            try:
                ast.parse(text)
            except (SyntaxError, ValueError, RecursionError):
                continue
            _screen_source_assignments(text, depth + 1, _literal_budget=budget)


class SourceFile(StrictModel):
    path: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_/]*\.py$", max_length=240)
    source: str = Field(max_length=65_536)
    git_blob: str = Field(pattern=r"^[0-9a-f]{40}$")
    sha256: Digest

    @model_validator(mode="after")
    def bytes_match(self) -> SourceFile:
        assert_public_content(self.model_dump())
        if any(not part.isidentifier() for part in self.path[:-3].split("/")):
            raise ValueError("source paths require canonical Python module components")
        raw = self.source.encode("utf-8")
        if len(raw) > 65_536 or not raw or "\x00" in self.source:
            raise ValueError("bounded nonempty UTF-8 Python text required")
        _screen_source_assignments(self.source)
        if hashlib.sha256(raw).hexdigest() != self.sha256:
            raise ValueError("source SHA256 mismatch")
        if hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() != self.git_blob:
            raise ValueError("source Git blob mismatch")
        return self


class SourcePackage(StrictModel):
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", max_length=120)
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    root: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_/]*$", max_length=200)
    files: list[SourceFile] = Field(min_length=1, max_length=8)
    stale_worker_proposal: bool = False

    @model_validator(mode="after")
    def complete_capture(self) -> SourcePackage:
        assert_public_content(self.model_dump())
        if any(not part.isidentifier() for part in self.root.split("/")):
            raise ValueError("capture root requires canonical Python module components")
        if len({f.path for f in self.files}) != len(self.files):
            raise ValueError("duplicate source path")
        modules = [file.path[:-3].replace("/", ".").removesuffix(".__init__") for file in self.files]
        if len(set(modules)) != len(modules):
            raise ValueError("ambiguous duplicate Python module identity in capture")
        if any(not f.path.startswith(self.root + "/") for f in self.files):
            raise ValueError("all files must belong to the declared captured root")
        if sum(len(f.source.encode()) for f in self.files) > 100_000:
            raise ValueError("captured package exceeds total byte bound")
        return self


class AuditProgram(StrictModel):
    indexed: bool = False
    query_once: bool = False
    dependency_queue: bool = False
    fragments: bool = False
    package_batch: bool = False
    checked_handoff: bool = False


class AuditRequest(StrictModel):
    campaign_id: str
    purpose: Literal[
        "Exact static inventory of every supplied source file and its captured dependency closure"
    ] = "Exact static inventory of every supplied source file and its captured dependency closure"
    publicOnly: bool = True
    permitted_actions: list[Literal["parse-static-source", "compare-local", "write-artifact"]]
    development: list[SourcePackage] = Field(min_length=1, max_length=2)
    confirmation_digest: Digest
    confirmation_count: int = Field(ge=1, le=4)
    execution_units: int = Field(default=50_000_000, ge=0, le=100_000_000)
    search_units: int = Field(default=10_000, ge=0, le=100_000)
    measurement_epoch: int = Field(default=0, ge=0)
    instrument_digest: Digest
    USDCBaseUnits: Literal["0"] = "0"
    AGIALPHABaseUnits: Literal["0"] = "0"

    @model_validator(mode="after")
    def identity(self) -> AuditRequest:
        assert_public_content(self.model_dump())
        if str(uuid.UUID(self.campaign_id)) != self.campaign_id or not self.publicOnly:
            raise ValueError("canonical campaign UUID and publicOnly=true required")
        if len(set(self.permitted_actions)) != len(self.permitted_actions):
            raise ValueError("actions must be unique")
        if len({source_fingerprint(p) for p in self.development}) != len(self.development):
            raise ValueError("development packages must be distinct")
        return self


class BudgetExhausted(ValueError):
    """Partial work cannot become a complete comparison."""


def _has_exact_type(value: object, expected: type[Any]) -> bool:
    """Require the original exact built-in type, excluding subclasses."""
    value_type = type(value)
    return value_type is expected


class Meter:
    def __init__(self, limit: int) -> None:
        if not _has_exact_type(limit, int) or limit < 0:
            raise ValueError("exact nonnegative unit allowance required")
        self.limit = limit
        self.costs = dict.fromkeys(CATEGORIES, 0)
        self.trace: Counter[str] = Counter()

    @property
    def used(self) -> int:
        return sum(self.costs.values())

    def charge(self, category: str, units: int = 1, event: str | None = None) -> None:
        if category not in self.costs or not _has_exact_type(units, int) or units < 0:
            raise ValueError("invalid logical charge")
        if self.used + units > self.limit:
            raise BudgetExhausted("source audit logical budget exhausted")
        self.costs[category] += units
        if event:
            self.trace[event] += 1


def package_identity(package: SourcePackage) -> str:
    """Bind exact source context; a fault switch does not mint a new worker version."""
    return digest(
        "source-audit-package",
        {
            "repository": package.repository,
            "commit": package.commit,
            "root": package.root,
            "files": sorted([f.path, f.git_blob] for f in package.files),
        },
    )


def source_fingerprint(package: SourcePackage) -> str:
    """Renaming paths/repositories/commits or duplicating bytes cannot mint freshness."""
    return digest("source-audit-freshness", sorted({f.git_blob for f in package.files}))


def program_id(program: AuditProgram) -> str:
    return "".join("1" if getattr(program, axis) else "0" for axis in AXES)


def programs() -> list[AuditProgram]:
    return [
        AuditProgram.model_validate(dict(zip(AXES, bits, strict=True)))
        for bits in itertools.product((False, True), repeat=len(AXES))
    ]


def _module(file: SourceFile) -> str:
    name = file.path[:-3].replace("/", ".")
    return name.removesuffix(".__init__")


def _tree(file: SourceFile, meter: Meter, category: str) -> ast.Module:
    meter.charge(category, (len(file.source.encode()) + 63) // 64, "read-source")
    try:
        tree = ast.parse(file.source, filename=file.path)
    except (SyntaxError, RecursionError) as exc:
        raise ValueError("source is outside the bounded parseable Python domain") from exc
    nodes = 0
    for _ in ast.walk(tree):
        nodes += 1
        meter.charge(category, 1, "ast-node-census-visit")
    if nodes > 12_000:
        raise ValueError("source AST exceeds node bound")
    meter.charge(category, 0, "parse-ast")
    return tree


def _imports(file: SourceFile, tree: ast.Module, captured: set[str], meter: Meter, category: str) -> list[str]:
    result: set[str] = set()
    package = _module(file) if file.path.endswith("/__init__.py") else _module(file).rsplit(".", 1)[0]
    construction = "check" if category == "check" else "construction"

    def add(target: str) -> None:
        meter.charge(construction, 1, "import-target-insertion")
        result.add(target)

    for node in ast.walk(tree):
        meter.charge(category, 1, "import-ast-visit")
        if isinstance(node, ast.Import):
            for alias in node.names:
                add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            parts = package.split(".")
            if node.level > len(parts):
                add("!relative-import-outside-root")
                continue
            base = ".".join(parts[: len(parts) - node.level + 1]) if node.level else ""
            target = ".".join(x for x in (base, node.module) if x)
            if node.module is None:
                add(target)
                for alias in node.names:
                    if alias.name != "*":
                        add(".".join(x for x in (target, alias.name) if x))
            else:
                add(target)
                # A from-import may resolve an attribute or a submodule at runtime.
                # Conservatively include explicitly captured candidate submodules.
                for alias in node.names:
                    meter.charge(construction, 1, "captured-import-membership")
                    if target + "." + alias.name in captured:
                        add(target + "." + alias.name)
    return sorted(result)


def _facts(
    file: SourceFile, meter: Meter, category: str = "read", captured: set[str] | None = None
) -> list[tuple[str, Any]]:
    tree = _tree(file, meter, category)
    licenses = re.findall(r"SPDX-License-Identifier:\s*([^\r\n]+)", "\n".join(file.source.splitlines()[:5]))
    dynamic = 0
    for n in ast.walk(tree):
        meter.charge(category, 1, "dynamic-ast-visit")
        if isinstance(n, ast.Call) and (
            (isinstance(n.func, ast.Name) and n.func.id in {"__import__", "import_module"})
            or (isinstance(n.func, ast.Attribute) and n.func.attr == "import_module")
        ):
            dynamic += 1
    symbols = set()
    for n in tree.body:
        meter.charge(category, 1, "symbol-ast-visit")
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.name.startswith("_"):
            meter.charge("check" if category == "check" else "construction", 1, "public-symbol-insertion")
            symbols.add(n.name)
    meter.charge("check" if category == "check" else "construction", 4, "materialize-facts")
    return [
        ("license", licenses[0].strip() if licenses else None),
        ("imports", _imports(file, tree, captured or set(), meter, category)),
        ("symbols", sorted(symbols)),
        ("dynamic", dynamic),
    ]


def reference_report(package: SourcePackage, meter: Meter) -> dict[str, Any]:
    """Fixed exact checker: direct static facts plus separate per-source graph walks."""
    package = SourcePackage.model_validate(copy.deepcopy(package.model_dump()))
    files = sorted(package.files, key=lambda f: f.path)
    names = {_module(f) for f in files}
    facts = {_module(f): dict(_facts(f, meter, "check", names)) for f in files}
    edges: dict[str, set[str]] = {}
    outside: dict[str, list[str]] = {}
    for name, fact in facts.items():
        meter.charge("check", 1, "reference-vertex")
        edges[name], outside[name] = set(), []
        for target in fact["imports"]:
            meter.charge("check", 2, "reference-edge-membership")
            if target in facts:
                meter.charge("check", 1, "reference-edge-insert")
                edges[name].add(target)
            else:
                outside[name].append(target)
    rows = []
    for file in files:
        meter.charge("check", 1, "reference-source-walk")
        name, seen, pending = _module(file), set(), []
        for target in sorted(edges[name]):
            meter.charge("check", 1, "reference-stack-push")
            pending.append(target)
        while pending:
            target = pending.pop()
            meter.charge("check", 2, "reference-pop-membership")
            if target not in seen:
                meter.charge("check", 1, "reference-seen-insert")
                seen.add(target)
                for child in sorted(edges[target]):
                    meter.charge("check", 2, "reference-edge-test")
                    if child not in seen:
                        meter.charge("check", 1, "reference-stack-push")
                        pending.append(child)
        meter.charge("check", 1, "reference-remove-self")
        seen.discard(name)
        row = facts[name]
        rows.append(
            {
                "path": file.path,
                "module": name,
                "git_blob": file.git_blob,
                "sha256": file.sha256,
                "license": row["license"],
                "public_symbols": row["symbols"],
                "imports": row["imports"],
                "captured_dependencies": sorted(edges[name]),
                "transitive_dependencies": sorted(seen),
                "outside_capture": sorted(outside[name]),
                "findings": ([] if row["license"] else ["missing-SPDX-header"])
                + (["dynamic-import-not-resolved"] if row["dynamic"] else []),
            }
        )
    return {
        "schema": "static-source-report/v1",
        "repository": package.repository,
        "commit": package.commit,
        "root": package.root,
        "capture_complete_only_for_listed_files": True,
        "dependency_semantics": (
            "syntactic import targets plus captured from-import submodules; conservative, not runtime resolution"
        ),
        "files": rows,
    }


def _execute(package: SourcePackage, program: AuditProgram, meter: Meter, expected: dict[str, Any]) -> dict[str, Any]:
    """Execute six actual formulation choices under the same static tools and goal."""
    package = SourcePackage.model_validate(copy.deepcopy(package.model_dump()))
    program = AuditProgram.model_validate(program.model_dump())
    expected = copy.deepcopy(expected)
    files = sorted(package.files, key=lambda f: f.path)
    names = {_module(f) for f in files}
    materials: dict[str, Any] = {}
    for file in files:
        if program.query_once:
            material = _facts(file, meter, captured=names)
            meter.charge("construction", len(material), "retain-facts")
            materials[file.path] = dict(material) if program.indexed else material
            if program.indexed:
                meter.charge("construction", len(material), "build-fact-index")

    def query(file: SourceFile, key: str) -> Any:
        material: Any = materials[file.path] if program.query_once else _facts(file, meter, captured=names)
        if program.indexed:
            if not program.query_once:
                meter.charge("construction", len(material), "build-fact-index")
                material = dict(material)
            meter.charge("query", 1, "keyed-query")
            return material[key]
        for field, value in material:
            meter.charge("query", 1, "sequential-query")
            if key == field:
                return value
        raise ValueError("missing static fact")

    imports = {_module(f): query(f, "imports") for f in files}
    graph: dict[str, set[str]] = {}
    outside: dict[str, list[str]] = {}
    for name, values in imports.items():
        meter.charge("dependency", 1, "graph-vertex")
        graph[name], outside[name] = set(), []
        for target in values:
            meter.charge("dependency", 2, "graph-edge-membership")
            if target in imports:
                meter.charge("dependency", 1, "graph-edge-insert")
                graph[name].add(target)
            else:
                outside[name].append(target)
    closures: dict[str, set[str]] = {}
    if program.dependency_queue:
        pending = []
        for name, targets in graph.items():
            meter.charge("dependency", 1, "initialize-closure-vertex")
            closures[name] = set()
            for target in sorted(targets):
                meter.charge("dependency", 1, "initialize-closure-insert")
                closures[name].add(target)
            meter.charge("dependency", 1, "dependency-queue-push")
            pending.append(name)
        while pending:
            name = pending.pop(0)
            meter.charge("dependency", 1, "dependency-queue-pop")
            for parent, targets in graph.items():
                meter.charge("dependency", 2, "dependency-queue-edge")
                if name in targets:
                    new = []
                    for target in sorted(closures[name]):
                        meter.charge("dependency", 1, "closure-membership")
                        if target not in closures[parent]:
                            new.append(target)
                    if new:
                        for target in new:
                            meter.charge("dependency", 1, "dependency-union")
                            closures[parent].add(target)
                        queued = False
                        for item in pending:
                            meter.charge("dependency", 1, "queue-membership-test")
                            if parent == item:
                                queued = True
                                break
                        if not queued:
                            meter.charge("dependency", 1, "dependency-queue-push")
                            pending.append(parent)
    else:
        for name in graph:
            seen: set[str] = set()
            pending = []
            for target in sorted(graph[name]):
                meter.charge("dependency", 1, "walk-stack-push")
                pending.append(target)
            meter.charge("dependency", 1, "serial-source-barrier")
            while pending:
                target = pending.pop()
                meter.charge("dependency", 2, "repeat-dependency-walk")
                if target not in seen:
                    meter.charge("dependency", 1, "walk-seen-insert")
                    seen.add(target)
                    for child in sorted(graph[target]):
                        meter.charge("dependency", 2, "walk-edge-membership")
                        if child not in seen:
                            meter.charge("dependency", 1, "walk-stack-push")
                            pending.append(child)
            closures[name] = seen
    for name in closures:
        meter.charge("dependency", 1, "remove-self")
        closures[name].discard(name)
    cached: dict[str, dict[str, Any]] = {}

    def fragment(file: SourceFile) -> dict[str, Any]:
        if program.fragments and file.path in cached:
            meter.charge("production", 1, "reuse-fragment")
            return copy.deepcopy(cached[file.path])
        name, license_id = _module(file), query(file, "license")
        row = {
            "path": file.path,
            "module": name,
            "git_blob": file.git_blob,
            "sha256": file.sha256,
            "license": license_id,
            "public_symbols": query(file, "symbols"),
            "imports": imports[name],
            "captured_dependencies": sorted(graph[name]),
            "transitive_dependencies": sorted(closures[name]),
            "outside_capture": sorted(outside[name]),
            "findings": ([] if license_id else ["missing-SPDX-header"])
            + (["dynamic-import-not-resolved"] if query(file, "dynamic") else []),
        }
        meter.charge("production", len(canonical(row)), "construct-fragment")
        if program.fragments:
            meter.charge("production", 1, "cache-fragment")
            cached[file.path] = copy.deepcopy(row)
        return row

    accepted: dict[str, dict[str, Any]] = {}
    expected_rows = {row["path"]: row for row in expected["files"]}
    version = package_identity(package)
    fields = ("all",) if program.package_batch else ("inventory", "license", "symbols", "dependencies")
    for field in fields:
        for file in files:
            meter.charge("coordination", 1, "package-job" if program.package_batch else "per-file-subtask")
            row = fragment(file)
            proposals = [(version, row)]
            if package.stale_worker_proposal and file == files[0]:
                stale = copy.deepcopy(row)
                stale["public_symbols"] = ["STALE_UNAPPROVED_SYMBOL"]
                proposals.append(("0" * 64, stale))
            for proposal_version, proposed in proposals:
                meter.charge("coordination", 1, "worker-proposal")
                if program.checked_handoff:
                    meter.charge("coordination", len(canonical(proposed)), "checked-CAS")
                    if proposal_version != version or proposed != expected_rows[file.path]:
                        meter.charge("coordination", 1, "reject-stale-or-invalid")
                        continue
                else:
                    meter.charge("coordination", 1, "unchecked-last-write")
                accepted[file.path] = proposed
    result = {**{k: v for k, v in expected.items() if k != "files"}, "files": [accepted[f.path] for f in files]}
    meter.charge("production", len(canonical(result)), "emit-report")
    meter.charge("check", len(canonical(result)), "exact-output-check")
    return {"artifact": result, "exact": result == expected, "artifact_digest": digest("source-audit-artifact", result)}


def execute(package: SourcePackage, program: AuditProgram, meter: Meter) -> dict[str, Any]:
    """Public pure execution always constructs its own fixed reference checker."""
    return _execute(package, program, meter, reference_report(package, meter))


def _source_digest() -> str:
    root = Path(__file__).parent
    manifest = {}
    for name in ("transformation_source_audit.py", "transformation_source_audit_cli.py", "measurement.py"):
        path = root / name
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > 256_000:
            raise ValueError("source-audit engine requires bounded regular source files")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            raw = stream.read(256_001)
            after = os.fstat(stream.fileno())
        if (
            (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
            or len(raw) != before.st_size
            or any(
                getattr(opened, key) != getattr(after, key)
                for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
            )
        ):
            raise ValueError("source-audit engine changed during binding")
        manifest[name] = hashlib.sha256(raw).hexdigest()
    return digest("source-audit-engine", {"sources": manifest, "runtime": _engine_digest()})


def initial_instrument() -> dict[str, Any]:
    return {
        "method": "file-count-proxy/v1",
        "implementation_digest": _source_digest(),
        "exact_admission_gate": "static-source-report/v1",
        "epoch": 0,
        "scope": "local static finite capture; not calibrated human usefulness",
    }


def exact_instrument() -> EvaluationInstrument:
    return EvaluationInstrument(
        instrument_id="source-package-exact",
        version=1,
        domain=SCHEMA,
        method="exact-source-report/v1",
        implementation_digest=_source_digest(),
        calibration_scope="deterministic finite report checker; no empirical outcome calibration",
    )


def revision_proposal(package: SourcePackage) -> dict[str, Any]:
    """Executed disagreement probe; output is unsigned and cannot revise a ledger."""
    package = SourcePackage.model_validate(copy.deepcopy(package.model_dump()))
    meter = Meter(10_000_000)
    expected = reference_report(package, meter)
    malformed = copy.deepcopy(expected)
    malformed["files"][0]["public_symbols"] = ["INVENTED_SYMBOL"]
    meter.charge("check", len(canonical(expected)) + len(canonical(malformed)), "instrument-disagreement-check")
    return {
        "instrument": exact_instrument().model_dump(),
        "cases": [
            {
                "id": package_identity(package),
                "evidence_digest": digest("source-audit-disagreement", {"expected": expected, "proposed": malformed}),
                "old_score_ppm": 1_000_000 if len(malformed["files"]) == len(expected["files"]) else 0,
                "new_score_ppm": 1_000_000 if malformed == expected else 0,
                "outcome_ppm": 0,
            }
        ],
        "evidence": {"expected": expected, "malformed": malformed},
        "costs": meter.costs,
        "authority_granted": False,
        "requires": "separate configured verifier disagreement attestation and controller approval",
    }


class SourceAuditDiscovery:
    """Serialize bounded phases; pause/cancel apply between phases, not inside AST parsing."""

    def __init__(self, journal: Journal, ledger: MeasurementLedger | None = None) -> None:
        journal.verify()
        if ledger is not None and (
            ledger.journal.identity != journal.identity or ledger.journal.path.resolve() != journal.path.resolve()
        ):
            raise ValueError("measurement ledger must use this journal")
        self.journal, self.ledger = journal, ledger

    @staticmethod
    def _key(campaign_id: str) -> str:
        return KEY + str(uuid.UUID(campaign_id))

    def measurement_context(self) -> dict[str, Any]:
        epochs: list[Any]
        if self.ledger is None:
            # Missing signer configuration must never reset a persisted ledger.
            # Historical show/envelope exports do not require this active context.
            try:
                self.journal.latest(MEASUREMENT_KEY)
            except KeyError as missing:
                # Other retained-record shape errors must never become epoch zero.
                if missing.args != (MEASUREMENT_KEY,):
                    raise
                # Only an absent measurement record permits the initial context.
                epochs = []
            else:
                raise Conflict("persisted measurement state requires its configured ledger")
        else:
            epochs = self.ledger.snapshot()["epochs"]
        if not _has_exact_type(epochs, list):
            raise Conflict("measurement epochs must be an exact list")
        if not epochs:
            return {
                "measurement_epoch": 0,
                "instrument_digest": digest("source-audit-instrument", initial_instrument()),
            }
        active = epochs[-1]
        if active["instrument"] != exact_instrument().model_dump():
            raise Conflict("active measurement instrument is not this installed exact source checker")
        return {"measurement_epoch": active["epoch"], "instrument_digest": active["instrument_digest"]}

    def _exposure_state(self, cx: Any) -> dict[str, Any]:
        try:
            state = Journal.document(self.journal.latest(EXPOSURES, cx))
        except KeyError:
            # A prototype journal cannot prove which failed/partial packages were
            # observed. Preserve it as history; never infer a fresh holdout.
            if cx.execute("SELECT 1 FROM events WHERE mission LIKE ? LIMIT 1", (KEY + "%",)).fetchone():
                raise Conflict(
                    "source-audit exposure checkpoint is missing; preserve history and do not infer freshness"
                )
            return {"schema": "source-audit-exposures/v2", "captures": {}, "blobs": {}}
        if set(state) != {"schema", "captures", "blobs"} or state["schema"] != "source-audit-exposures/v2":
            raise Conflict("invalid source-audit exposure checkpoint")
        for field, width, limit in (("captures", 64, MAX_EXPOSURES), ("blobs", 40, MAX_BLOB_EXPOSURES)):
            if not _has_exact_type(state[field], dict) or len(state[field]) > limit:
                raise Conflict("invalid source-audit exposure capacity")
            for identity, entry in state[field].items():
                if (
                    not _has_exact_type(identity, str)
                    or not re.fullmatch(r"[a-f0-9]{" + str(width) + "}", identity)
                    or not _has_exact_type(entry, dict)
                    or set(entry) != {"first_operation", "kinds"}
                    or not _has_exact_type(entry["first_operation"], str)
                    or not 1 <= len(entry["first_operation"]) <= 160
                    or not _has_exact_type(entry["kinds"], list)
                    or any(not _has_exact_type(kind, str) for kind in entry["kinds"])
                    or not entry["kinds"]
                    or len(entry["kinds"]) != len(set(entry["kinds"]))
                    or not set(entry["kinds"]) <= {"development", "proposal", "confirmation"}
                ):
                    raise Conflict("invalid source-audit exposure record")
        return state

    def _expose(self, packages: list[SourcePackage], kind: str, operation: str, cx: Any) -> bool:
        state = self._exposure_state(cx)
        identities = {source_fingerprint(package) for package in packages}
        blobs = {file.git_blob for package in packages for file in package.files}
        fresh = not identities.intersection(state["captures"]) and not blobs.intersection(state["blobs"])
        if (
            len(set(state["captures"]) | identities) > MAX_EXPOSURES
            or len(set(state["blobs"]) | blobs) > MAX_BLOB_EXPOSURES
        ):
            raise Conflict("source-audit exposure capacity reached; never reset its holdout history")
        changed = False
        for field, values in (("captures", identities), ("blobs", blobs)):
            for identity in sorted(values):
                if identity not in state[field]:
                    state[field][identity] = {"first_operation": operation, "kinds": [kind]}
                    changed = True
                elif kind not in state[field][identity]["kinds"]:
                    state[field][identity]["kinds"].append(kind)
                    state[field][identity]["kinds"].sort()
                    changed = True
        if changed:
            self.journal.append(cx, EXPOSURES, state)
        return fresh

    def revise_measurement(
        self, proposal_digest: str, validation: SignedEnvelope, approval: SignedEnvelope, *, operation_id: str
    ) -> dict[str, Any]:
        if self.ledger is None:
            raise PermissionError("separately configured measurement ledger required")
        validation = SignedEnvelope.model_validate(copy.deepcopy(validation.model_dump()))
        approval = SignedEnvelope.model_validate(copy.deepcopy(approval.model_dump()))
        assert_public_content([validation.model_dump(), approval.model_dump()])
        proposal = self.journal.latest(KEY + "revision:" + proposal_digest)["proposal"]
        if (
            proposal["instrument"] != exact_instrument().model_dump()
            or validation.payload.get("cases") != proposal["cases"]
        ):
            raise Conflict("signed validation must bind the retained current disagreement evidence")
        return self.ledger.revise_instrument(exact_instrument(), validation, approval, operation_id=operation_id)

    def propose_revision(self, package: SourcePackage) -> dict[str, Any]:
        package = SourcePackage.model_validate(copy.deepcopy(package.model_dump()))
        operation = digest("source-audit-revision-input", {"package": package.model_dump(), "engine": _source_digest()})
        input_key = KEY + "revision-input:" + operation
        with self.journal.transaction() as cx:
            try:
                return self.journal.latest(input_key, cx)
            except KeyError:
                pass
            if self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("native STOP is active")
            self._expose([package], "proposal", operation, cx)
            try:
                proposal = revision_proposal(package)
                assert_public_content(proposal)
            except (ValueError, RecursionError):
                return self.journal.append(
                    cx,
                    input_key,
                    {
                        "state": "failed",
                        "source_fingerprint": source_fingerprint(package),
                        "source_package": package.model_dump(),
                        "proposal": None,
                        "proposal_digest": None,
                        "authority_granted": False,
                        "physical_cost": "UNKNOWN; failed proposal exposure retained",
                    },
                )
            identity = digest("source-audit-revision", proposal)
            body = {
                "state": "pending-review",
                "source_package": package.model_dump(),
                "proposal_digest": identity,
                "proposal": proposal,
                "authority_granted": False,
            }
            self.journal.append(cx, KEY + "revision:" + identity, body)
            return self.journal.append(cx, input_key, body)

    def _binding(self, request: AuditRequest) -> str:
        if {k: getattr(request, k) for k in ("measurement_epoch", "instrument_digest")} != self.measurement_context():
            raise Conflict("measurement changed; create a fresh campaign under one common current epoch")
        return digest(
            "source-audit-binding",
            {
                "request": request.model_dump(),
                "code": _source_digest(),
                "cost_rule": COST_RULE,
                "language": [p.model_dump() for p in programs()],
            },
        )

    def show(self, campaign_id: str) -> dict[str, Any]:
        return self.journal.latest(self._key(campaign_id))

    def create(self, request: AuditRequest) -> dict[str, Any]:
        request = AuditRequest.model_validate(copy.deepcopy(request.model_dump()))
        binding = self._binding(request)
        with self.journal.transaction() as cx:
            try:
                record = self.journal.latest(self._key(request.campaign_id), cx)
            except KeyError:
                self._expose(request.development, "development", request.campaign_id, cx)
                return self.journal.append(
                    cx,
                    self._key(request.campaign_id),
                    {
                        "schema": SCHEMA,
                        "request": request.model_dump(),
                        "binding_digest": binding,
                        "approval": None,
                        "state": "queued",
                        "spent": dict.fromkeys(CATEGORIES, 0),
                        "development": [],
                        "freeze": None,
                        "confirmation": None,
                        "result": None,
                    },
                )
            if record["binding_digest"] != binding:
                raise Conflict("campaign identity already binds another comparison")
            return record

    def _ready(self, data: dict[str, Any], cx: Any) -> AuditRequest:
        request = AuditRequest.model_validate(data["request"])
        if self.journal.latest("@control", cx)["state"] != "ready" or data["state"] in {"paused", "cancelled"}:
            raise Conflict("source audit or native operator is stopped")
        if self._binding(request) != data["binding_digest"]:
            raise Conflict("source/request changed; fresh campaign required")
        if data["approval"] != data["binding_digest"]:
            raise PermissionError("approve the exact bounded source audit first")
        if set(request.permitted_actions) != {"parse-static-source", "compare-local", "write-artifact"}:
            raise PermissionError("fixed source audit actions must be explicitly allowed")
        return request

    def approve(self, campaign_id: str, binding_digest: str) -> dict[str, Any]:
        with self.journal.transaction() as cx:
            record = self.journal.latest(self._key(campaign_id), cx)
            data = Journal.document(record)
            if (
                data["state"] != "queued"
                or self._binding(AuditRequest.model_validate(data["request"])) != binding_digest
            ):
                raise Conflict("approval must bind the queued current comparison")
            if self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("native STOP is active")
            if data["approval"] == binding_digest:
                return record
            data["approval"] = binding_digest
            return self.journal.append(cx, self._key(campaign_id), data)

    def control(self, campaign_id: str, action: Literal["pause", "resume", "cancel"]) -> dict[str, Any]:
        with self.journal.transaction() as cx:
            record = self.journal.latest(self._key(campaign_id), cx)
            data = Journal.document(record)
            if data["state"] in {"completed", "cancelled"}:
                raise Conflict("terminal source audit cannot resume")
            if action == "resume" and data["state"] == "paused":
                data["state"] = data.pop("paused_from")
            elif action == "pause" and data["state"] != "paused":
                data["paused_from"], data["state"] = data["state"], "paused"
            elif action == "cancel":
                data["state"], data["approval"] = "cancelled", None
            else:
                raise Conflict("unsupported source audit control transition")
            return self.journal.append(cx, self._key(campaign_id), data)

    @staticmethod
    def _table(
        packages: list[SourcePackage], execution: Meter, search: Meter, rows: list[dict[str, Any]], epoch: int
    ) -> None:
        for package in packages:
            expected = reference_report(package, execution)
            row: dict[str, Any] = {"package_identity": package_identity(package), "methods": {}, "artifacts": {}}
            rows.append(row)
            for program in programs():
                search.charge("search", 1, "candidate-execution")
                method = Meter(execution.limit - execution.used)
                try:
                    result = _execute(package, program, method, expected)
                except (ValueError, RecursionError):
                    row["methods"][program_id(program)] = {
                        "complete": False,
                        "exact": False,
                        "costs": method.costs,
                        "units": method.used,
                        "trace": dict(method.trace),
                    }
                    raise
                finally:
                    for name, units in method.costs.items():
                        execution.charge(name, units)
                row["artifacts"][result["artifact_digest"]] = result["artifact"]
                proxy = len(result["artifact"]["files"]) == len(expected["files"])
                row["methods"][program_id(program)] = {
                    "artifact_digest": result["artifact_digest"],
                    "exact": result["exact"],
                    "score_ppm": 1_000_000 if (result["exact"] if epoch else proxy) else 0,
                    "costs": method.costs,
                    "units": method.used,
                    "trace": dict(method.trace),
                }

    @staticmethod
    def _totals(rows: list[dict[str, Any]], search: Meter) -> dict[str, int]:
        totals = {}
        for program in programs():
            identity = program_id(program)
            search.charge("search", 1, "selection-inspection")
            valid = True
            for row in rows:
                search.charge("search", 1, "candidate-exact-inspection")
                if not row["methods"][identity]["exact"]:
                    valid = False
                    break
            if valid:
                total = 0
                for row in rows:
                    search.charge("search", 1, "candidate-cost-inspection")
                    total += row["methods"][identity]["units"]
                totals[identity] = total
        return totals

    @staticmethod
    def _select(totals: dict[str, int], search: Meter, event: str) -> str:
        selected: str | None = None
        for identity in sorted(totals):
            search.charge("search", 1, event)
            if selected is None or (totals[identity], identity != "000000", identity) < (
                totals[selected],
                selected != "000000",
                selected,
            ):
                selected = identity
        if selected is None:
            raise ValueError("no exact control available")
        return selected

    @staticmethod
    def _oracle(rows: list[dict[str, Any]], search: Meter) -> int:
        total = 0
        for row in rows:
            best: int | None = None
            for method in row["methods"].values():
                search.charge("search", 1, "oracle-validity-inspection")
                if method["exact"]:
                    search.charge("search", 1, "oracle-minimum-comparison")
                    if best is None or method["units"] < best:
                        best = method["units"]
            if best is None:
                raise ValueError("no correct oracle alternative")
            total += best
        return total

    def _phase(
        self, campaign_id: str, packages: list[SourcePackage] | None, freeze_digest: str | None
    ) -> dict[str, Any]:
        supplied = (
            None
            if packages is None
            else [SourcePackage.model_validate(copy.deepcopy(p.model_dump())) for p in packages]
        )
        input_digest = None if supplied is None else digest("source-audit-confirmation", supplied)
        with self.journal.transaction() as cx:
            record = self.journal.latest(self._key(campaign_id), cx)
            data = Journal.document(record)
            if data["state"] == "completed":
                if (
                    supplied is not None
                    and data["confirmation"]
                    and data["confirmation"]["digest"] == input_digest
                    and data["freeze"]["digest"] == freeze_digest
                ):
                    return record
                raise Conflict("terminal comparison cannot be replaced")
            if supplied is None and data["state"] == "frozen":
                return record
            request = self._ready(data, cx)
            if supplied is None:
                if data["state"] != "queued":
                    raise Conflict("development requires queued campaign")
                cases, rows = request.development, data["development"]
            else:
                if data["state"] != "frozen" or data["freeze"]["digest"] != freeze_digest:
                    raise Conflict("confirmation requires exact frozen candidate")
                if len(supplied) != request.confirmation_count or input_digest != request.confirmation_digest:
                    raise ValueError("complete committed confirmation packages required")
                fresh = {source_fingerprint(p) for p in supplied}
                seen_blobs: set[str] = set()
                overlap = False
                for package in supplied:
                    package_blobs = {file.git_blob for file in package.files}
                    overlap |= bool(seen_blobs.intersection(package_blobs))
                    seen_blobs.update(package_blobs)
                globally_fresh = self._expose(supplied, "confirmation", campaign_id, cx)
                data["confirmation"] = {
                    "digest": input_digest,
                    "source_fingerprints": sorted(fresh),
                    "source_blobs": sorted(seen_blobs),
                    "packages": [package.model_dump() for package in supplied],
                    "rows": [],
                    "complete": False,
                }
                if len(fresh) != len(supplied) or overlap or not globally_fresh:
                    data["state"], data["approval"] = "completed", None
                    data["result"] = {
                        "decision": "retain-incumbent",
                        "reason": "confirmation-source-already-observed",
                        "metrics": None,
                        "full_campaign_units": sum(data["spent"].values()),
                    }
                    return self.journal.append(cx, self._key(campaign_id), data)
                cases, rows = supplied, data["confirmation"]["rows"]
            execution = Meter(request.execution_units - sum(v for k, v in data["spent"].items() if k != "search"))
            search = Meter(request.search_units - data["spent"]["search"])
            try:
                self._table(cases, execution, search, rows, request.measurement_epoch)
                totals = self._totals(rows, search)
                if not totals:
                    raise ValueError("no exact method on complete packages")
                incumbent = "000000"
                if supplied is None:
                    selected = self._select(totals, search, "development-minimum-comparison")
                    manifest = {
                        "program": AuditProgram.model_validate(
                            dict(zip(AXES, (c == "1" for c in selected), strict=True))
                        ).model_dump(),
                        "selected": selected,
                        "binding": data["binding_digest"],
                        "confirmation_digest": request.confirmation_digest,
                        "measurement_epoch": request.measurement_epoch,
                        "instrument_digest": request.instrument_digest,
                        "development_totals": totals,
                    }
                    data["freeze"] = {"manifest": manifest, "digest": digest("source-audit-freeze", manifest)}
                    data["state"] = "frozen"
                else:
                    chosen = data["freeze"]["manifest"]["selected"]
                    hand = "111111"
                    oracle = self._oracle(rows, search)
                    search.charge("search", 1, "frozen-candidate-validity")
                    valid = chosen in totals
                    strongest = self._select(totals, search, "control-minimum-comparison")
                    decision, beats = "reject-frozen-candidate", False
                    if valid:
                        search.charge("search", 1, "frozen-oracle-comparison")
                        beats = totals[chosen] < oracle
                        retain_incumbent = False
                        if incumbent in totals:
                            search.charge("search", 1, "incumbent-candidate-comparison")
                            retain_incumbent = totals[incumbent] <= totals[chosen]
                        if retain_incumbent:
                            decision = "retain-incumbent"
                        else:
                            search.charge("search", 1, "strong-control-candidate-comparison")
                            decision = (
                                "retain-stronger-control"
                                if totals[strongest] < totals[chosen]
                                else "candidate-supported-on-finite-captures"
                            )
                    data["confirmation"]["complete"] = True
                    data["result"] = {
                        "decision": decision,
                        "selected": chosen,
                        "hand_engineered": hand,
                        "strongest_control": strongest,
                        "valid_totals": totals,
                        "automated_units": totals.get(chosen),
                        "unrestricted_oracle_units": oracle,
                        "beats_unrestricted": beats,
                        "native_v1_compatible": False,
                        "authority_granted": False,
                        "scope": (
                            "public constructed finite source captures; "
                            "no independent campaign sampling or software-wide advantage"
                        ),
                        "oracle_reuse": "all64 methods actually executed; oracle reuses retained costs and artifacts",
                        "unknown_costs": COST_RULE["excluded"],
                    }
                    data["state"], data["approval"] = "completed", None
            except (BudgetExhausted, ValueError, RecursionError):
                data["state"], data["approval"] = "completed", None
                data["result"] = {
                    "decision": "retain-incumbent",
                    "reason": "incomplete-or-invalid-comparison",
                    "metrics": None,
                }
            for category, units in execution.costs.items():
                data["spent"][category] += units
            data["spent"]["search"] += search.used
            for event, count in search.trace.items():
                trace = data.setdefault("search_trace", {})
                trace[event] = trace.get(event, 0) + count
            if data["result"] is not None:
                data["result"]["full_campaign_units"] = sum(data["spent"].values())
            return self.journal.append(cx, self._key(campaign_id), data)

    def freeze(self, campaign_id: str) -> dict[str, Any]:
        return self._phase(campaign_id, None, None)

    def confirm(self, campaign_id: str, packages: list[SourcePackage], freeze_digest: str) -> dict[str, Any]:
        return self._phase(campaign_id, packages, freeze_digest)

    def envelope(self, campaign_id: str) -> dict[str, Any]:
        record = self.show(campaign_id)
        data = Journal.document(record)
        data["approval"] = None
        return {
            "schema": SCHEMA,
            "campaign": data,
            "journal_checkpoint": {
                "identity": self.journal.identity,
                "revision": record["revision"],
                "digest": record["digest"],
                "requires_original_journal_for_verification": True,
            },
            "authority": "none",
            "native_v1_compatible": False,
            "settlement": "none",
            "provenance": (
                "supplied immutable blob commitments; remote origin and public-use rights are not hash proofs"
            ),
        }
