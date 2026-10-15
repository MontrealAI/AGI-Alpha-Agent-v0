# SPDX-License-Identifier: Apache-2.0
"""The additive current audit cannot inherit old passes or hide stale evidence."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from scripts import ascension_current_audit as audit


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    for name in (audit.HISTORY, audit.POLICY, "BACKGROUND.md"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((audit.ROOT / name).read_bytes())
    (tmp_path / "source.py").write_text("initial source\n")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Audit Test",
            "-c",
            "user.email=audit@example.invalid",
            "commit",
            "-qm",
            "Synthetic audit repository",
        ],
        check=True,
    )
    return tmp_path


def evidence(root: Path, suite_id: str = "interruption", *, exit_code: int = 0, skipped: int = 0) -> Path:
    """A synthetic record used only to test validator mechanics, never product evidence."""
    _, policy = audit.catalog(root)
    spec = policy["suites"][suite_id]
    directory = root / audit.EVIDENCE / "synthetic-validator-fixture"
    directory.mkdir(parents=True)
    identity = audit.source_identity(root)
    audit.save_json(directory / "source.json", identity)
    output = (
        f"TAP version 13\n# tests 2\n# pass {2-skipped}\n# fail 0\n# cancelled 0\n" f"# skipped {skipped}\n# todo 0\n"
    ).encode()
    (directory / "output.txt").write_bytes(output)
    replacements = {"{python}": sys.executable, "{node}": "/test/node"}
    record: dict[str, Any] = {
        "schema": audit.RUN_SCHEMA,
        "run_id": "synthetic-validator-fixture",
        "suite_id": suite_id,
        "kind": spec["kind"],
        "suite_spec": spec,
        "suite_spec_sha256": audit.sha256(audit.canonical(spec)),
        "argv": [replacements.get(arg, arg) for arg in spec["argv"]],
        "cwd": spec["cwd"],
        "runtime": {"python": sys.executable, "node": "/test/node"},
        "execution_root": str(root),
        "environment": {"PYTHONPATH": str(root), "ALPHA_PYTHON": sys.executable, "NO_DISCLAIMER": "1"},
        "scope": spec["scope"],
        "human_participants": 0,
        "real_funds": False,
        "started_utc": "2026-10-14T00:00:00+00:00",
        "finished_utc": "2026-10-14T00:00:01+00:00",
        "source_before": identity["source_sha256"],
        "source_after": identity["source_sha256"],
        "source_manifest_sha256": audit.sha256((directory / "source.json").read_bytes()),
        "output_sha256": audit.sha256(output),
        "returncode": exit_code,
        "artifacts": {},
    }
    record["counts"] = audit.counts_from_log(output.decode(), spec["kind"])
    record["outcome"] = audit.run_outcome(record, output.decode())
    audit.save_json(directory / "run.json", record)
    return directory


def test_all_80_original_requirements_preserved_without_history_promotion(repository: Path) -> None:
    report = audit.build_audit(repository)
    history, _ = audit.catalog(repository)
    assert [(item["id"], item["requirement"]) for item in report["cases"]] == [
        (item["id"], item["requirement"]) for item in history["cases"]
    ]
    assert report["summary"]["requirement_counts"] == {"not_run": 80}
    assert report["summary"]["complete_software_release"] is False
    assert report["pilot"]["observed_participants"] == 0
    assert not report["summary"]["human_benefit_validated"]
    assert all(case["remaining_acceptance"] for case in report["cases"])
    assert len(report["graph"]["nodes"]) == 12 and len(report["graph"]["edges"]) == 18
    assert report["graph"]["original_preserved"]


def test_current_pass_is_bounded_and_source_change_invalidates_it(repository: Path) -> None:
    evidence(repository)
    report = audit.build_audit(repository)
    assert report["suites"]["interruption"]["status"] == "passed"
    assert report["cases"][75]["requirement_status"] == "partial"
    assert not report["summary"]["complete_software_release"]
    (repository / "source.py").write_text("changed source\n")
    changed = audit.build_audit(repository)
    assert changed["suites"]["interruption"]["status"] == "not_run"
    assert changed["runs"][0]["current_source"] is False


@pytest.mark.parametrize(
    "change", ["output", "outcome", "argv", "cwd", "source", "artifact", "counts", "environment", "human_participants"]
)
def test_tampered_evidence_rejected(repository: Path, change: str) -> None:
    directory = evidence(repository)
    record = audit.load_json(directory / "run.json")
    if change == "output":
        (directory / "output.txt").write_text("Different output")
    elif change == "source":
        manifest = audit.load_json(directory / "source.json")
        manifest["files"]["source.py"] = "0" * 64
        audit.save_json(directory / "source.json", manifest)
    elif change == "artifact":
        (directory / "artifacts").mkdir()
        (directory / "artifacts" / "forged.json").write_text("{}")
    else:
        record[change] = {
            "outcome": "failed",
            "argv": ["true"],
            "cwd": "/tmp",
            "counts": {"pass": 99},
            "environment": {},
            "human_participants": 1,
        }[change]
        audit.save_json(directory / "run.json", record)
    with pytest.raises(ValueError):
        audit.build_audit(repository)


def test_failed_and_skipped_results_do_not_become_full_passes(repository: Path) -> None:
    directory = evidence(repository, skipped=1)
    assert audit.build_audit(repository)["suites"]["interruption"]["status"] == "partial"
    record = audit.load_json(directory / "run.json")
    record["returncode"] = 1
    record["outcome"] = "failed"
    audit.save_json(directory / "run.json", record)
    report = audit.build_audit(repository)
    assert report["suites"]["interruption"]["status"] == "failed"
    assert report["cases"][75]["requirement_status"] == "failed"


def test_changed_suite_scope_stales_old_result_without_rewriting_history(repository: Path) -> None:
    evidence(repository)
    policy = audit.load_json(repository / audit.POLICY)
    policy["suites"]["interruption"]["scope"] += " Additional checks now required."
    audit.save_json(repository / audit.POLICY, policy)
    report = audit.build_audit(repository)
    assert report["suites"]["interruption"]["status"] == "not_run"
    assert report["runs"][0]["current_source"] is False


@pytest.mark.parametrize("change", ["requirement", "missing-case", "pilot"])
def test_changed_requirement_missing_case_or_invented_participant_rejected(repository: Path, change: str) -> None:
    policy = audit.load_json(repository / audit.POLICY)
    if change == "requirement":
        policy["cases"]["76"]["requirement"] = "A weaker replacement requirement"
    elif change == "missing-case":
        del policy["cases"]["80"]
    else:
        policy["pilot"]["observed_participants"] = 1
    audit.save_json(repository / audit.POLICY, policy)
    with pytest.raises(ValueError):
        audit.build_audit(repository)


def test_original_history_and_ambiguous_json_cannot_be_changed(repository: Path) -> None:
    original = repository / audit.HISTORY
    original.write_text(original.read_text() + " ")
    with pytest.raises(ValueError, match="historical"):
        audit.catalog(repository)
    path = repository / "ambiguous.json"
    path.write_text('{"status":"failed","status":"passed"}')
    with pytest.raises(ValueError, match="Duplicate"):
        audit.load_json(path)


def test_empty_or_skipped_only_command_cannot_pass() -> None:
    record = {"kind": "node", "returncode": 0, "source_before": "a", "source_after": "a"}
    assert audit.run_outcome(record, "") == "unverified"
    assert (
        audit.run_outcome(record, "# tests 1\n# pass 0\n# fail 0\n# cancelled 0\n# skipped 1\n# todo 0\n")
        == "unverified"
    )
    assert audit.run_outcome({**record, "source_after": "b"}, "") == "failed"


def test_report_outputs_do_not_invalidate_source_and_commit_context_is_not_self_referential(repository: Path) -> None:
    before = audit.source_identity(repository)
    audit.save_json(repository / audit.OUTPUT, audit.build_audit(repository))
    after = audit.source_identity(repository)
    assert before["source_sha256"] == after["source_sha256"]
    assert "commit" not in audit.build_audit(repository)["source_identity"]


def test_source_creation_deletion_and_generated_profile_are_bound(repository: Path) -> None:
    before = audit.source_identity(repository)["source_sha256"]
    (repository / "new-source.py").write_text("new code")
    assert audit.source_identity(repository)["source_sha256"] != before
    (repository / "new-source.py").unlink()
    (repository / "source.py").unlink()
    assert audit.source_identity(repository)["source_sha256"] != before
    profile = repository / audit.GENERATED_INPUTS[0]
    profile.parent.mkdir(parents=True)
    profile.write_text('{"newExposureEnabled":false}')
    assert audit.source_identity(repository)["files"][audit.GENERATED_INPUTS[0]] == audit.sha256(profile.read_bytes())


def test_incomplete_attempt_is_visible_and_orphaned_source_record_rejected(repository: Path) -> None:
    directory = evidence(repository)
    record = audit.load_json(directory / "run.json")
    record.update(returncode=None, source_after=None, outcome="incomplete")
    audit.save_json(directory / "run.json", record)
    report = audit.build_audit(repository)
    assert report["suites"]["interruption"]["status"] == "incomplete"
    assert report["cases"][75]["requirement_status"] == "not_run"
    (directory / "run.json").unlink()
    with pytest.raises(ValueError, match="Incomplete"):
        audit.build_audit(repository)


def test_all_mapped_runtime_pytest_suites_isolate_runtime_configuration():
    """Minimal operator CI must never import the unrelated repository conftest."""
    _, policy = audit.catalog(audit.ROOT)
    suites = {
        name: spec
        for name, spec in policy["suites"].items()
        if spec["kind"] == "pytest" and any(arg.startswith("tests/runtime/") for arg in spec["argv"])
    }
    assert {"native_budget_browser", "native_ecosystem", "ecosystem_browser"} <= suites.keys()
    for name, spec in suites.items():
        assert "--confcutdir=tests/runtime" in spec["argv"], name
        assert spec["cwd"] == ".", name


def test_standalone_preservation_suite_uses_minimal_configuration():
    _, policy = audit.catalog(audit.ROOT)
    argv = policy["suites"]["preservation"]["argv"]
    assert "--noconftest" in argv
    assert argv[argv.index("-o") + 1] == "addopts="
