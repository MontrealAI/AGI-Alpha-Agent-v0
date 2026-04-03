[See docs/DISCLAIMER_SNIPPET.md](../../../../docs/DISCLAIMER_SNIPPET.md)

# Repo-Healer v1 scratchpad (current repo state)

1. **Canonical evaluator surface now**
   - PR gate: `✅ PR CI` in `.github/workflows/pr-ci.yml` (`ruff check .` + smoke pytest subset).
   - Full post-merge gate: `🚀 Integration CI — Insight Demo` in `.github/workflows/ci.yml` (actionlint, Ruff, Mypy, pytest, docs/build checks).
   - Optional/manual surfaces: `🔥 Smoke Test` and `📚 Docs`.
2. **Toy-specific leftovers identified**
   - Legacy entrypoint and fixture (`sample_broken_calc`) remain for demo mode only.
   - Legacy `patcher_core.py` still uses unstructured logs and `pytest -q` defaults (kept as compatibility/demo utility).
3. **Narrow truthful v1**
   - `repo_healer_v1` is the production path: typed failure bundles, deterministic triage, bounded candidate generation, isolated apply+replay, and structured reporting.
4. **Overclaim areas corrected**
   - Demo README now describes support tiers, report-only fallbacks, and benchmark outcomes explicitly; unsupported surfaces are diagnose/draft-only.
