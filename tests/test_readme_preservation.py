# SPDX-License-Identifier: Apache-2.0
"""Badge maintenance must not weaken the original-content preservation rule."""
from scripts.check_agent_preservation import normalize_badge_urls


def test_badge_queries_may_change_without_changing_content() -> None:
    url = b"https://github.com/montrealai/AGI-Alpha-Agent-v0/actions/workflows/smoke.yml"
    original = b"[![Smoke](" + url + b"/badge.svg)](" + url + b")\nFLYWHEEL"
    updated = original.replace(b"badge.svg)", b"badge.svg?branch=main)").replace(b".yml)", b".yml?query=branch%3Amain)")
    assert normalize_badge_urls(original) == normalize_badge_urls(updated)
    assert normalize_badge_urls(original) != normalize_badge_urls(updated.replace(b"FLYWHEEL", b""))
    assert normalize_badge_urls(original) != normalize_badge_urls(updated.replace(b"Smoke", b"Always passing"))
