[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)

# Self-Healing Repo / Repo-Healer v1

Repo-Healer v1 is a **bounded CI repair capability for this repository** (`AGI-Alpha-Agent-v0`).
The legacy UI demo and `sample_broken_calc` fixture still exist, but they are no longer the production repair path.

## Maintainer scratchpad (current state)

1. **Canonical evaluator surface now**
   - PR gate: **✅ PR CI** (`.github/workflows/pr-ci.yml`) with `ruff check .` and smoke pytest subset.
   - Heavy integration matrix: **🚀 CI — Insight Demo** (`.github/workflows/ci.yml`) with actionlint, Ruff, Mypy, pytest, docs/deploy/build checks.
   - Optional surfaces: **🔥 Smoke Test** and **📚 Docs** workflows.
2. **What was toy-specific before**
   - defaulting to `sample_broken_calc` clone flow,
   - relying on unstructured logs and placeholder diffs,
   - treating pytest as one-size-fits-all validation.
3. **Narrow truthful v1**
   - typed failure bundle plus GitHub workflow_run ingestion (`ci_bundle.py`),
   - deterministic triage + validator registry aligned to real CI commands,
   - bounded isolated repair loop with patch safety checks,
   - seeded benchmark proving baseline vs healed outcomes on this repo.
4. **Docs that overclaimed**
   - legacy table rows suggesting fully autonomous CI healing to green for every class,
   - toy clone behavior implied as the main production path.

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
- `repo_healer_v1/candidate_generation.py`: deterministic patch synthesis for Tier-1 replayable failures.
- `repo_healer_v1/engine.py`: isolated repair loop (`triage -> safety -> targeted -> broader -> promote`).
- `repo_healer_v1/benchmark.py`: seeded benchmark in isolated temp copy with machine-readable result.


## What Repo-Healer v1 can actually patch today

Repo-Healer v1 is intentionally bounded. It only auto-generates patches for deterministic Tier-1 patterns:

- Ruff unused-import regressions (e.g., `F401`),
- simple mypy assignment regressions introduced in existing files,
- broken imports that reference missing modules,
- Linux pytest/smoke assertion regressions with known string mismatches,
- MkDocs strict-build regressions caused by malformed injected YAML lines.

Anything else is classified into draft-only or report-only modes with a structured diagnosis.

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
- Workflow runs dry-run validation by default and downgrades early run attempts to report-only until rerun surfaces settle.

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

The benchmark runs in an isolated temp copy and reports baseline vs healed exit codes. For determinism and bounded runtime it executes targeted validators only (the full engine still runs targeted + broader validators by default).

## Legacy demo wrapper

`agent_selfheal_entrypoint.py` and `sample_broken_calc/` remain as lightweight fixture/UI examples only.
They are not the canonical Repo-Healer v1 production loop.
