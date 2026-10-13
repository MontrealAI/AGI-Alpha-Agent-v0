# SPDX-License-Identifier: Apache-2.0
"""Real domain work, execution binding, artifact use and native recovery checks."""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor import workbench

FAMILIES = ["reliability", "performance", "documentation", "public-data", "numerical"]


@pytest.mark.parametrize("family", FAMILIES)
def test_real_domain_artifacts_and_seven_job_binding(family: str, tmp_path: Path) -> None:
    spec = workbench.invoke({"operation": "example", "family": family})
    pack = workbench.invoke({"operation": "run", "spec": spec})
    assert pack["evaluation"]["authority"] == []
    assert pack["evaluation"]["admission"] == "HOLD"
    assert pack["result"]["artifacts"]
    workbench.write_artifacts(pack, tmp_path / family)
    restored = workbench.invoke({"operation": "inspect", "pack": pack})
    assert restored["spec"] == spec
    assert restored["activeProof"] == restored["activeAuthority"] == []
    if family == "reliability":
        assert pack["result"]["summary"]["defects"] == 2
        result = subprocess.run(["node", str(tmp_path / family / "check.mjs")], capture_output=True, check=True)
        assert b"passed" in result.stdout
    elif family == "public-data":
        assert "295" in (tmp_path / family / "analysis.json").read_text()
    elif family == "numerical":
        assert pack["result"]["summary"]["simpson"] is True


def test_input_identity_and_cosmetic_edit() -> None:
    spec = workbench.invoke({"operation": "example", "family": "reliability"})
    original = workbench.invoke({"operation": "run", "spec": spec})
    spec["name"] = "Une autre Ω"
    renamed = workbench.invoke({"operation": "run", "spec": spec})
    assert renamed["releaseDigest"] == original["releaseDigest"]
    spec["inputs"]["source"] = "export function contains(value, low, high) { return low <= value && value <= high; }"
    changed = workbench.invoke({"operation": "run", "spec": spec})
    assert changed["releaseDigest"] != original["releaseDigest"]
    assert changed["result"]["decision"] == "RETAIN_INCUMBENT"
    assert changed["result"]["summary"]["defects"] == 0


def test_poisoned_import_and_code_are_rejected() -> None:
    spec = workbench.invoke({"operation": "example", "family": "reliability"})
    pack = workbench.invoke({"operation": "run", "spec": spec})
    pack["result"]["artifacts"][0]["name"] = "../escape.mjs"
    with pytest.raises(ValueError):
        workbench.invoke({"operation": "inspect", "pack": pack})
    spec["inputs"]["source"] += "\nprocess.exit(0);"
    with pytest.raises(ValueError, match="SOURCE_GRAMMAR"):
        workbench.invoke({"operation": "run", "spec": spec})


def test_signed_journal_idempotency_review_and_no_overwrite(tmp_path: Path) -> None:
    home, run_id = tmp_path / "operator", str(uuid.uuid4())
    spec = workbench.invoke({"operation": "example", "family": "documentation"})
    record = workbench.execute(home, spec, run_id)
    journal = Journal(home)
    head = journal.verify()
    assert record["state"] == "review"
    assert workbench.execute(home, spec, run_id)["result_digest"] == record["result_digest"]
    assert journal.verify() == head
    workbench.write_artifacts(record["result"], tmp_path / "artifacts")
    with pytest.raises(FileExistsError):
        workbench.write_artifacts(record["result"], tmp_path / "artifacts")
    spec["inputs"]["markdown"] += "\nChanged input."
    with pytest.raises(Conflict, match="different request"):
        workbench.execute(home, spec, run_id)


def test_interrupted_pure_work_requires_explicit_resume(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec = workbench.invoke({"operation": "example", "family": "numerical"})
    original, run_id = workbench.invoke, str(uuid.uuid4())

    def interrupt(request: dict[str, Any], *args: Any) -> dict[str, Any]:
        if request["operation"] == "run":
            raise KeyboardInterrupt()
        return original(request, *args)

    monkeypatch.setattr(workbench, "invoke", interrupt)
    with pytest.raises(KeyboardInterrupt):
        workbench.execute(tmp_path / "home", spec, run_id)
    with pytest.raises(Conflict, match="--resume"):
        workbench.execute(tmp_path / "home", spec, run_id)
    monkeypatch.setattr(workbench, "invoke", original)
    result = workbench.execute(tmp_path / "home", spec, run_id, resume=True)
    assert result["attempts"] == 2
    assert result["state"] == "review"


def test_worker_source_is_reproducible() -> None:
    from scripts.generate_successor_workbench import bundle

    _, source_hash, sources = bundle()
    manifest = json.loads(workbench.WORKER.with_name("workbench_sources.json").read_text())
    assert manifest["sourceHash"] == source_hash
    assert manifest["sources"] == json.loads(sources)
