[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)

# Self-Healing Repo / Repo-Healer v1

Repo-Healer v1 graduates the earlier demo into a bounded repair engine for this repository.
The demo UI still exists, but production repair logic now lives in `repo_healer_v1/` and targets
`AGI-Alpha-Agent-v0` by default via structured failure bundles.

## What v1 can auto-heal (Tier 1)

- Ruff Python lint failures.
- Mypy type failures.
- Broken imports and simple Python config regressions.
- Linux-reproducible pytest/smoke failures.
- MkDocs/docs build failures reproducible locally.

## What v1 only diagnoses (Tier 2)

- Workflow/actionlint issues.
- Docker build issues.
- Windows/macOS-only failures.

## What v1 refuses to patch (Tier 3)

- Secrets, tokens, credentials, signing, release publishing.
- Branch-protection weakening and CI bypass edits.
- Any patch touching protected surfaces (for example workflow guardrails) without manual review.

## Repo-Healer v1 architecture

- `repo_healer_v1/models.py`: structured failure bundle + risk model.
- `repo_healer_v1/triage.py`: classifies failure into auto-fixable, transient, permission, unsafe, unsupported.
- `repo_healer_v1/validators.py`: validator registry keyed by failure class.
- `repo_healer_v1/safety.py`: patch safety policy (existing-file-only default).
- `repo_healer_v1/engine.py`: bounded triage → patch safety → targeted validator → broader validator loop.
- `repo_healer_v1/benchmark.py`: seeded benchmark with machine-readable baseline vs healed report.

## CI integration

Workflow: `.github/workflows/repo-healer.yml`

- Trigger: failed `workflow_run` from real CI workflows (and manual dispatch).
- Emits structured artifacts:
  - `repo_healer_bundle.json`
  - `repo_healer_candidates.json`
  - `repo_healer_report.json`
- Runs in report-only mode by default to avoid fighting CI Health rerun logic and fork permission limits.

## Local replay

```bash
python -m alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.cli \
  --repo . \
  --failure-bundle repo_healer_bundle.json \
  --candidates repo_healer_candidates.json \
  --report repo_healer_report.json \
  --dry-run
```

## Seeded benchmark

```bash
python -m alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.benchmark \
  --repo . \
  --out repo_healer_benchmark.json
```

Benchmark cases include seeded Ruff, mypy, broken import, smoke, docs, and one Tier-2 Windows diagnose-only case.
The benchmark runs in a temporary copy so the main working tree stays untouched.

## Legacy demo wrapper

`agent_selfheal_entrypoint.py` and `sample_broken_calc/` remain for UI illustration, but are no longer the core repair engine.
