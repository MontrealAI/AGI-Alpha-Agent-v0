# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
records = json.loads((ROOT / "source-identities-final.json").read_text())
by_source = {(r["refId"], r["path"]): r for r in records}
by_id = {r["id"]: r for r in records}


def source(row):
    return {"repository": row["repository"], "commit": row["commit"], "path": row["path"],
            "sha256": row["sha256"], "text": (ROOT / row["file"]).read_text()}


click_paths = ["src/click/__init__.py", "src/click/utils.py", "src/click/termui.py"]
scipy_paths = ["scipy/__init__.py", "scipy/linalg/__init__.py", "scipy/linalg/_misc.py",
               "scipy/sparse/__init__.py", "scipy/sparse/linalg/__init__.py",
               "scipy/sparse/linalg/_eigen/__init__.py", "scipy/sparse/linalg/_eigen/arpack/__init__.py",
               "scipy/sparse/linalg/_eigen/arpack/arpack.py"]
httpx_paths = ["httpx/__init__.py", "httpx/_client.py", "httpx/_config.py"]
selection = [
    {"id": "F01", "consumerId": "consumer-flask", "scopes": ["show_server_banner"],
     "package": "click", "before": ["click-before", "8.1.7"], "after": ["click-after", "8.2.1"],
     "providers": click_paths, "title": "Flask startup banner across the Click 8.1.7 to 8.2.1 transition",
     "purpose": "Assess every Click call in the real Flask development-server banner, including conditional app/debug output. Identify the precise argument or runtime evidence needed before relying on this CLI output under the target version."},
    {"id": "F02", "consumerId": "consumer-black", "scopes": ["_out", "_err"],
     "package": "click", "before": ["click-before", "8.1.7"], "after": ["click-after", "8.2.1"],
     "providers": click_paths, "title": "Black output and error formatting across the Click transition",
     "purpose": "Review the complete Click-call intake for Black's paired internal output/error helpers as one maintenance question. Preserve formatting-argument uncertainty and distinguish it from declaration binding; no terminal or formatter process is executed."},
    {"id": "F03", "consumerId": "consumer-networkx", "scopes": ["eigenvector_centrality_numpy"],
     "package": "scipy", "before": ["scipy-110", "1.10.1"], "after": ["scipy-after", "1.14.1"],
     "providers": scipy_paths, "title": "NetworkX eigenvector centrality across the SciPy transition",
     "purpose": "Review every SciPy call in the real NumPy-backed eigenvector-centrality implementation. Separate the upstream solver and normalization contracts from numerical convergence, graph behavior and operations belonging to other libraries."},
    {"id": "F04", "consumerId": "consumer-huggingface", "scopes": ["default_client_factory", "default_async_client_factory"],
     "package": "httpx", "before": ["httpx-before", "0.27.2"], "after": ["httpx-after", "0.28.1"],
     "providers": httpx_paths, "title": "Hugging Face Hub default HTTP client factories across the HTTPX transition",
     "purpose": "Review both real synchronous/asynchronous default client factories as one integration component. Include nested dependency construction. Identify what constructor, timeout, hook or runtime evidence remains necessary without sending any request."},
]

(ROOT / "tasks").mkdir(exist_ok=True)
for item in selection:
    consumer = by_id[item["consumerId"]]
    sources = {"consumer": source(consumer)}
    sides = {}
    for side, prefix in [("before", "b"), ("after", "a")]:
        ref_id, version = item[side]
        sides[side] = []
        for index, path in enumerate(item["providers"]):
            ident = prefix + str(index)
            sources[ident] = source(by_source[ref_id, path])
            sides[side].append(ident)
    used_refs = {consumer["refId"], item["before"][0], item["after"][0]}
    licenses = [{k: r[k] for k in ["repository", "commit", "path", "sha256", "bytes", "file"]}
                for r in records if r["refId"] in used_refs and "license" in r["path"].lower()]
    task = {"schema": "alpha-transfer-raw-task/v1", "id": item["id"], "title": item["title"],
            "purpose": item["purpose"], "dependency": {"package": item["package"], "importRoots": [item["package"]],
            "before": {"version": item["before"][1]}, "after": {"version": item["after"][1]}},
            "consumer": {"source": "consumer", "scopeSymbols": item["scopes"]}, "sources": sources,
            "providerSides": sides, "licenseRecords": licenses}
    assert 2 <= len(sources) <= 24
    assert all(hashlib.sha256(s["text"].encode()).hexdigest() == s["sha256"] for s in sources.values())
    with (ROOT / "tasks" / (item["id"] + ".json")).open("x") as handle:
        handle.write(json.dumps(task, ensure_ascii=False, indent=2) + "\n")
with (ROOT / "task-selection.json").open("x") as handle:
    handle.write(json.dumps(selection, ensure_ascii=False, indent=2) + "\n")
print("Four raw tasks built; no candidate executed or inputs released.")
