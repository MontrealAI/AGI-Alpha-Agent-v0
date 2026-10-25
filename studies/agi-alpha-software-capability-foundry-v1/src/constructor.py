# SPDX-License-Identifier: Apache-2.0
"""Finite, deterministic capability construction. Not a production scheduler."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import time
import types

ROOT = Path(__file__).resolve().parents[1]

def identity(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path: Path):
    raw = path.read_bytes()
    module = types.ModuleType("asset_" + hashlib.sha256(raw).hexdigest())
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module

def retain_reader(source: Path, destination: Path, evidence: dict) -> dict:
    """Construct versioned executable bytes and metadata from a qualified method."""
    started = time.perf_counter()
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / "reader.py"
    target.write_bytes(source.read_bytes())
    compile(target.read_bytes(), str(target), "exec")
    record = {"schema": "foundry-reader/v1", "version": "1.0.0", "sha256": identity(target),
              "source_sha256": identity(source), "interface": "read(repo, commit, paths, max_file, total)",
              "limits": {"paths": 256, "max_file": 8000000, "total": 32000000},
              "dependencies": ["Python 3.11+", "Git with cat-file --batch-command"],
              "operating_scope": "local SHA-1 Git commits; regular blob files; no mutable-file cache",
              "rollback": "retain original full verifier or direct specialist",
              "maintenance_money": None, "maintenance_human_seconds": None,
              "qualification": evidence, "construction_wall_seconds": time.perf_counter() - started}
    (destination / "reader.json").write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    return record

CHILD = '''# SPDX-License-Identifier: Apache-2.0
"""Constructed archive drift capability, bound to an accepted reader."""
from pathlib import Path
import hashlib
import json
from constructor import load, identity
from drift_core import compare
PARENT_SHA256 = {parent!r}
PARENT_ACCEPTANCE = {acceptance!r}
def diagnose(repo, commit, paths, archive, max_file=8000000, total=32000000):
    parent = Path(__file__).with_name("reader.py")
    if identity(parent) != PARENT_SHA256:
        raise ValueError("Retained parent bytes changed")
    module = load(parent)
    files = module.read(repo, commit, paths, max_file, total)
    result = compare(files, archive, max_file, total)
    inventory = {{p: hashlib.sha256(b).hexdigest() for p,b in sorted(files.items())}}
    result["parent_trace"] = {{"selected_execution": True, "invocations": 1,
      "parent_sha256": PARENT_SHA256, "acceptance_sha256": PARENT_ACCEPTANCE,
      "input_commit": commit, "input_paths_sha256": hashlib.sha256(json.dumps(sorted(paths)).encode()).hexdigest(),
      "output_inventory_sha256": hashlib.sha256(json.dumps(inventory,sort_keys=True).encode()).hexdigest()}}
    return result
'''

def construct_child(asset_dir: Path, acceptance: dict) -> dict:
    """Materialize a distinct interface only from a recorded accepted parent use."""
    if acceptance.get("passed") is not True or acceptance.get("parent_sha256") != identity(asset_dir / "reader.py"):
        raise ValueError("A matching accepted parent mission is required")
    encoded = json.dumps(acceptance, sort_keys=True, separators=(",", ":")).encode()
    binding = hashlib.sha256(encoded).hexdigest()
    child = asset_dir / "drift.py"
    child.write_text(CHILD.format(parent=identity(asset_dir / "reader.py"), acceptance=binding))
    compile(child.read_bytes(), str(child), "exec")
    record = {"schema": "foundry-drift/v1", "version": "1.0.0", "sha256": identity(child),
              "parent_sha256": identity(asset_dir / "reader.py"), "parent_acceptance_sha256": binding,
              "interface": "diagnose(repo, commit, paths, archive, max_file, total)",
              "limits": {"members": 256, "max_file": 8000000, "total": 32000000},
              "source_dependencies": {"constructor.py": identity(Path(__file__)),
                                      "drift_core.py": identity(ROOT / "src/drift_core.py")},
              "behavior": "complete changed/missing/extra diagnosis; no extraction or source writes",
              "rollback": "use direct specialist; previous versions remain available",
              "maintenance_money": None, "maintenance_human_seconds": None}
    (asset_dir / "drift.json").write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    (asset_dir / "accepted_parent.json").write_text(json.dumps(acceptance, sort_keys=True, indent=2) + "\n")
    return record
