from scripts import verify_branch_protection


EXPECTED_REQUIRED_CHECKS = [
    "✅ PR CI / Lint (ruff)",
    "✅ PR CI / Smoke tests",
]


def test_default_required_checks_match_expectations() -> None:
    assert verify_branch_protection.DEFAULT_REQUIRED_CHECKS == EXPECTED_REQUIRED_CHECKS
