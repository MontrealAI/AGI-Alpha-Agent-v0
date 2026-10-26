"""Serialize this curator's manually reasoned, task-specific selectors.

This is not a reusable source extractor. No inspected source is executed.
No binding/assessment outcome is computed here.
"""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent

# Every selector below was chosen by source inspection before this file ran.
# Columns are CPython AST UTF-8 column offsets; callee is ast.unparse(call.func).
SELECTORS = {
    "T01": [
        (43, 12, "httpx.URL", "b2", "URL.__init__", "a2", "URL.__init__",
         "Consumer line 29 locally imports httpx. Captured httpx/__init__.py imports _urls at line 12 and lists URL in __all__; both _urls.py files define URL.__init__ at line 77. This is a declared constructor target. Local-import/export resolution and class construction are not runtime identity or dispatch proofs."),
        (45, 9, "httpx.Client", "b1", "Client.__init__", "a1", "Client.__init__",
         "Consumer line 29 locally imports httpx. Both captured package initializers import _client at line 4 and list Client; _client.__all__ also lists Client. The explicit constructors are Client.__init__ at before line 628 and after line 639. Class construction and runtime export identity are not proved by this declared target."),
        (53, 17, "client.stream", "b1", "Client.stream", "a1", "Client.stream",
         "Consumer line 45 binds client through with httpx.Client(...). Captured Client.__enter__ returns self (before line 1304, after line 1291). Client.stream is defined at before line 840 and after line 828 and decorated with contextmanager. This is a source-supported receiver target; actual receiver identity, descriptor dispatch and decorator behavior remain unverified."),
        (64, 16, "response.raise_for_status", "b3", "Response.raise_for_status", "a3", "Response.raise_for_status",
         "Consumer line 53 binds response from client.stream. Both captured Client.stream declarations advertise Iterator[Response], assign response = self.send(...) and yield response; Client.send advertises Response and _client imports Response from _models. Selected Response.raise_for_status definitions begin at before line 728 and after line 794. Return annotations/source flow are evidence for a declared target, not proof of runtime identity or receiver dispatch."),
        (65, 19, "response.headers.get", "b3", "Headers.get", "a3", "Headers.get",
         "The response receiver is source-associated with HTTPX Response through the captured Client.stream body and annotations. Response.__init__ assigns self.headers = Headers(headers) in both captured _models.py files; Headers.get is defined at before line 170 and after line 242. This declared attribute receiver chain is not a runtime identity or descriptor-dispatch proof."),
        (68, 29, "response.iter_raw", "b3", "Response.iter_raw", "a3", "Response.iter_raw",
         "Consumer response is bound from client.stream at line 53; captured stream yields the self.send result and advertises Iterator[Response], while send advertises Response. Explicit Response.iter_raw definitions begin at before line 869 and after line 935. This declared method target preserves the source-supported relationship without asserting runtime receiver identity or descriptor dispatch."),
    ],
    "T02": [
        (755, 8, "super().__init__", "b1", "Client.__init__", "a1", "Client.__init__",
         "Consumer line 750 declares _DefaultHttpxClient(httpx.Client), with httpx imported at line 36. Both captured package initializers export Client through _client. The super().__init__(**kwargs) call is declared against the captured Client.__init__ definitions. Inheritance/runtime dispatch and the contents of expanded kwargs are not established by source selection; no keywords are invented."),
        (1335, 8, "super().__init__", "b1", "AsyncClient.__init__", "a1", "AsyncClient.__init__",
         "Consumer line 1330 declares _DefaultAsyncHttpxClient(httpx.AsyncClient), with httpx imported at line 36. Both captured package initializers export AsyncClient through _client. The super().__init__(**kwargs) call is declared against captured AsyncClient.__init__ definitions. Inheritance/runtime dispatch and the contents of expanded kwargs are not established by source selection; no keywords are invented."),
    ],
    "T03": [
        (330, 52, "linalg.eigh", "b0", "eigh", "a0", "eigh",
         "Consumer line 9 imports linalg from scipy. Captured scipy/linalg/__init__.py imports ._decomp at line 200 on both sides; each _decomp.__all__ lists eigh, defined at before line 267 and after line 270. This captured export path supports the declared eigh target. Public-module re-exports and uncaptured modules do not establish runtime object identity; the unchanged core's direct-import path does not resolve this re-export."),
        (335, 52, "eigsh", "b2", "eigsh", "a2", "eigsh",
         "Consumer line 10 imports eigsh from scipy.sparse.linalg. Both captured sparse/linalg initializers import _eigen at line 123; _eigen imports .arpack at line 9 and includes eigsh in __all__; arpack/__init__.py imports .arpack at line 20. arpack.py includes eigsh in __all__ and defines it at before line 1350 and after line 1357. This source export chain supports a declared target, not runtime identity or the unchanged core's direct-import mapping."),
    ],
    "T04": [
        (330, 52, "linalg.eigh", "b0", "eigh", "a0", "eigh",
         "Consumer line 9 imports linalg from scipy. Captured scipy/linalg/__init__.py imports ._decomp at before line 200 and after line 206; each _decomp.__all__ lists eigh, defined at before line 270 and after line 283. This captured export path supports the declared eigh target. Public-module re-exports and uncaptured modules do not establish runtime object identity; the unchanged core's direct-import path does not resolve this re-export."),
        (335, 52, "eigsh", "b2", "eigsh", "a2", "eigsh",
         "Consumer line 10 imports eigsh from scipy.sparse.linalg. Captured sparse/linalg initializers import _eigen at before line 123 and after line 132; _eigen imports .arpack at line 9 and includes eigsh in __all__; arpack/__init__.py imports .arpack at line 20. arpack.py includes eigsh in __all__ and defines it at before line 1357 and after line 1360. This source export chain supports a declared target, not runtime identity or the unchanged core's direct-import mapping."),
    ],
    "T05": [
        (176, 42, "eigsh", "b2", "eigsh", "a2", "eigsh",
         "Consumer line 12 imports eigsh from scipy.sparse.linalg. Captured sparse/linalg initializers import _eigen at before line 123 and after line 132; _eigen imports .arpack at line 9 and includes eigsh in __all__; arpack/__init__.py imports .arpack at line 20. arpack.py includes eigsh in __all__ and defines it at before line 1357 and after line 1360. This captured chain supports a declared target, not runtime object identity or the unchanged core's direct-import mapping."),
        (192, 38, "eigh", "b0", "eigh", "a0", "eigh",
         "Consumer line 10 imports eigh from scipy.linalg. Captured scipy/linalg/__init__.py imports ._decomp at before line 200 and after line 206; each _decomp.__all__ lists eigh, defined at before line 270 and after line 283. This captured export path supports the declared target. Runtime export identity is not proved, and the unchanged core's direct-import mapping does not follow this re-export."),
    ],
    "T06": [
        (259, 12, "simpson", "b0", "simpson", "a0", "simpson",
         "Consumer locally tries from scipy.integrate import simpson at line 249, with an ImportError fallback importing simps as simpson at line 252. Both specified source versions expose simpson: integrate/__init__.py imports _quadrature (before line 91, after line 94), whose __all__ includes simpson and whose explicit definitions begin at before line 536 and after line 535. The selection uses this present simpson export on both sides. The conditional local import and uncaptured import execution remain limitations; no runtime branch or fallback identity is invented."),
    ],
}

