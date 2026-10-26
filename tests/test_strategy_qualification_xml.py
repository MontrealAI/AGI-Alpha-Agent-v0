# SPDX-License-Identifier: Apache-2.0
"""Collector-local JUnit bounds; no companion mission or browser is executed."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import ParseError
import pytest

SOURCE = Path(__file__).resolve().parents[1] / "contrib/strategy_succession/qa/collect_qualification.py"
SPEC = importlib.util.spec_from_file_location("strategy_qualification_collector", SOURCE)
assert SPEC is not None and SPEC.loader is not None
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


@pytest.mark.parametrize(
    "raw",
    [
        b'<testsuite name="transport"><testcase name="bounds"/></testsuite>',
        b'<?xml version="1.0" encoding="UTF-8"?><testsuites><testsuite tests="2"><testcase name="one"/><testcase name="two"><system-out>Escaped &lt;data&gt;, not a declaration.</system-out></testcase></testsuite></testsuites>',
        '<testsuite><testcase name="vérification">Valid UTF-8 data.</testcase></testsuite>'.encode(),
    ],
)
def test_actual_nonempty_passing_junit_is_accepted(tmp_path: Path, raw: bytes) -> None:
    report = tmp_path / "normal.xml"
    report.write_bytes(raw)
    assert collector.verify_junit(report) is None


@pytest.mark.parametrize("tag", ["failure", "error", "skipped"])
def test_failed_error_and_skipped_cases_cannot_be_qualified(tmp_path: Path, tag: str) -> None:
    report = tmp_path / "rejected.xml"
    report.write_text(f'<testsuites><testsuite><testcase name="held"><{tag}/></testcase></testsuite></testsuites>')
    with pytest.raises(ValueError, match="no failure, error or skip"):
        collector.verify_junit(report)


@pytest.mark.parametrize(
    "raw",
    [
        b'<testsuite tests="0"/>',
        b'<testsuites><testsuite tests="0"/></testsuites>',
        b'<not-junit><testcase name="forged"/></not-junit>',
        b"",
        b"<testsuite><testcase></testsuite>",
        b"not XML at all",
    ],
)
def test_empty_wrong_shape_and_malformed_reports_are_refused(tmp_path: Path, raw: bytes) -> None:
    report = tmp_path / "invalid.xml"
    report.write_bytes(raw)
    with pytest.raises((ValueError, ParseError)):
        collector.verify_junit(report)


@pytest.mark.parametrize(
    "declaration,content",
    [
        ("<!DOCTYPE testsuite>", ""),
        ('<!DOCTYPE testsuite [<!ENTITY local "forged passing output">]>', "&local;"),
        ('<!DOCTYPE testsuite SYSTEM "https://invalid.example/no-network.dtd">', ""),
        ('<!DOCTYPE testsuite [<!ENTITY external SYSTEM "file:///not-an-approved-input">]>', "&external;"),
        ('<!DOCTYPE testsuite [<!ENTITY % external SYSTEM "https://invalid.example/no-network.dtd">%external;]>', ""),
    ],
)
def test_dtd_internal_external_and_parameter_entities_are_refused(
    tmp_path: Path, declaration: str, content: str
) -> None:
    report = tmp_path / "untrusted.xml"
    report.write_text(declaration + '<testsuite><testcase name="attempt">' + content + "</testcase></testsuite>")
    with pytest.raises(DefusedXmlException):
        collector.verify_junit(report)


def test_external_file_entity_never_imports_its_contents(tmp_path: Path) -> None:
    other = tmp_path / "outside-data.txt"
    marker = "SYNTHETIC_DATA_MUST_NOT_BECOME_JUNIT"
    other.write_text(marker)
    report = tmp_path / "external.xml"
    report.write_text(
        '<!DOCTYPE testsuite [<!ENTITY data SYSTEM "' + other.as_uri() + '">]>'
        '<testsuite><testcase name="attempt">&data;</testcase></testsuite>'
    )
    with pytest.raises(DefusedXmlException) as failure:
        collector.verify_junit(report)
    assert marker not in str(failure.value)


def test_oversized_report_is_rejected_before_xml_parsing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report = tmp_path / "large.xml"
    with report.open("wb") as stream:
        stream.truncate(collector.MAX_JUNIT_BYTES + 1)

    def unexpected_parse(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("Oversized files must never reach the XML parser")

    monkeypatch.setattr(collector.SafeET, "fromstring", unexpected_parse)
    with pytest.raises(ValueError, match="bounded nonempty regular file"):
        collector.verify_junit(report)


@pytest.mark.parametrize("kind", ["file", "ancestor", "directory", "missing"])
def test_junit_input_must_have_regular_file_ancestry(tmp_path: Path, kind: str) -> None:
    real = tmp_path / "real"
    real.mkdir()
    good = real / "passing.xml"
    good.write_text('<testsuite><testcase name="valid"/></testsuite>')
    target = tmp_path / "report.xml"
    if kind == "file":
        target.symlink_to(good)
    elif kind == "ancestor":
        alias = tmp_path / "alias"
        alias.symlink_to(real, target_is_directory=True)
        target = alias / good.name
    elif kind == "directory":
        target.mkdir()
    with pytest.raises(ValueError):
        collector.verify_junit(target)


def test_nonregular_fifo_is_refused_without_waiting_for_a_writer(tmp_path: Path) -> None:
    report = tmp_path / "fifo.xml"
    os.mkfifo(report)
    with pytest.raises(ValueError):
        collector.verify_junit(report)


def test_parent_traversal_does_not_gain_report_authority(tmp_path: Path) -> None:
    report = tmp_path / "valid.xml"
    report.write_text('<testsuite><testcase name="valid"/></testsuite>')
    nested = tmp_path / "nested"
    nested.mkdir()
    with pytest.raises(ValueError):
        collector.verify_junit(nested / ".." / report.name)
