[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)

# Self-Healing Repo / Repo-Healer v1

Repo-Healer v1 is a **bounded CI repair engine for this repository** (`AGI-Alpha-Agent-v0`).
The legacy `sample_broken_calc` fixture remains only as a demo seed and is not the default repair path.

## Scratchpad (current repo truth)

1. **Canonical evaluator surface now**: PR gate is `.github/workflows/pr-ci.yml` (`ruff check .` + smoke test subset).
   Full post-merge/manual validation surface includes `.github/workflows/ci.yml` (mypy, pytest, docs, docker, cross-platform jobs).
2. **Toy-specific leftovers removed from core path**: no clone-first workflow, no raw-log-only input, no `pytest -q`-only validator path.
3. **Narrow truthful v1**: structured bundle triage + policy mode + validator registry + bounded patch loop + seeded benchmark.
4. **Overclaim fixed**: docs now explicitly separate autopatch, draft-only, and diagnose-only support tiers.

## Support tiers

### Tier 1 (autopatch-safe)
- Ruff failures.
- Mypy failures.
- Broken imports/simple Python regressions.
- Linux reproducible pytest/smoke failures.
- MkDocs failures reproducible on Linux.

### Tier 2 (draft/report only)
- Workflow/actionlint.
- Docker build failures.
- Windows-only or macOS-only failures.

### Tier 3 (hard refusal)
- Secrets/tokens/credentials/signing/publishing flows.
- Branch-protection weakening and CI bypass edits.
- Changes meant to skip/disable evaluators.

## Architecture

- `repo_healer_v1/models.py`: typed failure bundle, triage decision, validator class, support mode.
- `repo_healer_v1/triage.py`: decision model with required classes (`SAFE_AUTOPATCH`, `DRAFT_PR_ONLY`, etc.).
- `repo_healer_v1/validators.py`: registry aligned to current repo CI commands.
- `repo_healer_v1/safety.py`: existing-file-only and protected-surface policy.
- `repo_healer_v1/engine.py`: bounded repair loop with rollback and targeted-then-broader validation.
- `repo_healer_v1/benchmark.py`: seeded failure benchmark in an isolated temp clone.

## Report modes

- `AUTOPATCH_SAFE`: apply patch + validators.
- `DRAFT_PR_ONLY`: analyze and emit structured diagnosis for human-authored PR.
- `REPORT_ONLY`: no patch apply; emit machine-readable report only.

Fork/low-permission contexts should force `REPORT_ONLY`.

## Local replay

```bash
python -m alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.cli \
  --repo . \
  --failure-bundle repo_healer_bundle.json \
  --candidates repo_healer_candidates.json \
  --report repo_healer_report.json
```

Add `--dry-run` to validate policy/safety without writing files.

## Seeded benchmark

```bash
python -m alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.benchmark \
  --repo . \
  --out repo_healer_benchmark.json
```

The benchmark:
- runs in a temporary copy of this repo,
- seeds Ruff, mypy, import, smoke, docs, and one non-autofix refusal case,
- compares baseline vs healed exit codes,
- emits machine-readable JSON.

## CI integration

Workflow: `.github/workflows/repo-healer.yml`

- Trigger: failures from current CI surfaces (`✅ PR CI`, `🚀 CI — Insight Demo`, `🔥 Smoke Test`) and manual dispatch.
- Artifacts:
  - `repo_healer_bundle.json`
  - `repo_healer_candidates.json`
  - `repo_healer_report.json`

## Legacy demo wrapper

`agent_selfheal_entrypoint.py` and `sample_broken_calc/` remain for UI illustration only.