NOTES = {
    "T01": [
        "All explicit dependency-related Call nodes in evaluate_agent are selected, including the Headers.get call within a larger .lower() expression.",
        "The outer .lower() is associated with the string result: Headers.get returns self[key] or the supplied default, Headers.__getitem__ is annotated str, and this call supplies a literal string default. It is not selected as a separate HTTPX declaration.",
        "httpx.URL(...).host is an attribute/property access, not a separate explicit Call node. Implicit with/iteration protocol calls are not invented as explicit selected calls.",
        "Other explicit calls are Python builtins, stdlib functions, consumer-local/runtime configuration, or methods on input/decoded JSON objects. No claim is made about network behavior or provider contact.",
    ],
    "T02": [
        "Each requested initializer scope has one explicit inherited initializer call. The nested super() builtin and kwargs.setdefault calls are not extra dependency calls.",
        "The exact **kwargs expansions are preserved. Defaults set in surrounding source do not disclose every runtime key or justify materializing a different call.",
    ],
    "T03": [
        "Both SciPy solver branches in KernelPCA._fit_transform are represented.",
        "_randomized_eigsh and _init_arpack_v0 are imported from sklearn relatives; their internal transitive calls are outside the named source scope. Array operations and sklearn utilities are not added as SciPy calls.",
    ],
    "T04": [
        "The consumer source is byte-identical to T03; its two SciPy call locations are retained, with this task's distinct before/after source sets.",
        "Only the specified direct scope is inventoried; transitive sklearn helper internals are not inferred.",
    ],
    "T05": [
        "Both explicitly imported SciPy solver calls in null_space are represented.",
        "M.toarray at consumer line 191 is guarded by hasattr and M is an untyped function parameter accepting several documented object forms. The captured source does not identify a concrete dependency receiver/class for that duck-typed operation. It is not asserted to be a specific SciPy declaration.",
        "Calls imported from sklearn, numpy array operations, hasattr and exception construction are not separate SciPy API calls in this scope.",
    ],
    "T06": [
        "The single explicit imported integration call is selected once. Both specified provider versions capture simpson and the export path used by the try import.",
        "The ImportError fallback is retained as an explicit limitation. An absent after-side simps fallback is not substituted for the present simpson definition; no execution of imports was attempted.",
        "smoother.transform is a method on a passed consumer smoother, and _get_integration_points is consumer-local; neither is selected as an upstream SciPy declaration.",
    ],
}


