"""Check the public practical input with independent graph/cover and Node references."""
from __future__ import annotations
import argparse
from collections import deque
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess

BASE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shortest_path(case, start, target):
    adjacency = {node: [] for node in case["nodes"]}
    for dependency, dependent in case["edges"]:
        adjacency[dependency].append(dependent)
    queue, parents = deque([start]), {start: None}
    while queue:
        current = queue.popleft()
        if current == target:
            result = []
            while current is not None:
                result.append(current)
                current = parents[current]
            return list(reversed(result))
        for following in sorted(adjacency[current]):
            if following not in parents:
                parents[following] = current
                queue.append(following)
    raise ValueError("declared illustrative lineage is absent")


def evaluate():
    case = json.loads((BASE / "case.json").read_text())
    audit_bytes = gzip.decompress((BASE / "graph_audit.json.gz").read_bytes())
    audit = json.loads(audit_bytes)
    audit_manifest = json.loads((BASE / "audit_manifest.json").read_text())
    if hashlib.sha256(audit_bytes).hexdigest() != audit_manifest["payload_sha256"] or len(audit_bytes) != audit_manifest["payload_bytes"]:
        raise ValueError("decompressed graph audit differs from its exact-byte manifest")
    reference_path = BASE.parent / "independent" / "reference.py"
    spec = importlib.util.spec_from_file_location("public_case_independent_reference", reference_path)
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    reference.validate_case(case)
    if any(test["cost"] <= 0 for test in case["tests"]):
        raise ValueError("coverage weights must be strictly positive")
    if case["study_role"] != "public_practical_acceptance_only_excluded_from_confirmation":
        raise ValueError("practical case must be excluded from confirmation")
    native = json.loads(subprocess.run(["node", str(BASE / "verify_node_resolution.cjs")], check=True, text=True, capture_output=True).stdout)
    results = reference.solve_batch(case)
    paths = []
    for start, target in [
        ("alpha-web::node_modules/vite", "alpha-web::<root>"),
        ("alpha-web::node_modules/react", "alpha-web::<root>"),
        ("alpha-web::node_modules/@babel/parser", "alpha-web::<root>"),
        ("manager::ui/vendor/zod", "manager::<root>"),
    ]:
        chain = shortest_path(case, start, target)
        source_edges = []
        for dependency, dependent in zip(chain, chain[1:]):
            matching = [row for row in audit["resolved_dependency_records"] if row["dependency"] == dependency and row["dependent"] == dependent]
            if not matching:
                raise ValueError("path has no exact source declaration")
            source_edges.extend(matching)
        paths.append({"start": start, "target": target, "nodes": chain, "source_declarations": source_edges})
    # Acceptance is structural: the source declares a dependency on these build
    # roots. It is not a claim that a change breaks a build or that tests are safe.
    for index, query in enumerate(case["queries"]):
        expected = sorted({node.split("::", 1)[0] + "::<root>" for node in query})
        if results[index]["affected"] != expected:
            raise ValueError("walkthrough root acceptance failed at query " + str(index))
    tracked = [BASE / "parser.py", BASE / "acceptance.py", BASE / "verify_node_resolution.cjs", BASE / "case.json", BASE / "graph_audit.json.gz", BASE / "audit_manifest.json", BASE / "source_receipt.json", reference_path]
    tracked += sorted((BASE / "raw").glob("*.json"))
    return {
        "schema": "bloom-public-practical-acceptance/v1", "status": "PASS",
        "scope": "Pinned public lock-map structure, independent impact and exact synthetic cover; excluded from confirmatory results.",
        "acceptance_criteria": ["All source hashes verified by parser --check.", "Every declared root/build dependency, optional declaration, peer declaration and link matches native Node ancestry or an explicit unresolved record.", "Case edges equal the independently reconstructed source edge set.", "Every fixed query has the expected project-root impact under independent BFS.", "Independent exhaustive subset enumeration supplies expected synthetic-cover outputs for downstream candidate comparison; weights are positive; no actual test-safety claim.", "Illustrative dependency lineages have exact source-declaration receipts."],
        "environment": {"python": platform.python_version(), "node": native.pop("node")},
        "native_resolution_check": native, "counts": audit["counts"],
        "decompressed_audit_sha256": hashlib.sha256(audit_bytes).hexdigest(),
        "query_results": [{"query_index": i, "changed": query, **result} for i, (query, result) in enumerate(zip(case["queries"], results))],
        "lineage_paths": paths,
        "artifact_sha256": {str(path.relative_to(BASE.parent)): digest(path) for path in tracked},
        "real_regression_safety": "not_established", "cash_or_customer_acceptance": "not_claimed",
        "coverage_cost_unit": "synthetic_coverage_weight",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Recompute acceptance and compare existing evidence, permitting different runtime versions.")
    args = parser.parse_args()
    # Rebuild exact canonical outputs in check mode before independent checks.
    subprocess.run([__import__("sys").executable, str(BASE / "parser.py"), "--check"], check=True)
    receipt = evaluate()
    destination = BASE / "acceptance.json"
    if args.check:
        previous = json.loads(destination.read_text())
        previous.pop("environment", None)
        observed = dict(receipt)
        observed.pop("environment", None)
        if previous != observed:
            raise SystemExit("FAIL: acceptance results or bound source bytes differ")
    else:
        destination.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "queries": len(receipt["query_results"]), "native_records": receipt["native_resolution_check"]["checked_records"], "real_regression_safety": receipt["real_regression_safety"], "acceptance_sha256": digest(destination)}, sort_keys=True))


if __name__ == "__main__":
    main()
