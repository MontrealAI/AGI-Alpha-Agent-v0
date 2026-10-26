# SPDX-License-Identifier: Apache-2.0
import argparse, hashlib, json
from pathlib import Path

def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def registry_from_custody(root, metadata_path, expected_metadata_sha256, source_root, consumer_root):
    metadata_raw = metadata_path.read_bytes()
    if sha(metadata_raw) != expected_metadata_sha256:
        raise ValueError("METADATA_IDENTITY")
    metadata = json.loads(metadata_raw)
    custody = json.loads((source_root / "source-custody.json").read_text())
    if custody["manifest_sha256"] != expected_metadata_sha256:
        raise ValueError("CUSTODY_METADATA_IDENTITY")
    recorded = {row["path"]: row for row in custody["files"]}
    snapshots = {}
    for snapshot in metadata["snapshots"]:
        relative = Path("snapshots") / snapshot["project"] / snapshot["tag"]
        inventory = {}
        for row in snapshot["files"]:
            name = str(relative / row["path"])
            evidence = recorded[name]
            path = source_root / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("SOURCE_NOT_REGULAR")
            raw = path.read_bytes()
            raw.decode("utf-8")
            git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            if git_blob != row["blob"] or sha(raw) != evidence["sha256"] or len(raw) != row["size"]:
                raise ValueError("SOURCE_IDENTITY")
            inventory[row["path"]] = sha(raw)
        actual = {p.relative_to(source_root / relative).as_posix() for p in (source_root / relative).rglob("*.py")}
        if actual != set(inventory):
            raise ValueError("SOURCE_INVENTORY_CLOSURE")
        snapshots[(snapshot["project"], snapshot["tag"])] = {
            "directory": (source_root / relative).relative_to(root).as_posix(),
            "inventory_sha256": sha(encoded(inventory)),
            "files": len(inventory),
        }
    consumer_manifest = json.loads((consumer_root / "manifest.json").read_text())
    consumer_relative = consumer_root.relative_to(root).as_posix()
    consumer_inventory = {}
    for row in consumer_manifest["files"]:
        path = consumer_root / row["path"]
        if path.is_symlink() or not path.is_file():
            raise ValueError("CONSUMER_NOT_REGULAR")
        raw = path.read_bytes()
        raw.decode("utf-8")
        if sha(raw) != row["sha256"]:
            raise ValueError("CONSUMER_IDENTITY")
        consumer_inventory[consumer_relative + "/" + row["path"]] = sha(raw)
    if {p.relative_to(consumer_root).as_posix() for p in consumer_root.rglob("*.py")} != {r["path"] for r in consumer_manifest["files"]}:
        raise ValueError("CONSUMER_INVENTORY_CLOSURE")
    missions = {}
    for row in metadata["missions"]:
        old = snapshots[(row["project"], row["before_tag"])]
        new = snapshots[(row["project"], row["after_tag"])]
        missions[row["id"]] = {
            "repository": row["repo"],
            "before_ref": row["before_commit"],
            "after_ref": row["after_commit"],
            "before_tag": row["before_tag"],
            "after_tag": row["after_tag"],
            "before_dir": old["directory"],
            "after_dir": new["directory"],
            "before_dir_inventory_sha256": old["inventory_sha256"],
            "after_dir_inventory_sha256": new["inventory_sha256"],
            "consumers": [consumer_relative],
            "consumer_inventory_sha256": sha(encoded(consumer_inventory)),
            "consumer_scope": consumer_manifest["scope"],
            "consumer_source_commit": consumer_manifest["source_commit"],
            "purpose": "Historical dependency upgrade assessment under a bounded captured Alpha consumer scope",
            "role": "held-out-historical-confirmation",
            "freshness": "Held out from constructors in this study; public history, not prospective releases or paid orders",
            "trigger": row["trigger"],
        }
    return {"schema": "value-compounds-mission-registry/v1", "metadata_sha256": expected_metadata_sha256,
            "source_custody_sha256": sha((source_root / "source-custody.json").read_bytes()),
            "consumer_manifest_sha256": sha((consumer_root / "manifest.json").read_bytes()),
            "missions": missions}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--metadata", type=Path, required=True)
    p.add_argument("--expected-metadata-sha256", required=True)
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--consumer-root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = registry_from_custody(a.root.resolve(), a.metadata.resolve(), a.expected_metadata_sha256,
                                   a.source_root.resolve(), a.consumer_root.resolve())
    if a.out.exists():
        raise ValueError("OUTPUT_EXISTS")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    raw = encoded(result) + b"\n"
    a.out.write_bytes(raw)
    print(json.dumps({"missions": len(result["missions"]), "path": str(a.out), "sha256": sha(raw)}))

if __name__ == "__main__":
    main()
