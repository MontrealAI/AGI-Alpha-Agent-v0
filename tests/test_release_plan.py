# SPDX-License-Identifier: Apache-2.0
"""Negative controls for the conservative editorial tier and exact plan binding."""

from __future__ import annotations

import pytest

from pathlib import Path
from scripts.build_service_worker import is_cache_asset

from scripts.release_plan import (
    MAX_DOCUMENT_BYTES,
    plan_for_full_scope,
    plan_for_proved_scope,
    prove_editorial_document,
    verify_plan,
)


@pytest.mark.parametrize(
    "after",
    [
        b"Corrected earlier wording.\n",
        b"## Heading\n\n[Ordinary link](https://example.org/)\n",
        b"<details><summary>Notes</summary>Editorial text</details>\n",
        b"```text\nExample\n```\n",
        "Clarification française.\n".encode(),
        b"",
    ],
)
def test_ordinary_editorial_edits_are_allowed_without_publishing_them(after: bytes) -> None:
    prove_editorial_document(b"Previous wording\n", after)


@pytest.mark.parametrize("before,after", [(b"old", b"\xff"), (b"\xff", b"new")])
def test_editorial_text_requires_utf8(before: bytes, after: bytes) -> None:
    with pytest.raises(UnicodeError):
        prove_editorial_document(before, after)


def test_document_size_uses_existing_git_proof_bound() -> None:
    with pytest.raises(ValueError):
        prove_editorial_document(b"old", b"a" * (MAX_DOCUMENT_BYTES + 1))


def test_editorial_markdown_is_not_a_service_worker_runtime_input() -> None:
    assert not is_cache_asset(Path("CHANGELOG.md"))


@pytest.mark.parametrize("has_papers", [True, False])
def test_plan_is_descriptive_and_never_claims_new_software_or_reused_test_results(has_papers: bool) -> None:
    plan = plan_for_proved_scope("a" * 40, "b" * 40, has_paper_changes=has_papers)
    assert verify_plan(plan.to_dict(), plan) == plan
    assert plan.software_checks == plan.software_publication == "not-applicable"
    assert plan.component_reuse is False
    assert plan.paper_publication == ("run" if has_papers else "not-applicable")


@pytest.mark.parametrize(
    "key,value",
    [
        ("schema", "agialpha.release-plan.v2"),
        ("source_commit", "c" * 40),
        ("base_commit", "d" * 40),
        ("tier", "full"),
        ("software_checks", "passed"),
        ("software_publication", "run"),
        ("paper_publication", "run"),
        ("component_reuse", True),
        ("component_reuse", 0),
        ("unexpected", "claim"),
    ],
)
def test_plan_cannot_override_independent_scope_proof(key: str, value: object) -> None:
    expected = plan_for_proved_scope("a" * 40, "b" * 40, has_paper_changes=False)
    with pytest.raises(ValueError):
        verify_plan({**expected.to_dict(), key: value}, expected)


def test_missing_plan_field_is_rejected() -> None:
    expected = plan_for_proved_scope("a" * 40, "b" * 40, has_paper_changes=False)
    raw = expected.to_dict()
    del raw["base_commit"]
    with pytest.raises(ValueError):
        verify_plan(raw, expected)


def test_full_fallback_retains_required_checks_and_does_not_claim_acceptance() -> None:
    plan = plan_for_full_scope("a" * 40)
    assert plan.tier == "full"
    assert plan.software_checks == "run"
    assert plan.software_publication == "requires-full-acceptance"
    assert plan.component_reuse is False
    assert verify_plan(plan.to_dict(), plan) == plan


@pytest.mark.parametrize("sha", ["main", "a" * 39, "A" * 40, "b" * 40, None])
def test_plan_requires_distinct_exact_identities(sha: object) -> None:
    with pytest.raises(ValueError):
        plan_for_proved_scope(sha, "b" * 40, has_paper_changes=False)  # type: ignore[arg-type]


class _IntegerSubclass(int):
    pass


class _BooleanImpostor:
    def __bool__(self) -> bool:
        raise AssertionError("Classification must not coerce arbitrary objects")

    def __eq__(self, other: object) -> bool:
        raise AssertionError("Classification must not compare arbitrary objects")


@pytest.mark.parametrize(
    "value", [0, 1, 0.0, 1.0, None, "", "true", [], {}, _IntegerSubclass(0), _IntegerSubclass(1), _BooleanImpostor()]
)
def test_classification_requires_bool_singletons(value: object) -> None:
    with pytest.raises(ValueError, match="real, classified transition"):
        plan_for_proved_scope("a" * 40, "b" * 40, has_paper_changes=value)  # type: ignore[arg-type]


def test_verified_plan_rejects_equal_string_subclass() -> None:
    class StringSubclass(str):
        pass

    expected = plan_for_proved_scope("a" * 40, "b" * 40, has_paper_changes=False)
    with pytest.raises(ValueError, match="claims differ"):
        verify_plan({**expected.to_dict(), "tier": StringSubclass(expected.tier)}, expected)