def main() -> None:
    started = datetime.now(timezone.utc).isoformat()
    observations = {
        "schema": "agi-alpha-curator-source-observations/v1",
        "arm": "A",
        "authorship": "Current-session AI curator; not observed human labor",
        "method": "Manual source inspection with ordinary stdlib AST location listings; hard-coded selector materialization only",
        "limitations": [
            "No inspected consumer or provider source was executed.",
            "No external network was used.",
            "No B compiler, C extractor, other-arm response/result, production audit or oracle was read.",
            "No core assessment, binding, critic or verifier outcome was executed during selection.",
            "Source relationship declarations do not establish runtime object identity or behavior.",
        ],
        "tasks": {},
        "materializationStartedUtc": started,
    }
    hashes = {}
    for task, tuples in SELECTORS.items():
        raw_path = ROOT / "inputs" / f"{task}.json"
        raw_bytes = raw_path.read_bytes()
        raw = json.loads(raw_bytes)
        source = raw["sources"][raw["consumer"]["source"]]["text"]
        consumer_tree = ast.parse(source)
        selected_calls = []
        selected_observations = []
        for index, (line, col, callee, bsrc, bsym, asrc, asym, explanation) in enumerate(tuples, 1):
            nodes = [n for n in ast.walk(consumer_tree) if isinstance(n, ast.Call)
                     and (n.lineno, n.col_offset, ast.unparse(n.func)) == (line, col, callee)]
            assert len(nodes) == 1, (task, line, col, callee)
            c = nodes[0]
            selected_calls.append({
                "id": f"{task}-call-{index:02d}",
                "consumer": raw["consumer"]["source"],
                "line": line,
                "column": col,
                "callee": callee,
                "before": {"source": bsrc, "symbol": bsym},
                "after": {"source": asrc, "symbol": asym},
                "mapping": {"kind": "declared-target", "explanation": explanation},
            })
            declaration_observations = {}
            for side, ident, symbol in (("before", bsrc, bsym), ("after", asrc, asym)):
                text = raw["sources"][ident]["text"]
                body = ast.parse(text).body
                for part in symbol.split("."):
                    matches = [n for n in body if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == part]
                    assert len(matches) == 1, (task, ident, symbol)
                    node = matches[0]
                    body = node.body
                assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                declaration_observations[side] = {
                    "source": ident, "symbol": symbol, "line": node.lineno,
                    "endLine": node.end_lineno,
                    "decorators": [ast.unparse(n) for n in node.decorator_list],
                    "header": "\n".join(text.splitlines()[node.lineno - 1:node.body[0].lineno - 1]),
                }
            selected_observations.append({
                "id": selected_calls[-1]["id"], "line": line, "column": col,
                "callee": callee, "callText": ast.get_source_segment(source, c),
                "declarations": declaration_observations,
                "relationship": explanation,
            })
        scope_observations = []
        for symbol in raw["consumer"]["scopeSymbols"]:
            body = consumer_tree.body
            for part in symbol.split("."):
                node = next(n for n in body if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == part)
                body = node.body
            scope_observations.append({
                "symbol": symbol, "line": node.lineno, "endLine": node.end_lineno,
                "text": ast.get_source_segment(source, node),
                "allExplicitCallLocations": [
                    {"line": n.lineno, "column": n.col_offset, "callee": ast.unparse(n.func)}
                    for n in sorted((n for n in ast.walk(node) if isinstance(n, ast.Call)), key=lambda n: (n.lineno, n.col_offset))
                ],
            })
        pack = {
            "schema": "alpha-upgrade-call-request/v1",
            "id": raw["id"], "title": raw["title"], "purpose": raw["purpose"],
            "sources": raw["sources"], "calls": selected_calls,
            "historicalEvidence": [], "recordedChecks": [],
        }
        encoded = (json.dumps(pack, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
        first_path = DEST / f"{task}.request.first-attempt.json"
        final_path = DEST / f"{task}.request.json"
        assert not first_path.exists() and not final_path.exists(), "preserve existing attempts"
        first_path.write_bytes(encoded)
        final_path.write_bytes(encoded)
        hashes[task] = hashlib.sha256(encoded).hexdigest()
        observations["tasks"][task] = {
            "rawInputSha256": hashlib.sha256(raw_bytes).hexdigest(),
            "sourceHashes": {k: v["sha256"] for k, v in raw["sources"].items()},
            "scope": scope_observations, "selected": selected_observations,
            "selectionNotes": NOTES[task],
            "missingCapturedTargetCount": 0,
        }
    observations["materializationFinishedUtc"] = datetime.now(timezone.utc).isoformat()
    (DEST / "source-observations.json").write_text(json.dumps(observations, indent=2, ensure_ascii=False) + "\n")
    (DEST / "supplemental-missing-evidence.json").write_text(json.dumps({
        "schema": "agi-alpha-curator-supplemental-evidence/v1", "arm": "A",
        "missingCapturedTargetCount": 0, "missingTargets": [],
        "note": "All selected, source-associated dependency call targets have captured declarations. Conditional imports, export identity, descriptors, receiver identity and untyped parameter operations are limitations recorded separately in source observations, not invented target identities.",
    }, indent=2) + "\n")
    print(json.dumps({"materializedUtc": observations["materializationFinishedUtc"], "requestHashes": hashes}, indent=2))


if __name__ == "__main__":
    main()
