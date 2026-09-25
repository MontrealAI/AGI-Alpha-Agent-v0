# SPDX-License-Identifier: Apache-2.0
"""Badge maintenance must not weaken the original-content preservation rule."""
import pytest

from scripts.check_agent_preservation import CI_HEALTH_BADGE, LIVE_CHECK_BADGES, normalize_badge_urls


def test_badge_queries_may_change_without_changing_content() -> None:
    url = b"https://github.com/montrealai/AGI-Alpha-Agent-v0/actions/workflows/smoke.yml"
    original = b"[![Smoke](" + url + b"/badge.svg)](" + url + b")\nFLYWHEEL"
    updated = original.replace(b"badge.svg)", b"badge.svg?branch=main)").replace(b".yml)", b".yml?query=branch%3Amain)")
    assert normalize_badge_urls(original) == normalize_badge_urls(updated)
    assert normalize_badge_urls(original) != normalize_badge_urls(updated.replace(b"FLYWHEEL", b""))
    assert normalize_badge_urls(original) != normalize_badge_urls(updated.replace(b"Smoke", b"Always passing"))


@pytest.mark.parametrize("workflow,badge", LIVE_CHECK_BADGES.items())
def test_live_provider_preserves_the_original_badge_and_flywheel(workflow: str, badge: bytes) -> None:
    image_url = f"https://github.com/montrealai/AGI-Alpha-Agent-v0/actions/workflows/{workflow}.yml/badge.svg".encode()
    original = b"[![Check](" + image_url + b")](/evidence)\nFLYWHEEL"
    updated = original.replace(image_url, badge, 1)
    assert normalize_badge_urls(original) == normalize_badge_urls(updated)
    assert normalize_badge_urls(original) != normalize_badge_urls(updated.replace(b"FLYWHEEL", b""))


@pytest.mark.parametrize(
    "unapproved",
    [
        CI_HEALTH_BADGE.replace(b"/main?", b"/old-passing-branch?"),
        CI_HEALTH_BADGE.replace(b"CI%20watchdog", b"unrelated-check"),
        CI_HEALTH_BADGE.replace(b"MontrealAI", b"another-owner"),
        CI_HEALTH_BADGE + b"&color=green",
        b"https://img.shields.io/badge/CI%20Health-passing-green",
    ],
)
def test_health_badge_exception_rejects_misleading_substitutes(unapproved: bytes) -> None:
    approved = b"[![Health](" + CI_HEALTH_BADGE + b")](/evidence)\nFLYWHEEL"
    assert normalize_badge_urls(approved) != normalize_badge_urls(approved.replace(CI_HEALTH_BADGE, unapproved))
