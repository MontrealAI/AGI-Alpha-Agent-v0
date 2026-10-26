# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast
import hashlib
import inspect
import json

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def select(tree, symbol):
    body = tree.body
    for name in symbol.split("."):
        matches = [n for n in body if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
        if len(matches) != 1:
            raise ValueError((symbol, len(matches)))
        node = matches[0]
        body = node.body
    return node


def signature(node):
    args = node.args
    positional = args.posonlyargs + args.args
    required = len(positional) - len(args.defaults)
    params = [inspect.Parameter(n.arg, inspect.Parameter.POSITIONAL_ONLY if i < len(args.posonlyargs)
                                else inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                default=inspect.Parameter.empty if i < required else None)
              for i, n in enumerate(positional)]
    if args.vararg:
        params.append(inspect.Parameter(args.vararg.arg, inspect.Parameter.VAR_POSITIONAL))
    params.extend(inspect.Parameter(n.arg, inspect.Parameter.KEYWORD_ONLY,
                                   default=inspect.Parameter.empty if default is None else None)
                  for n, default in zip(args.kwonlyargs, args.kw_defaults))
    if args.kwarg:
        params.append(inspect.Parameter(args.kwarg.arg, inspect.Parameter.VAR_KEYWORD))
    return inspect.Signature(params)


MANUAL = {
    "F01": [(724, 8, "click.echo", 1, "echo", None), (727, 8, "click.echo", 1, "echo", None)],
    "F02": [(20, 18, "style", 2, "style", "EXPANDED_ARGUMENTS"), (21, 4, "echo", 1, "echo", None),
            (29, 18, "style", 2, "style", "EXPANDED_ARGUMENTS"), (30, 4, "echo", 1, "echo", None)],
    "F03": [(336, 21, "sp.sparse.linalg.eigs", 7, "eigs", None), (340, 36, "sp.linalg.norm", 2, "norm", None)],
    "F04": [(130, 11, "httpx.Client", 1, "Client.__init__", "UNSUPPORTED_RECEIVER"),
            (133, 16, "httpx.Timeout", 2, "Timeout.__init__", "UNSUPPORTED_RECEIVER"),
            (141, 11, "httpx.AsyncClient", 1, "AsyncClient.__init__", "UNSUPPORTED_RECEIVER"),
            (144, 16, "httpx.Timeout", 2, "Timeout.__init__", "UNSUPPORTED_RECEIVER")],
}
summary = []
for tid, manual in MANUAL.items():
    task = json.loads((ROOT / "tasks" / (tid + ".json")).read_text())
    text = task["sources"]["consumer"]["text"]
    tree = ast.parse(text)
    scopes = [select(tree, s) for s in task["consumer"]["scopeSymbols"]]
    calls = [n for scope in scopes for n in ast.walk(scope) if isinstance(n, ast.Call)]
    rows = []
    for line, column, callee, source_index, symbol, unsupported in manual:
        call = next(n for n in calls if (n.lineno, n.col_offset, ast.unparse(n.func)) == (line, column, callee))
        row = {"line": line, "column": column, "callee": callee,
               "consumer_sha256": task["sources"]["consumer"]["sha256"],
               "snippet_sha256": hashlib.sha256(ast.get_source_segment(text, call).encode()).hexdigest(),
               "unsupported_reason": unsupported, "targets": {}, "independent_argument_acceptance": {}}
        for side, prefix in [("before", "b"), ("after", "a")]:
            sid = prefix + str(source_index)
            source = task["sources"][sid]
            node = select(ast.parse(source["text"]), symbol)
            sig = signature(node)
            row["targets"][side] = {"source": sid, "symbol": symbol, "sha256": source["sha256"],
                                    "declaration_line": node.lineno, "declaration_end_line": node.end_lineno,
                                    "decorators": [ast.unparse(n) for n in node.decorator_list], "signature": str(sig)}
            if unsupported:
                row["independent_argument_acceptance"][side] = None
            else:
                assert not node.decorator_list
                assert not any(isinstance(n, ast.Starred) for n in call.args)
                assert not any(n.arg is None for n in call.keywords)
                try:
                    sig.bind(*([object()] * len(call.args)), **{n.arg: object() for n in call.keywords})
                    row["independent_argument_acceptance"][side] = True
                except TypeError as exc:
                    row["independent_argument_acceptance"][side] = False
                    row.setdefault("argument_binding_error", {})[side] = str(exc)
        before, after = [row["independent_argument_acceptance"][side] for side in ("before", "after")]
        row["expected_core_scope_outcome"] = ("UNRESOLVED" if unsupported else "BINDING_CONFLICT" if before and not after
                                               else "BINDING_PRESERVED" if before and after else "UNRESOLVED")
        row["mapping_scope"] = "Nominal captured declaration under standard imports, no monkeypatching and relevant path execution. Binding does not establish runtime identity, successful argument evaluation, behavior, security or deployment readiness."
        rows.append(row)
    selected = {(r["line"], r["column"], r["callee"]) for r in rows}
    excluded = []
    for call in calls:
        key = call.lineno, call.col_offset, ast.unparse(call.func)
        if key not in selected:
            reason = "Builtin, consumer/other-library helper or decorator, not a call to the registered dependency."
            if tid == "F03" and key[2] in ["eigenvector.flatten", "largest.sum"]:
                reason = "The captured eigs return documentation specifies NumPy ndarray eigenvectors. Flatten and sum here operate on returned numerical data, not a SciPy-defined receiver. This NumPy/data operation is outside the registered SciPy call inventory."
            excluded.append({"line": key[0], "column": key[1], "callee": key[2], "reason": reason})
    out = {"schema": "alpha-transfer-independent-oracle/v1", "id": tid,
           "canonical_input_sha256": hashlib.sha256(canonical(task)).hexdigest(),
           "oracle_owner": "Separate same-session production audit; not institutional replication",
           "basis": "Manual whole-scope inventory plus independent inert Python signature reconstruction; no candidate outcome or inspected package execution.",
           "calls": rows, "nondependency_scope_calls": excluded, "complete_call_count": len(rows),
           "accepted_truthful_assessment": "Complete exact inventory, valid conditional targets or substantiated abstention, independent binding agreement, and separately checked complete bilingual handoff."}
    with (ROOT / "oracle" / (tid + ".json")).open("x") as handle:
        handle.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    summary.append({"task": tid, "calls": len(rows), "status_counts": {
        s: sum(r["expected_core_scope_outcome"] == s for r in rows)
        for s in ("BINDING_PRESERVED", "BINDING_CONFLICT", "UNRESOLVED")}})
with (ROOT / "oracle/summary.json").open("x") as handle:
    handle.write(json.dumps(summary, indent=2) + "\n")
print("Four independent source oracle records built, retained from all constructor/extractor roles.")
