[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)

# Self-Healing Repo / Repo-Healer v1

Repo-Healer v1 is a **bounded CI repair capability for this repository** (`AGI-Alpha-Agent-v0`).
The legacy UI demo and `sample_broken_calc` fixture still exist, but they are no longer the production repair path.

## Current evaluator surface

- PR gate: **✅ PR CI** (`.github/workflows/pr-ci.yml`) with `ruff check .` plus smoke pytest subset.
- Heavy integration matrix: **🚀 CI — Insight Demo** (`.github/workflows/ci.yml`) with workflow linting, Ruff, Mypy,
  pytest, docs, Docker, and deploy-path checks.
- Additional signal-only workflows: **🔥 Smoke Test**, **📚 Docs**, and **🩺 CI Health**.

Repo-Healer v1 discovers PR gate replay commands from `pr-ci.yml` and uses those commands for Tier-1 local replay.

## Tiered support model

### Tier 1 — supported for bounded repair

- Ruff failures.
- Mypy failures.
- Broken imports/simple Python config regressions.
- Linux reproducible pytest/smoke failures.
- MkDocs `mkdocs build --strict` failures when reproducible locally.

### Tier 2 — diagnose/draft only

- workflow YAML/actionlint issues,
- Docker build failures,
- Windows-only and macOS-only failures.

### Tier 3 — explicit refusal

- Secrets/tokens/credentials/signing/release publish surfaces.
- Branch protection weakening, CI bypasses, skipped validators.
- Permission broadening or policy bypasses.

## Repo-Healer v1 architecture

- `repo_healer_v1/models.py`: typed failure bundle and report model.
- `repo_healer_v1/triage.py`: deterministic classification to support mode.
- `repo_healer_v1/validators.py`: registry of targeted + broader validator commands from real workflows.
- `repo_healer_v1/safety.py`: protected-surface and existing-file-only patch safety policy.
- `repo_healer_v1/engine.py`: isolated repair loop (`triage -> safety -> targeted -> broader -> promote`).
- `repo_healer_v1/benchmark.py`: seeded benchmark in isolated temp copy with machine-readable result.

## Report modes

- `AUTOPATCH_SAFE`: run bounded autopatch loop.
- `DRAFT_PR_ONLY`: produce structured diagnosis and commands for human/draft flow.
- `REPORT_ONLY`: permission/transient/unsafe contexts; no patch application.

## CI integration

Workflow: `.github/workflows/repo-healer.yml`

- Trigger: failed `workflow_run` from real CI workflows + manual dispatch.
- Emits structured artifacts:
  - `repo_healer_bundle.json`
  - `repo_healer_candidates.json`
  - `repo_healer_report.json`
- Current workflow runs report-only by default for fork/permission safety.

In low-permission contexts (forks, missing token, workflow_run read-only metadata), Repo-Healer explicitly degrades to
`REPORT_ONLY` and emits diagnosis artifacts instead of trying to push fixes.

## Local replay

```bash
python -m alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.cli \
  --repo . \
  --failure-bundle repo_healer_bundle.json \
  --candidates repo_healer_candidates.json \
  --report repo_healer_report.json
```

Use `--dry-run` to verify safety/classification and planned validators without applying patches.

## Seeded benchmark (required proof)

```bash
python -m alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.benchmark \
  --repo . \
  --out repo_healer_benchmark.json
```

Cases:
- Ruff seed
- Mypy seed
- broken import seed
- Linux pytest seed
- mkdocs seed
- non-autofix permission/context seed (graceful refusal)

The benchmark runs in an isolated temp copy and reports baseline vs healed exit codes.

## Legacy demo wrapper

`agent_selfheal_entrypoint.py` and `sample_broken_calc/` remain as lightweight fixture/UI examples only.
They are not the canonical Repo-Healer v1 production loop.
