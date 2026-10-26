# SPDX-License-Identifier: Apache-2.0
"""Portable policy-only challenges: no approved map, scan waiver or product run.

Positive fixtures explicitly monkeypatch a test-only pin. Production source has
no approved SHA and no map file; these fixtures are never release case data.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

import pytest

from scripts import semgrep_inapplicability as policy


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def commit(root: Path) -> None:
    git(root, "add", "--all")
    git(
        root,
        "-c",
        "user.name=Inert fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "--allow-empty",
        "-qm",
        "fixture",
    )


def position(body: bytes, offset: int) -> dict[str, int]:
    return {
        "offset": offset,
        "line": body.count(b"\n", 0, offset) + 1,
        "col": offset - body.rfind(b"\n", 0, offset),
    }


def alternate_variant(captured: policy.CapturedInputs) -> policy.CapturedInputs:
    prefix = b"# second exact development representation\n"
    return replace(
        captured,
        official_pack=prefix + captured.official_pack,
        rule_definitions=tuple(
            replace(rule, start_byte=rule.start_byte + len(prefix), end_byte=rule.end_byte + len(prefix))
            for rule in captured.rule_definitions
        ),
    )


def fixture_case(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: bytes = b"import hashlib\nhashlib.sha1(b'inert')\n",
    copies: bool = False,
) -> tuple[dict[str, Any], policy.CapturedInputs]:
    monkeypatch.setattr(policy, "ROOT", root.resolve())
    # Development fixtures have their own inactive state and never inherit a
    # future operator-reviewed production map pin.
    monkeypatch.setattr(policy, "APPROVED_MAP_SHA256", None)
    (root / "selected.py").write_bytes(body)
    targets = ("selected.py",)
    if copies:
        (root / "copied.py").write_bytes(body)
        targets += ("copied.py",)
    matcher = root / policy.MODULE_PATH
    matcher.parent.mkdir(parents=True)
    matcher.write_text("APPROVED_MAP_SHA256: str | None = None\n# fixed fixture policy body\n")
    (root / "caller.yml").write_text("trusted: fixture\n")
    (root / "other.py").write_text("label = 'inert'\n")
    git(root, "init", "-q")
    commit(root)
    pack = b"# fixture only\nrules:\n- id: fixture-rule\n  pattern: hashlib.sha1(...)\n# unchanged footer\n"
    start, end = pack.index(b"id:"), pack.index(b"# unchanged footer")
    rule = policy.RuleDefinition("fixture-rule", start, end, policy._digest(pack[start:end]))
    captured = policy.capture_inputs(targets, pack, (rule,))
    monkeypatch.setattr(
        policy,
        "REVIEWABLE_PACK_SHA256S",
        (policy._digest(pack), policy._digest(alternate_variant(captured).official_pack)),
    )
    first = body.index(b"hashlib.sha1")
    last = body.rindex(b")") + 1
    start_position, end_position = position(body, first), position(body, last)
    normalized_lines = body.decode().replace("\r\n", "\n").replace("\r", "\n").split("\n")
    reported_lines = "\n".join(normalized_lines[start_position["line"] - 1 : end_position["line"]]).rstrip()
    report = {
        "version": policy.SEMGREP_VERSION,
        "results": [
            {
                "check_id": "fixture-rule",
                "path": "selected.py",
                "start": start_position,
                "end": end_position,
                "extra": {"is_ignored": False, "lines": reported_lines},
            }
        ],
        "errors": [],
        "skipped_rules": [],
        "paths": {"scanned": list(targets)},
    }
    return report, captured


def assess(
    report: dict[str, Any], before: policy.CapturedInputs, after: policy.CapturedInputs | None = None, code: int = 1
) -> dict[str, Any]:
    return policy.assess(json.dumps(report).encode(), code, before, before if after is None else after)


def reviewed_fixture(
    root: Path, monkeypatch: pytest.MonkeyPatch, report: dict[str, Any], captured: policy.CapturedInputs
) -> dict[str, Any]:
    alternate = alternate_variant(captured)
    monkeypatch.setattr(
        policy,
        "REVIEWABLE_PACK_SHA256S",
        (policy._digest(captured.official_pack), policy._digest(alternate.official_pack)),
    )
    inactive = assess(report, captured)
    assert inactive["policy_disposition"] == "INACTIVE" and not inactive["policy_accepted"]
    value = {
        "schema": "agialpha.semgrep-reviewed-inapplicability/v2",
        "semgrep_version": policy.SEMGREP_VERSION,
        "target_paths_sha256": policy._digest(policy._canonical(sorted(captured.targets))),
        "repository_inventory_sha256": captured.repository.sha256,
        "variants": [],
    }
    for inputs in (captured, alternate):
        own = assess(report, inputs)
        assert own["policy_disposition"] == "INACTIVE"
        value["variants"].append(
            {
                "official_pack_sha256": policy._digest(inputs.official_pack),
                "cases": [
                    {
                        "identity": own["finding_identities"][0],
                        "rationale": "Synthetic fixture only, not an actual applicability judgment",
                        "review_reference": "test-only; no production review or approval",
                    }
                ],
            }
        )
    install_fixture(root, monkeypatch, value)
    return value


def install_fixture(root: Path, monkeypatch: pytest.MonkeyPatch, value: dict[str, Any] | bytes) -> None:
    body = value if type(value) is bytes else json.dumps(value).encode()
    path = root / policy.MAP_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    commit(root)
    monkeypatch.setattr(policy, "APPROVED_MAP_SHA256", policy._digest(body))


def test_production_has_only_the_two_fixed_reviewed_configuration_states(monkeypatch: pytest.MonkeyPatch) -> None:
    assert policy.MAP_PATH == "scripts/data/semgrep_python_inapplicability.json"
    assert set(policy.REVIEWABLE_PACK_SHA256S) == {
        "de5bc79d074c3b4146338a0bf95830406f169bd91ac590a2f1ef111f162e23f5",
        "e3c25cf9b28ddfd3cb1b7f240d2fc0998734199efa539fa0b10281487a602e79",
    }
    monkeypatch.setenv("SEMGREP_INAPPLICABILITY_MAP", "/unreviewed/alternate-map.json")
    monkeypatch.setenv("SEMGREP_APPROVED_MAP_SHA256", "0" * 64)
    if policy.APPROVED_MAP_SHA256 is None:
        assert not (policy.ROOT / policy.MAP_PATH).exists()
    else:
        # This reads only the fixed committed regular file and literal pin;
        # it never treats environment input as an approval or data selector.
        _data, approved_sha = policy._approved_map()
        assert approved_sha == policy.APPROVED_MAP_SHA256


def test_no_map_pin_keeps_valid_findings_inactive_with_raw_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    monkeypatch.setenv("SEMGREP_APPROVED_MAP_SHA256", "a" * 64)
    monkeypatch.setenv("SEMGREP_INAPPLICABILITY_MAP", "/tmp/unreviewed-map.json")
    monkeypatch.setattr(policy, "_approved_map", lambda: pytest.fail("Inactive policy must not read a map"))
    result = assess(report, captured)
    assert result["policy_disposition"] == "INACTIVE" and result["policy_accepted"] is False
    assert result["raw_exit_code"] == 1 and result["raw_scan_passed"] is False
    assert result["raw_findings"] == report["results"] and result["raw_finding_count"] == 1
    assert result["inapplicable_finding_count"] == 0
    assert result["production_authority"] is False and result["release_authorized"] is False


def test_inactive_fixture_does_not_inherit_a_production_pin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy, "APPROVED_MAP_SHA256", "f" * 64)
    report, captured = fixture_case(tmp_path, monkeypatch)
    result = assess(report, captured)
    assert policy.APPROVED_MAP_SHA256 is None
    assert result["policy_disposition"] == "INACTIVE" and not result["policy_accepted"]


@pytest.mark.parametrize(
    "defect",
    [
        "errors",
        "missing-errors",
        "skipped-rule",
        "missing-rules",
        "skipped-target",
        "zero-coverage",
        "missing-coverage",
        "duplicate-coverage",
        "unknown-coverage",
        "wrong-version",
        "bad-exit",
        "signal-exit",
        "boolean-exit",
        "exit0-findings",
        "exit1-empty",
        "duplicate-finding",
        "unknown-rule",
        "unknown-path",
        "ignored-finding",
        "missing-lines",
        "forged-lines",
        "boolean-position",
        "bad-column",
        "reversed-span",
        "missing-location",
    ],
)
def test_invalid_scan_is_refused_before_any_map_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    monkeypatch.setattr(policy, "APPROVED_MAP_SHA256", "a" * 64)
    monkeypatch.setattr(policy, "_approved_map", lambda: pytest.fail("Invalid evidence reached map matching"))
    code: Any = 1
    finding = report["results"][0]
    if defect == "errors":
        report["errors"] = [{"type": "ParseError"}]
    elif defect == "missing-errors":
        del report["errors"]
    elif defect == "skipped-rule":
        report["skipped_rules"] = ["fixture-rule"]
    elif defect == "missing-rules":
        del report["skipped_rules"]
    elif defect == "skipped-target":
        report["paths"]["skipped"] = ["selected.py"]
    elif defect == "zero-coverage":
        report["paths"]["scanned"] = []
    elif defect == "missing-coverage":
        del report["paths"]
    elif defect == "duplicate-coverage":
        report["paths"]["scanned"] *= 2
    elif defect == "unknown-coverage":
        report["paths"]["scanned"] = ["unknown.py"]
    elif defect == "wrong-version":
        report["version"] = "0.0.0"
    elif defect == "bad-exit":
        code = 2
    elif defect == "signal-exit":
        code = -9
    elif defect == "boolean-exit":
        code = True
    elif defect == "exit0-findings":
        code = 0
    elif defect == "exit1-empty":
        report["results"] = []
    elif defect == "duplicate-finding":
        report["results"] *= 2
    elif defect == "unknown-rule":
        finding["check_id"] = "other-rule"
    elif defect == "unknown-path":
        finding["path"] = "other.py"
    elif defect == "ignored-finding":
        finding["extra"]["is_ignored"] = True
    elif defect == "missing-lines":
        del finding["extra"]["lines"]
    elif defect == "forged-lines":
        finding["extra"]["lines"] = "different source"
    elif defect == "boolean-position":
        finding["start"]["line"] = True
    elif defect == "bad-column":
        finding["start"]["col"] += 1
    elif defect == "reversed-span":
        finding["end"] = finding["start"]
    else:
        del finding["start"]["offset"]
    result = assess(report, captured, code=code)
    assert result["policy_disposition"] == "REFUSED" and result["policy_accepted"] is False


@pytest.mark.parametrize("raw", [b"[]", b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e309}'])
def test_invalid_or_duplicate_report_json_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw: bytes
) -> None:
    _, captured = fixture_case(tmp_path, monkeypatch)
    assert policy.assess(raw, 1, captured, captured)["policy_disposition"] == "REFUSED"


def test_clean_valid_scan_needs_no_map_and_grants_no_release_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    report["results"] = []
    monkeypatch.setattr(policy, "_approved_map", lambda: pytest.fail("Raw pass reached a map"))
    result = assess(report, captured, code=0)
    assert result["raw_scan_passed"] is True and result["policy_disposition"] == "NOT_NEEDED_RAW_PASS"
    assert not result["release_authorized"] and result["raw_finding_count"] == 0


def test_exact_fixture_matches_without_rewriting_engine_findings_or_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    reviewed_fixture(tmp_path, monkeypatch, report, captured)
    original = deepcopy(report)
    result = assess(report, captured)
    assert result["policy_disposition"] == "EXACT_REVIEWED_INAPPLICABILITY" and result["policy_accepted"]
    assert report == original and result["raw_findings"] == original["results"]
    assert result["raw_exit_code"] == 1 and result["raw_scan_passed"] is False
    assert result["raw_finding_count"] == result["inapplicable_finding_count"] == 1
    assert not result["production_authority"] and not result["release_authorized"]


@pytest.mark.parametrize("change", ["source-during", "source-after", "pack", "rule-span", "target-scope"])
def test_input_changes_refuse_before_map_matching(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    monkeypatch.setattr(policy, "APPROVED_MAP_SHA256", "a" * 64)
    monkeypatch.setattr(policy, "_approved_map", lambda: pytest.fail("Input drift reached map matching"))
    after = captured
    if change.startswith("source-"):
        (tmp_path / "selected.py").write_text("# changed\n")
        if change == "source-during":
            commit(tmp_path)
            after = policy.capture_inputs(captured.targets, captured.official_pack, captured.rule_definitions)
    elif change == "pack":
        after = replace(captured, official_pack=captured.official_pack + b"# changed\n")
    elif change == "rule-span":
        after = replace(captured, rule_definitions=())
    else:
        after = replace(captured, targets=())
    result = assess(report, captured, after)
    assert result["policy_disposition"] == "REFUSED" and not result["policy_accepted"]


@pytest.mark.parametrize(
    "change",
    [
        "duplicate",
        "missing-case",
        "extra-case",
        "case-identity",
        "rationale",
        "pack",
        "rule",
        "scope",
        "version",
        "unrelated-source",
    ],
)
def test_exact_map_refuses_unknown_missing_changed_and_duplicate_cases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    value = reviewed_fixture(tmp_path, monkeypatch, report, captured)
    cases = value["variants"][0]["cases"]
    if change == "duplicate":
        cases *= 2
    elif change == "missing-case":
        cases.clear()
    elif change == "extra-case":
        extra = deepcopy(cases[0])
        extra["identity"]["snippet_sha256"] = "0" * 64
        cases.append(extra)
    elif change == "case-identity":
        del cases[0]["identity"]["snippet_sha256"]
    elif change == "rationale":
        cases[0]["rationale"] = ""
    elif change == "pack":
        value["variants"][0]["official_pack_sha256"] = "0" * 64
    elif change == "rule":
        cases[0]["identity"]["rule_definition_sha256"] = "0" * 64
    elif change == "scope":
        value["target_paths_sha256"] = "0" * 64
    elif change == "version":
        value["semgrep_version"] = "0.0.0"
    else:
        (tmp_path / "selected.py").write_bytes((tmp_path / "selected.py").read_bytes() + b"# unrelated edit\n")
        commit(tmp_path)
        captured = policy.capture_inputs(captured.targets, captured.official_pack, captured.rule_definitions)
    install_fixture(tmp_path, monkeypatch, value)
    assert assess(report, captured)["policy_accepted"] is False


def test_identical_body_at_another_selected_path_does_not_inherit_a_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch, copies=True)
    reviewed_fixture(tmp_path, monkeypatch, report, captured)
    report["results"][0]["path"] = "copied.py"
    assert assess(report, captured)["policy_accepted"] is False


def test_identical_snippet_at_another_location_does_not_inherit_a_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = b"hashlib.sha1(b'x')\nhashlib.sha1(b'x')\n"
    report, captured = fixture_case(tmp_path, monkeypatch, body)
    finding = report["results"][0]
    finding["end"] = position(body, body.index(b"\n"))
    finding["extra"]["lines"] = "hashlib.sha1(b'x')"
    reviewed_fixture(tmp_path, monkeypatch, report, captured)
    start = body.index(b"hashlib.sha1", 1)
    finding["start"], finding["end"] = position(body, start), position(body, len(body) - 1)
    assert assess(report, captured)["policy_accepted"] is False


def test_whole_pack_change_outside_the_rule_does_not_inherit_a_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    reviewed_fixture(tmp_path, monkeypatch, report, captured)
    changed = replace(captured, official_pack=captured.official_pack + b"# outside the identified rule\n")
    assert assess(report, changed)["policy_accepted"] is False


def test_identical_rule_bytes_at_another_pack_offset_do_not_inherit_a_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    rule = captured.rule_definitions[0]
    copied_definition = captured.official_pack[rule.start_byte : rule.end_byte]
    pack = captured.official_pack + copied_definition
    captured = replace(captured, official_pack=pack)
    reviewed_fixture(tmp_path, monkeypatch, report, captured)
    copied = replace(rule, start_byte=len(captured.official_pack) - len(copied_definition), end_byte=len(pack))
    changed = replace(captured, rule_definitions=(copied,))
    assert copied.sha256 == rule.sha256
    assert assess(report, changed)["policy_accepted"] is False


@pytest.mark.parametrize("change", ["duplicate-rule", "wrong-rule-span", "symlink-source", "symlink-ancestor"])
def test_invalid_definition_or_aliased_source_never_reaches_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    monkeypatch.setattr(policy, "APPROVED_MAP_SHA256", "a" * 64)
    monkeypatch.setattr(policy, "_approved_map", lambda: pytest.fail("Invalid input reached map"))
    if change == "duplicate-rule":
        captured = replace(captured, rule_definitions=captured.rule_definitions * 2)
    elif change == "wrong-rule-span":
        rule = captured.rule_definitions[0]
        captured = replace(captured, rule_definitions=(replace(rule, start_byte=rule.start_byte + 1),))
    elif change == "symlink-source":
        source = tmp_path / "selected.py"
        copy = tmp_path / "actual.py"
        copy.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(copy)
    else:
        alias = tmp_path / "alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        monkeypatch.setattr(policy, "ROOT", alias)
    assert assess(report, captured)["policy_disposition"] == "REFUSED"


@pytest.mark.parametrize("change", ["drift", "duplicate-json", "oversized", "symlink", "directory", "missing"])
def test_fixed_map_is_bounded_regular_duplicate_safe_and_pinned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    reviewed_fixture(tmp_path, monkeypatch, report, captured)
    path = tmp_path / policy.MAP_PATH
    if change == "drift":
        path.write_bytes(path.read_bytes() + b" ")
    elif change == "duplicate-json":
        install_fixture(tmp_path, monkeypatch, b'{"cases":[],"cases":[]}')
    elif change == "oversized":
        path.write_bytes(b" " * (policy.MAX_MAP_BYTES + 1))
    elif change == "symlink":
        target = tmp_path / "copied-map.json"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
    elif change == "directory":
        path.unlink()
        path.mkdir()
    else:
        path.unlink()
    assert assess(report, captured)["policy_accepted"] is False


@pytest.mark.parametrize(
    "body", ["label='é';hashlib.sha1(b'x')\n", "# é\nhashlib.sha1(\n b'x'\n)\n", "hashlib.sha1(b'x')   \t\r\n"]
)
def test_utf8_and_multiline_byte_positions_bind_exact_source_spans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch, body.encode())
    reviewed_fixture(tmp_path, monkeypatch, report, captured)
    assert assess(report, captured)["policy_accepted"] is True
    report["results"][0]["start"]["offset"] -= 1
    assert assess(report, captured)["policy_accepted"] is False


def test_reported_lines_follow_pinned_end_line_inclusive_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = b"hashlib.sha1(b'x')\nnext_line = 1\n"
    report, captured = fixture_case(tmp_path, monkeypatch, body)
    finding = report["results"][0]
    finding["end"] = position(body, body.index(b"\n") + 1)
    finding["extra"]["lines"] = "hashlib.sha1(b'x')\nnext_line = 1"
    reviewed_fixture(tmp_path, monkeypatch, report, captured)
    assert assess(report, captured)["policy_accepted"] is True


@pytest.mark.parametrize("change", ["consumer", "yaml", "new", "delete", "rename", "mode", "matcher-byte"])
def test_whole_tracked_context_expires_after_any_other_source_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    reviewed_fixture(tmp_path, monkeypatch, report, captured)
    if change == "consumer":
        (tmp_path / "other.py").write_text("security_consumer = 'changed trusted input assumptions'\n")
    elif change == "yaml":
        (tmp_path / "caller.yml").write_text("trusted: changed\n")
    elif change == "new":
        (tmp_path / "new-consumer.js").write_text("const consumer = 'new';\n")
    elif change == "delete":
        (tmp_path / "caller.yml").unlink()
    elif change == "rename":
        git(tmp_path, "mv", "caller.yml", "renamed.yml")
    elif change == "mode":
        (tmp_path / "other.py").chmod(0o755)
    else:
        path = tmp_path / policy.MODULE_PATH
        path.write_bytes(path.read_bytes() + b"# any other matcher byte changes the context\n")
    commit(tmp_path)
    after = policy.capture_inputs(captured.targets, captured.official_pack, captured.rule_definitions)
    assert after.repository.sha256 != captured.repository.sha256
    assert not assess(report, captured, after)["policy_accepted"]
    assert not assess(report, after)["policy_accepted"]


@pytest.mark.parametrize(
    "change", ["assume-unchanged", "skip-worktree", "index-overlay", "head-overlay", "unknown-mode"]
)
def test_index_flags_and_restored_working_bytes_cannot_hide_committed_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    reviewed_fixture(tmp_path, monkeypatch, report, captured)
    source = tmp_path / "other.py"
    original = source.read_bytes()
    if change in ("assume-unchanged", "skip-worktree"):
        git(tmp_path, "update-index", "--" + change, "other.py")
    elif change == "index-overlay":
        source.write_bytes(b"changed = 1\n")
        git(tmp_path, "add", "other.py")
        source.write_bytes(original)
    elif change == "head-overlay":
        source.write_bytes(b"changed = 1\n")
        commit(tmp_path)
        source.write_bytes(original)
    else:
        source.unlink()
        source.symlink_to(tmp_path / "selected.py")
        commit(tmp_path)
    assert not assess(report, captured)["policy_accepted"]


def test_fixed_map_must_be_committed_not_merely_present_or_added(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    reviewed_fixture(tmp_path, monkeypatch, report, captured)
    git(tmp_path, "rm", "--cached", policy.MAP_PATH)
    git(tmp_path, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "untrack map")
    result = assess(report, captured)
    assert not result["policy_accepted"]
    assert "committed" in result["reason"]


def test_only_literal_pin_normalization_breaks_the_inventory_size_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, captured = fixture_case(tmp_path, monkeypatch)
    path = tmp_path / policy.MODULE_PATH
    path.write_bytes(path.read_bytes().replace(b"= None", b'= "' + b"a" * 64 + b'"'))
    commit(tmp_path)
    after = policy.repository_inventory()
    assert after.sha256 == captured.repository.sha256
    assert after.records == captured.repository.records
    assert after.raw_sha256[policy.MODULE_PATH] != captured.repository.raw_sha256[policy.MODULE_PATH]
    assert after.head_sha256[policy.MODULE_PATH] == after.raw_sha256[policy.MODULE_PATH]
    assert after.fingerprints != captured.repository.fingerprints


def test_uncommitted_pin_only_overlay_is_refused_even_when_normalized_context_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    reviewed_fixture(tmp_path, monkeypatch, report, captured)
    path = tmp_path / policy.MODULE_PATH
    original = path.read_bytes()
    changed = original.replace(b"= None", b'= "' + b"a" * 64 + b'"')
    assert policy._normalize_pin(original) == policy._normalize_pin(changed)
    path.write_bytes(changed)
    with pytest.raises(policy.Refusal, match="raw bytes overlay committed HEAD"):
        policy.repository_inventory()
    assert not assess(report, captured)["policy_accepted"]


@pytest.mark.parametrize(
    "declaration",
    [
        "APPROVED_MAP_SHA256 = None\n",
        "APPROVED_MAP_SHA256: object = None\n",
        "APPROVED_MAP_SHA256: str | None = 'a' * 64\n",
        "APPROVED_MAP_SHA256: str | None = None\nAPPROVED_MAP_SHA256 = None\n",
        "APPROVED_MAP_SHA256: str | None = None\ndef f():\n APPROVED_MAP_SHA256 = None\n",
        "APPROVED_MAP_SHA256: str | None = '" + "a" * 64 + "'\n",
        'APPROVED_MAP_SHA256: str | None = "' + "A" * 64 + '"\n',
    ],
)
def test_duplicate_computed_or_altered_pin_declarations_refuse_normalization(declaration: str) -> None:
    with pytest.raises(policy.Refusal):
        policy._normalize_pin(declaration.encode())


@pytest.mark.parametrize("budget", ["MAX_INVENTORY_FILES", "MAX_INVENTORY_FILE_BYTES", "MAX_INVENTORY_TOTAL_BYTES"])
def test_repository_inventory_fails_closed_at_each_resource_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, budget: str
) -> None:
    fixture_case(tmp_path, monkeypatch)
    monkeypatch.setattr(policy, budget, 1)
    with pytest.raises(policy.Refusal):
        policy.repository_inventory()


def test_partial_or_changed_body_during_inventory_capture_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture_case(tmp_path, monkeypatch)
    original = policy._git
    changed = False

    def observe(*args: str, maximum: int = 8 * 1024 * 1024) -> bytes:
        nonlocal changed
        result = original(*args, maximum=maximum)
        if args[:2] == ("cat-file", "blob") and not changed:
            changed = True
            (tmp_path / "caller.yml").write_bytes(b"partial")
        return result

    monkeypatch.setattr(policy, "_git", observe)
    with pytest.raises(policy.Refusal):
        policy.repository_inventory()


def test_actual_git_body_output_is_bounded_before_buffering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture_case(tmp_path, monkeypatch)
    blob = policy._tracked()["other.py"]
    assert blob.size > 2
    with pytest.raises(policy.Refusal, match="failed or exceeded"):
        policy._git("cat-file", "blob", blob.oid, maximum=2)


def test_already_captured_body_drift_during_a_later_file_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture_case(tmp_path, monkeypatch)
    original = policy._git
    count = 0

    def observe(*args: str, maximum: int = 8 * 1024 * 1024) -> bytes:
        nonlocal count
        result = original(*args, maximum=maximum)
        if args[:2] == ("cat-file", "blob"):
            count += 1
            if count == 2:
                (tmp_path / "caller.yml").write_text("untrusted: later-change\n")
        return result

    monkeypatch.setattr(policy, "_git", observe)
    with pytest.raises(policy.Refusal, match="Previously captured"):
        policy.repository_inventory()


def test_alternate_index_environment_cannot_hide_a_real_index_overlay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture_case(tmp_path, monkeypatch)
    alternate = tmp_path / "saved-index"
    shutil.copyfile(tmp_path / ".git/index", alternate)
    caller = tmp_path / "caller.yml"
    original = caller.read_bytes()
    caller.write_text("changed: staged\n")
    git(tmp_path, "add", "caller.yml")
    caller.write_bytes(original)
    monkeypatch.setenv("GIT_INDEX_FILE", str(alternate))
    with pytest.raises(policy.Refusal, match="Index overlays"):
        policy.repository_inventory()


def test_git_directory_environment_cannot_select_another_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture_case(tmp_path, monkeypatch)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "missing-foreign-git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "missing-foreign-worktree"))
    assert policy.repository_inventory().records


@pytest.mark.parametrize("variant", [0, 1])
def test_each_exact_variant_selects_only_its_own_case_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: int
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    value = reviewed_fixture(tmp_path, monkeypatch, report, captured)
    selected = captured if variant == 0 else alternate_variant(captured)
    result = assess(report, selected)
    assert result["policy_accepted"] is True and result["raw_exit_code"] == 1
    assert result["raw_finding_count"] == result["inapplicable_finding_count"] == 1
    assert result["official_pack_sha256"] == value["variants"][variant]["official_pack_sha256"]


@pytest.mark.parametrize(
    "defect",
    [
        "duplicate",
        "unknown",
        "missing",
        "extra",
        "cross-cases",
        "other-empty",
        "other-duplicate",
        "other-unknown-source",
    ],
)
def test_variant_duplicates_unknowns_and_cross_pack_cases_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    value = reviewed_fixture(tmp_path, monkeypatch, report, captured)
    variants = value["variants"]
    if defect == "duplicate":
        variants[1] = deepcopy(variants[0])
    elif defect == "unknown":
        variants[1]["official_pack_sha256"] = "0" * 64
    elif defect == "missing":
        variants.pop()
    elif defect == "extra":
        variants.append(deepcopy(variants[0]))
    elif defect == "cross-cases":
        variants[0]["cases"], variants[1]["cases"] = variants[1]["cases"], variants[0]["cases"]
    elif defect == "other-empty":
        variants[1]["cases"] = []
    elif defect == "other-duplicate":
        variants[1]["cases"] *= 2
    else:
        variants[1]["cases"][0]["identity"]["source_path"] = "unknown.py"
    install_fixture(tmp_path, monkeypatch, value)
    result = assess(report, captured)
    assert result["policy_accepted"] is False and result["raw_exit_code"] == 1


@pytest.mark.parametrize("code", [0, 1])
def test_unknown_actual_pack_cannot_succeed_even_with_a_clean_raw_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    unknown = replace(captured, official_pack=captured.official_pack + b"# unreviewed third representation\n")
    if code == 0:
        report["results"] = []
    monkeypatch.setattr(policy, "_approved_map", lambda: pytest.fail("Unknown actual pack reached map matching"))
    result = assess(report, unknown, code=code)
    assert result["policy_disposition"] == "REFUSED" and not result["policy_accepted"]
    assert result["raw_exit_code"] == code


def test_variant_array_order_cannot_select_another_caseset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report, captured = fixture_case(tmp_path, monkeypatch)
    value = reviewed_fixture(tmp_path, monkeypatch, report, captured)
    value["variants"].reverse()
    install_fixture(tmp_path, monkeypatch, value)
    assert assess(report, captured)["policy_accepted"] is True
    assert assess(report, alternate_variant(captured))["policy_accepted"] is True
