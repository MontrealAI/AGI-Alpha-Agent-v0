# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import os
import re
from pathlib import Path
from typing import Any

from packaging.markers import default_environment
from packaging.utils import canonicalize_name

try:
    from .acceptance import ROOT, in_study
except ImportError:
    from acceptance import ROOT, in_study

FAMILIES = ("cryptography", "eth-account", "prometheus-client", "pydantic-settings", "pyyaml", "uvicorn")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def save(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def block_for(text: str, family: str) -> str:
    pattern = r"(?ms)^" + re.escape(family) + r"==[^\n]*\n.*?(?=^[A-Za-z0-9_.-]+==|\Z)"
    rows = re.findall(pattern, text)
    if len(rows) != 1:
        raise ValueError("EXACT_ONE_ORIGINAL_PIN_BLOCK:" + family)
    return rows[0]


def replace_block(text: str, family: str, replacement: str) -> str:
    original = block_for(text, family)
    return text.replace(original, replacement, 1)


def prepare(heritage: Path, output: Path, wheelhouse: Path) -> dict[str, Any]:
    output = in_study(output, must_exist=False)
    wheelhouse = in_study(wheelhouse)
    output.mkdir(parents=True, exist_ok=False)
    source = heritage / "inputs"
    if not source.is_dir() and (heritage / "development/job.json").is_file():
        source = heritage
    baseline_path = source / "development/job.json"
    baseline_raw = baseline_path.read_bytes()
    baseline = json.loads(baseline_raw)
    lock_raw = (source / "development/requirements-agent.lock").read_bytes()
    project_raw = (source / "development/pyproject.toml").read_bytes()
    if digest(lock_raw) != baseline["lock_sha256"] or digest(project_raw) != baseline["pyproject_sha256"]:
        raise ValueError("HERITAGE_BASELINE_IDENTITY")
    if baseline["target_environment"] != default_environment():
        raise ValueError("CURRENT_ENVIRONMENT_DIFFERS_REGISTER_A_SEPARATE_ENVIRONMENT_FIRST")
    baseline_text = lock_raw.decode()
    changes = {}
    source_rows = [{"path": "inputs/development/job.json", "sha256": digest(baseline_raw)},
                   {"path": "inputs/development/requirements-agent.lock", "sha256": digest(lock_raw)},
                   {"path": "inputs/development/pyproject.toml", "sha256": digest(project_raw)}]
    for family in FAMILIES:
        folder = source / "confirmation" / family
        raw = (folder / "job.json").read_bytes()
        old = json.loads(raw)
        changed_raw = (folder / "requirements.lock").read_bytes()
        if digest(changed_raw) != old["lock_sha256"] or old["pyproject_sha256"] != baseline["pyproject_sha256"]:
            raise ValueError("HERITAGE_CHANGED_INPUT_IDENTITY")
        selected = [w for w in old["wheels"] if canonicalize_name(w["name"]) == family]
        if len(selected) != 1:
            raise ValueError("SINGLE_SELECTED_PREDECESSOR_REQUIRED")
        changes[family] = {"block": block_for(changed_raw.decode(), family), "wheel": selected[0],
                           "original_job_sha256": digest(raw)}
        source_rows += [{"path": f"inputs/confirmation/{family}/job.json", "sha256": digest(raw)},
                        {"path": f"inputs/confirmation/{family}/requirements.lock", "sha256": digest(changed_raw)}]
    rows = []

    def make(ident: str, group: str, families: tuple[str, ...], *, project: bytes = project_raw,
             extras: list[str] | None = None, declaration: str = "") -> None:
        folder = output / ident
        folder.mkdir()
        text = baseline_text
        selected = copy.deepcopy(baseline["wheels"])
        for family in families:
            text = replace_block(text, family, changes[family]["block"])
            selected = [copy.deepcopy(changes[family]["wheel"]) if canonicalize_name(w["name"]) == family else w
                        for w in selected]
        for wheel in selected:
            path = wheelhouse / wheel["filename"]
            if not path.is_file() or digest(path.read_bytes()) != wheel["sha256"]:
                raise ValueError("SOURCE_WHEEL_BYTES_UNAVAILABLE:" + wheel["filename"])
        (folder / "requirements.lock").write_text(text)
        (folder / "pyproject.toml").write_bytes(project)
        job = {"schema": "agialpha-lock-job/v1", "id": ident, "lock_path": "requirements.lock",
               "lock_sha256": digest(text.encode()), "pyproject_path": "pyproject.toml",
               "pyproject_sha256": digest(project), "project_extras": baseline["project_extras"] if extras is None else extras,
               "wheelhouse_path": os.path.relpath(wheelhouse, folder), "wheels": selected,
               "target_environment": default_environment()}
        save(folder / "job.json", job)
        provenance = {"schema": "verified-capability-input-derivation/v1", "group": group,
                      "baseline_job_sha256": digest(baseline_raw), "changed_families": list(families),
                      "parent_jobs": [changes[family]["original_job_sha256"] for family in families],
                      "declaration": declaration, "dependency_metadata_inspected_by_preparation": False,
                      "resolution_run_by_preparation": False, "customer_order": False,
                      "prior_results_modified": False}
        save(folder / "source.json", provenance)
        rows.append({"id": ident, "group": group, "families": list(families), "status": "READY",
                     "job": str((folder / "job.json").relative_to(ROOT)),
                     "job_sha256": digest((folder / "job.json").read_bytes()),
                     "source_sha256": digest((folder / "source.json").read_bytes())})

    make("development-unchanged-lock", "development", (), declaration="Unchanged inherited baseline; engineering development only.")
    for first, second in itertools.combinations(FAMILIES, 2):
        make("pair-" + first + "--" + second, "primary-composition", (first, second),
             declaration="Two exact previously selected predecessor substitutions combined for the first time; all other pins and original project constraints unchanged. Joint outcomes not assumed from single-component validity.")
    project_text = project_raw.decode()
    crypto_old, crypto_new = '"cryptography>=50.0.1,<51"', '"cryptography>=51,<52"'
    python_old, python_new = 'requires-python = ">=3.11,<3.14"', 'requires-python = ">=3.13,<3.14"'
    if project_text.count(crypto_old) != 1 or project_text.count(python_old) != 1:
        raise ValueError("DECLARED_ROOT_CHANGE_SOURCE_NO_LONGER_MATCHES")
    make("stress-cryptography-major-requirement", "designed-root-stress", (),
         project=project_text.replace(crypto_old, crypto_new, 1).encode(),
         declaration="Designed requirement stress: maintainer now requires cryptography51 while preserving existing lock. Expected mismatch is a negative control, not a newly discovered demand.")
    make("stress-remove-chain-requirement", "designed-root-stress", (), extras=[],
         declaration="Designed scope stress: selected chain extra is removed; locked packages remain. No claim that dropping a customer requirement improves the original mission.")
    make("stress-python-minimum-313", "designed-root-stress", (),
         project=project_text.replace(python_old, python_new, 1).encode(),
         declaration="Designed environment contract stress: project requires Python>=3.13 while current interpreter is3.12.14. Original project requirement remains preserved.")
    manifest = {"schema": "verified-capability-mission-inputs/v1", "jobs": rows,
                "counts": {"development": 1, "primary_composition": 15, "designed_root_stress": 3},
                "selection": "Complete lexicographically ordered choose(6,2) of preserved predecessor substitutions; no outcome-based replacement.",
                "freshness": "New joint questions over shared historical public inputs. Correlated cohort, not15 independent release families or customer orders.",
                "preparation_outcomes_inspected": False, "source_bindings": source_rows,
                "same_resources_all_arms": "Exact same job, wheels, pip, environment, independent verifier and evidence; only selector layer differs.",
                "unchanged_requests": "Use semantic mission_key excluding id/path/rendering/timing. Revalidating the same key is a cache/control observation, never a new job."}
    save(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--heritage", type=Path, default=ROOT / "heritage/second-investment-inputs")
    parser.add_argument("--out", type=Path, default=ROOT / "inputs/missions-v1")
    parser.add_argument("--wheelhouse", type=Path, default=ROOT / "inputs/wheels")
    args = parser.parse_args()
    manifest = prepare(args.heritage, args.out, args.wheelhouse)
    print(json.dumps({"counts": manifest["counts"], "metadata_inspected": False, "outcomes_run": False}))
