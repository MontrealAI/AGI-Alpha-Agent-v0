"""Build a bounded dependency-impact fixture from exact public npm lock snapshots.

No installation, package scripts, network, or arbitrary repository code is run.
Edges are declared package dependencies at locked installation locations, oriented
dependency -> dependent. They are not observed imports or executable build edges.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
PROJECTS = (
    ("alpha-web", "alpha-web-package-lock.json"),
    ("manager", "manager-package-lock.json"),
)
OUTPUTS = ("case.json", "graph_audit.json.gz", "audit_manifest.json")


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def compressed(data):
    stream = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=stream, mode="wb", mtime=0, compresslevel=9) as target:
        target.write(data)
    return stream.getvalue()


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def node_id(project, location):
    return project + "::" + (location or "<root>")


def validate_location(location):
    if not isinstance(location, str) or "\\" in location:
        raise ValueError("lock locations must be relative POSIX paths")
    if location and (location.startswith("/") or any(x in ("", ".", "..") for x in location.split("/"))):
        raise ValueError("unsafe or noncanonical lock location: " + location)


def lookup_locations(from_location, dependency_name):
    """Node-style node_modules ancestry, confined to one lockfile's root.

    Scoped directory segments remain intact: scope directories participate in
    ancestry, while a node_modules segment does not acquire node_modules twice.
    Request aliases retain their manifest key, matching installation locations.
    """
    validate_location(from_location)
    parts = dependency_name.split("/")
    if not dependency_name or any(x in ("", ".", "..") for x in parts) or "\\" in dependency_name:
        raise ValueError("invalid dependency name: " + dependency_name)
    if (dependency_name.startswith("@") and len(parts) != 2) or (not dependency_name.startswith("@") and len(parts) != 1):
        raise ValueError("unsupported dependency name: " + dependency_name)
    directories = from_location.split("/") if from_location else []
    result = []
    for length in range(len(directories), -1, -1):
        prefix = directories[:length]
        if prefix and prefix[-1] == "node_modules":
            continue
        result.append("/".join(prefix + ["node_modules", dependency_name]))
    return result


def declarations(metadata, is_root):
    fields = ["dependencies", "optionalDependencies", "peerDependencies"]
    if is_root:
        fields.append("devDependencies")
    names = sorted({name for field in fields for name in metadata.get(field, {})})
    for name in names:
        constraints = {field: metadata[field][name] for field in fields if name in metadata.get(field, {})}
        peer_optional = bool(metadata.get("peerDependenciesMeta", {}).get(name, {}).get("optional", False))
        # npm optionalDependencies override a same-named ordinary dependency.
        optional = "optionalDependencies" in constraints or (
            set(constraints) == {"peerDependencies"} and peer_optional
        )
        yield name, constraints, optional, peer_optional


def package_name(location, metadata):
    if metadata.get("name"):
        return metadata["name"]
    if "node_modules/" in location:
        return location.rsplit("node_modules/", 1)[1]
    return location


def read_verified_sources(base):
    receipt = json.loads((base / "source_receipt.json").read_text())
    by_file = {entry["filename"]: entry for entry in receipt["files"]}
    all_locks = {}
    verified = []
    for filename, entry in sorted(by_file.items()):
        data = (base / "raw" / filename).read_bytes()
        expected = entry.get("verified_git_blob", entry.get("tree", {}).get("sha"))
        if git_blob(data) != expected or sha256(data) != entry["sha256"] or len(data) != entry["bytes"]:
            raise ValueError("source bytes do not match recorded Git blob/SHA256: " + filename)
        lock = json.loads(data)
        if lock.get("lockfileVersion") != 3 or not isinstance(lock.get("packages"), dict) or "" not in lock["packages"]:
            raise ValueError("fixture requires an npm lockfileVersion 3 packages map")
        for location in lock["packages"]:
            validate_location(location)
        all_locks[filename] = lock
        verified.append({key: entry[key] for key in ("filename", "repo", "path", "commit", "url", "bytes", "sha256", "verified_git_blob")})
    return all_locks, verified


def construct(base=BASE):
    locks, verified = read_verified_sources(base)
    nodes, edges, node_records, edge_records, unresolved = [], set(), [], [], []
    omitted_transitive_dev = []
    root_records = []
    for project, filename in PROJECTS:
        lock = locks[filename]
        packages = lock["packages"]
        root_records.append({"project": project, "node": node_id(project, ""), "package_name": packages[""].get("name", lock.get("name")), "version": packages[""].get("version", lock.get("version")), "source": filename})
        for location, metadata in sorted(packages.items()):
            identifier = node_id(project, location)
            nodes.append(identifier)
            node_records.append({"id": identifier, "project": project, "lock_location": location,
                                 "name": package_name(location, metadata), "version": metadata.get("version"),
                                 "link": bool(metadata.get("link", False)), "resolved": metadata.get("resolved"),
                                 "dev": bool(metadata.get("dev", False)), "optional": bool(metadata.get("optional", False)),
                                 "os": metadata.get("os"), "cpu": metadata.get("cpu")})
            if metadata.get("link"):
                target = metadata.get("resolved")
                if not isinstance(target, str):
                    raise ValueError("link has no string target: " + identifier)
                validate_location(target)
                record = {"project": project, "from_lock_path": location, "kind": "link", "resolved_path": target if target in packages else None,
                          "declared_target": target, "dependent": identifier,
                          "dependency": node_id(project, target) if target in packages else None}
                (edge_records if target in packages else unresolved).append(record)
                if target in packages:
                    edges.add((node_id(project, target), identifier))
                continue
            if location and metadata.get("devDependencies"):
                omitted_transitive_dev.append({"project": project, "from_lock_path": location, "names": sorted(metadata["devDependencies"])})
            for name, constraints, optional, peer_optional in declarations(metadata, not location):
                candidates = lookup_locations(location, name)
                selected = next((candidate for candidate in candidates if candidate in packages), None)
                record = {"project": project, "from_lock_path": location, "kind": "package-declaration", "requested_name": name,
                          "constraints": constraints, "optional": optional, "peer_optional": peer_optional,
                          "resolved_path": selected, "dependent": identifier,
                          "dependency": node_id(project, selected) if selected is not None else None}
                if selected is None:
                    record["searched_locations"] = candidates
                    unresolved.append(record)
                else:
                    edges.add((node_id(project, selected), identifier))
                    edge_records.append(record)

    known = set(nodes)
    apps = [node_id(project, "") for project, _ in PROJECTS]
    # This sequence is a transparent practical walkthrough, never a confirmatory sample.
    requests = [
        ("alpha-web", ["vite"]), ("alpha-web", ["react"]),
        ("alpha-web", ["@babel/parser"]), ("alpha-web", ["rollup"]),
        ("alpha-web", ["vue"]), ("alpha-web", ["typescript"]),
        ("alpha-web", ["@vitejs/plugin-react"]), ("alpha-web", ["@vitejs/plugin-vue"]),
        ("alpha-web", ["cypress"]), ("alpha-web", ["@opentelemetry/api"]),
        ("manager", ["hardhat"]), ("manager", ["solc"]),
        ("manager", ["ethers"]), ("manager", ["@openzeppelin/contracts"]),
        ("manager", ["zod"]),
    ]
    queries = [[node_id(project, "node_modules/" + name) for name in names] for project, names in requests]
    queries += [[node_id("alpha-web", "node_modules/vite"), node_id("manager", "node_modules/solc")], []]
    if any(node not in known for query in queries for node in query):
        raise ValueError("predeclared walkthrough package is absent from pinned snapshot")
    tests = [
        {"id": "synthetic-alpha", "covers": [apps[0]], "cost": 7},
        {"id": "synthetic-manager", "covers": [apps[1]], "cost": 5},
        {"id": "synthetic-both", "covers": apps, "cost": 10},
    ]
    if len(nodes) > 2000:
        raise ValueError("public practical graph exceeds the declared 2,000-node envelope")
    case = {
        "schema": "bloom-dependency-case/v1", "id": "public-alpha-manager-locks-v1", "seed": 0,
        "topology": "public_npm_lock_installed_locations", "nodes": sorted(nodes), "edges": sorted(map(list, edges)),
        "applications": apps, "queries": queries, "changed": queries[0], "tests": tests,
        "coverage_cost_unit": "synthetic_coverage_weight", "real_regression_safety": "not_established",
        "study_role": "public_practical_acceptance_only_excluded_from_confirmation",
        "test_semantics": "Illustrative positive coverage weights; these are not executable tests, observed coverage, measured durations, prices, or economic savings.",
        "graph_semantics": "Declared npm lockfile dependencies, optional/peer declarations, and local links; dependency to dependent; runtime plus root development/build scope; no cross-project edges.",
        "application_semantics": "Two actual package-manifest build roots. No claim of complete source import, runtime, or build dependency reconstruction.",
        "source_snapshots": [{"project": project, "filename": filename,
                             "sha256": next(x["sha256"] for x in verified if x["filename"] == filename)} for project, filename in PROJECTS],
    }
    kind_counts = Counter(field for row in edge_records if row["kind"] == "package-declaration" for field in row["constraints"])
    missing_counts = Counter(field for row in unresolved if row["kind"] == "package-declaration" for field in row["constraints"])
    audit = {
        "schema": "bloom-public-dependency-audit/v1", "roots": root_records,
        "source_snapshots": verified, "included_projects": [project for project, _ in PROJECTS],
        "unused_snapshot": {"filename": "jobs-package-lock.json", "reason": "Verified source receipt only: its 2,605 package entries exceed this fixture's total 2,000-node cap. No Jobs graph edges are asserted."},
        "counts": {"nodes": len(nodes), "edges": len(edges), "applications": len(apps), "queries": len(queries), "synthetic_coverage_options": len(tests),
                   "resolved_records": len(edge_records), "unresolved_records": len(unresolved), "resolved_declaration_fields": dict(sorted(kind_counts.items())),
                   "unresolved_declaration_fields": dict(sorted(missing_counts.items())), "link_records": sum(row["kind"] == "link" for row in edge_records)},
        "node_records": node_records, "resolved_dependency_records": edge_records, "unresolved_dependency_records": unresolved,
        "omitted_transitive_dev_dependencies": omitted_transitive_dev,
        "limitations": [
            "Snapshot union, not a live npm install: OS/CPU/engine/optional conditions are recorded but not executed or filtered.",
            "Nearest node_modules ancestry is resolved within each project's exact lock map. Missing declarations remain unresolved; no packages are downloaded or invented.",
            "Peer declarations are included when a nearest location exists; semver peer compatibility is not evaluated.",
            "Transitive package devDependencies are omitted; root devDependencies are included because the task concerns package build roots.",
            "Local links use the lock's root-relative resolved target as a separate dependency-to-link edge. preserve-symlinks variants are not modeled.",
            "Dynamic imports, conditional exports, package self-reference, bundler aliases, optional runtime branches, generated files, source-level imports, and native build edges are not reconstructed.",
            "Each project's install locations are namespaced. Same-name packages across projects are not silently merged.",
            "Synthetic coverage options demonstrate the successor optimizer only; real regression-safety acceptance requires measured project test coverage.",
            "The practical case is excluded from development selection and all confirmatory or reproduction statistics.",
        ],
    }
    return case, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Reconstruct and compare checked-in outputs without modifying files.")
    parser.add_argument("--output-dir", type=Path, default=BASE)
    args = parser.parse_args()
    case, audit = construct()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    audit_bytes = encoded(audit)
    audit_gzip = compressed(audit_bytes)
    audit_manifest = {"schema": "bloom-public-audit-storage/v1", "file": "graph_audit.json.gz",
                      "encoding": "gzip", "compressed_sha256": sha256(audit_gzip),
                      "payload_sha256": sha256(audit_bytes), "payload_bytes": len(audit_bytes),
                      "reason": "Lossless compact storage; the decompressed canonical JSON is authoritative."}
    for name, expected in zip(OUTPUTS, (encoded(case), audit_gzip, encoded(audit_manifest))):
        path = args.output_dir / name
        if args.check:
            if not path.exists() or path.read_bytes() != expected:
                raise SystemExit("FAIL: reconstructed bytes differ: " + str(path))
        else:
            path.write_bytes(expected)
        print(name, sha256(expected), len(expected), "bytes")
    print(json.dumps(audit["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
