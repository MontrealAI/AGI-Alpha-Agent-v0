# SPDX-License-Identifier: Apache-2.0
"""A release must not race failing or unrelated historical CI."""

from __future__ import annotations

import pytest

from scripts.wait_for_release_ci import assess_runs

SHA = "a" * 40


def run(**overrides: object) -> dict:
    return (
        dict(id=1, head_sha=SHA, head_branch="main", event="push", status="completed", conclusion="success") | overrides
    )


def test_exact_main_push_success() -> None:
    assert assess_runs([run()], SHA)


@pytest.mark.parametrize(
    "override", [{"head_sha": "b" * 40}, {"head_branch": "other"}, {"event": "pull_request"}, {"status": "in_progress"}]
)
def test_unrelated_or_pending_runs_do_not_authorize_release(override: dict) -> None:
    assert not assess_runs([run(**override)], SHA)


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "skipped", "timed_out", None])
def test_unsuccessful_run_blocks_release(conclusion: str | None) -> None:
    with pytest.raises(RuntimeError, match="did not pass"):
        assess_runs([run(conclusion=conclusion)], SHA)


def test_latest_run_must_pass_even_when_an_older_run_passed() -> None:
    with pytest.raises(RuntimeError, match="did not pass"):
        assess_runs([run(), run(id=2, conclusion="failure")], SHA)
    assert not assess_runs([], SHA)
