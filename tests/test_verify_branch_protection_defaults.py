from scripts import verify_branch_protection


EXPECTED_REQUIRED_CHECKS = [
    "✅ PR CI / Lint (ruff)",
    "✅ PR CI / Smoke tests",
    "🚀 CI — Insight Demo / 🧹 Ruff + 🏷️ Mypy (3.11)",
    "🚀 CI — Insight Demo / 🧹 Ruff + 🏷️ Mypy (3.12)",
    "🚀 CI — Insight Demo / ✅ Actionlint",
    "🚀 CI — Insight Demo / ✅ Pytest (3.11)",
    "🚀 CI — Insight Demo / ✅ Pytest (3.12)",
    "🚀 CI — Insight Demo / Windows Smoke",
    "🚀 CI — Insight Demo / macOS Smoke",
    "🚀 CI — Insight Demo / 📜 MkDocs",
    "🚀 CI — Insight Demo / 📚 Docs Build",
    "🚀 CI — Insight Demo / 🐳 Docker build",
    "🚀 CI — Insight Demo / 📦 Deploy",
    "🚀 CI — Insight Demo / 🔒 Branch protection guardrails",
    "🩺 CI Health / CI watchdog",
]


def test_default_required_checks_match_expectations() -> None:
    assert verify_branch_protection.DEFAULT_REQUIRED_CHECKS == EXPECTED_REQUIRED_CHECKS
