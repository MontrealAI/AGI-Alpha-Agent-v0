# SPDX-License-Identifier: Apache-2.0
"""The advisory gate must not pass on missing or unexamined packages."""

import copy

import pytest

from scripts.audit_agent_dependencies import validate_report

LOCK = "example_pkg==1.2.3 \\\n    --hash=sha256:abc\nother==2.0.0 \\\n    --hash=sha256:def\n"
REPORT = {
    "dependencies": [
        {"name": "example-pkg", "version": "1.2.3", "vulns": []},
        {"name": "other", "version": "2.0.0", "vulns": []},
    ]
}


def test_complete_matching_audit() -> None:
    assert validate_report(LOCK, REPORT) == 2


@pytest.mark.parametrize("problem", ["missing", "duplicate", "version", "skipped", "vulnerable", "incomplete"])
def test_incomplete_or_advisory_audit_blocks_release(problem: str) -> None:
    report = copy.deepcopy(REPORT)
    if problem == "missing":
        report["dependencies"].pop()
    elif problem == "duplicate":
        report["dependencies"].append(report["dependencies"][0])
    elif problem == "version":
        report["dependencies"][0]["version"] = "0.0.1"
    elif problem == "skipped":
        report["dependencies"][0]["skip_reason"] = "not available"
    elif problem == "vulnerable":
        report["dependencies"][0]["vulns"] = [{"id": "TEST-advisory"}]
    else:
        del report["dependencies"][0]["vulns"]
    with pytest.raises(ValueError):
        validate_report(LOCK, report)
