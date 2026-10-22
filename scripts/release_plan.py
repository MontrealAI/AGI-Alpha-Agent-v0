# SPDX-License-Identifier: Apache-2.0
"""Conservative, descriptive plans derived from independently proved Git transitions.

A plan is not authorization to skip checks. Consumers must first reproduce the
trusted-base Git proof; fields supplied by a branch or an artifact are not trusted.
Component-result reuse is deliberately not enabled by this policy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Literal

SCHEMA = "agialpha.release-plan.v1"
EDITORIAL_PATH = "docs/CHANGELOG.md"
MAX_DOCUMENT_BYTES = 25_000_000


def prove_editorial_document(before: bytes, after: bytes) -> None:
    """Admit ordinary UTF-8 editorial edits, not new executable or published inputs.

    File identity/mode and complete history are checked by the Git proof caller.
    This document is excluded from paper-site overlays. No release is created or
    newly qualified by this scope, so Markdown links and corrections are allowed.
    The bound matches the existing Git-object proof's maximum blob size.
    """
    if max(len(before), len(after)) > MAX_DOCUMENT_BYTES:
        raise ValueError("Editorial document exceeds existing Git proof bounds")
    before.decode("utf-8")
    after.decode("utf-8")


@dataclass(frozen=True, slots=True)
class ReleasePlan:
    """Small closed schema: scope, identities and planned actions, never fake results."""

    schema: str
    base_commit: str | None
    source_commit: str | None
    tier: Literal["full", "paper", "passive-editorial"]
    software_checks: Literal["run", "not-applicable"]
    software_publication: Literal["requires-full-acceptance", "not-applicable"]
    paper_publication: Literal["run", "not-applicable"]
    component_reuse: Literal[False]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def plan_for_full_scope(head: str | None) -> ReleasePlan:
    """Unknown/mixed/policy inputs retain the existing full acceptance boundary."""
    if head is not None and (not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head)):
        raise ValueError("Full plan requires an exact source identity")
    return ReleasePlan(SCHEMA, None, head, "full", "run", "requires-full-acceptance", "not-applicable", False)


def plan_for_proved_scope(base: str, head: str, *, has_paper_changes: bool) -> ReleasePlan:
    """Describe a completed independent proof; this does not perform that proof."""
    if any(not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha) for sha in (base, head)):
        raise ValueError("Release plans require exact source identities")
    # Identity admits only the two bool singletons, not truthy/equal substitutes.
    if base == head or (has_paper_changes is not True and has_paper_changes is not False):
        raise ValueError("Release plans require a real, classified transition")
    return ReleasePlan(
        SCHEMA,
        base,
        head,
        "paper" if has_paper_changes else "passive-editorial",
        "not-applicable",
        "not-applicable",
        "run" if has_paper_changes else "not-applicable",
        False,
    )


def verify_plan(raw: object, expected: ReleasePlan) -> ReleasePlan:
    """Reject omissions, extra claims and wrong types against a reproduced proof."""
    wanted = expected.to_dict()
    if not isinstance(raw, dict) or raw.keys() != wanted.keys():
        raise ValueError("Release plan shape differs from the independently proved plan")
    if any(type(raw[key]) is not type(value) or raw[key] != value for key, value in wanted.items()):
        raise ValueError("Release plan claims differ from the independently proved plan")
    return expected
