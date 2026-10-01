[Project notice](../DISCLAIMER_SNIPPET.md)

# Whole-catalog audit — October 1, 2026

The audit covers all 26 entries in `alpha_factory_v1/demos`: 24 demos and two
reference/support entries. The executable catalog defines 17 finite offline launch contracts.
The [complete inventory](DEMO_VALIDATION.md) identifies the other nine entries and their
separate prerequisites. Passing a bounded example does not qualify every retained integration.

## Corrections

- Both complete inventory tables now derive their version, count, modes and descriptions from
  `catalog.json`. The old landing page said 1.14.0 and 14 finite commands despite shipping 1.22.1
  and 17 commands. Several descriptions still referred to replaced implementations.
- Versioned headings inside the current launch sections of 22 individual demo guides now track
  the same catalog release. Historical publication headings and code examples are preserved.
- The catalog launcher supports `--new-run`, which creates a distinct output directory without
  replacing prior evidence. Finance and Sovereign correctly refused repeated writes to an existing
  output path; this option makes a separate repeat experiment a single command. The default
  persistent-history behavior is unchanged. Both the selected run and its parent state directory
  are excluded from inherited Python import paths.
- Governance, MuZero Planning, MuZero × MCTS × LLM and Insight v1 gallery cards now lead to their
  own maintained experiences. The Decision Studio remains available with all eleven cases.
- The walkthrough includes Sovereign, Finance, both MuZero paths, Experience and Discovery.
- Generated documentation uses raw image resources instead of GitHub's HTML blob pages.
  Linked badges, source links, code fences and Mermaid diagrams remain intact.
- Finite validation retains a result for every attempted command, including missing prerequisites,
  nonzero exits and timeouts. It writes the report before returning failure and explicitly lists
  entries requiring separate acceptance. An inventory-only run does not claim execution.
- PR CI now checks documentation synchronization, the relevant regression tests, every finite
  launch contract, and retains the JSON evidence artifact.

## Evidence

| Check | Result |
|---|---|
| Directory/catalog coverage | All 26 entries accounted for |
| Finite launch contracts | All 17 passed; v1/v2 repeated runs retained their six lineage records |
| Focused regression | 52 passed, including failure reporting, catalog drift, gallery routing, repeat runs and launcher boundaries |
| Demo domain regression | 339 passed across Sovereign, Finance, Governance, Discovery, Experience, Curriculum, MATS, catalog and legacy simulation tests |
| Installed wheel | All 17 finite demos launched normally and with `--new-run`: 34 successful launches; original outputs unchanged; Python network calls blocked |
| Insight browser packaging | Both quickstart-PDF and distribution-ZIP tests passed using pinned Node 22.17.1 |
| Browser algorithm tests | 85 passed across the seven `tests/browser/*.test.mjs` suites |
| Source syntax | 310 Python files parsed; 23 shell scripts passed `bash -n` |
| Relative links in the 26 source READMEs | No missing file targets |
| Documentation | `mkdocs build --strict` passed |
| Changed Python tools | Ruff and strict mypy passed |
| Original repository preservation | 2,125 baseline paths and original root README/flywheels retained |
| Factory preservation | 1,005 baseline paths, 46 Mermaid blocks and 23 media files retained |
| Manuscript integrity | Canonical manuscript and figure checksums passed |

The inspected base commit is `101ec3396ff59321a5ab138188abb55fa13ff9d9`.
Its [release acceptance run](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/36875044409)
reported 24 successful jobs when inspected: native demos, real model, full regression, browser
contracts, full/minimal galleries, dependency audit, quality, packaging, historical CI, installed
demo distribution and the Python runtime/Finance/MuZero/Sovereign matrices. Its Pages job was
queued at inspection. These are base-commit results, not evidence for a later commit or a completed
deployment. The PR's own checks identify the commit containing these corrections.

## Remaining qualification boundaries

The broader local regression stopped after 1,208 passes, 37 skips, four expected failures,
two failures and three errors. All five failures/errors originated in the Insight browser build
under the runner's default Node version. With the pinned Node 22.17.1 environment and browser assets,
the build succeeded and both failed packaging tests passed on rerun. The local runner separately
denied Chromium's socket creation, so this audit does not claim a fresh browser-interaction pass
or a completely passing full local regression. The repository's
hosted acceptance jobs remain the gates for browser interaction, container isolation, native
training, installed-wheel behavior and publication. Do not count those as freshly passed merely
because the catalog, documentation or algorithm tests pass.

The supported private-operator and bounded-demo scopes remain those in
[release readiness](RELEASE_READINESS.md) and the
[manuscript implementation map](MANUSCRIPT_ALIGNMENT.md). Independent external validation,
long-running operations, additional native platforms, mainnet deployment and paper-level AGI/ASI
claims require their stated evidence. No demos, diagrams, research narratives or media were
removed to obtain these results.

## Reproduce the changed checks

From the documented development environment at the repository root:

```sh
python -m scripts.sync_demo_catalog_docs --check
python -m scripts.validate_demo_catalog --smoke --output evidence/demo-catalog.json
python -m scripts.run_local_tests tests/test_demo_inventory_docs.py tests/test_demo_validation_report.py tests/test_generate_demo_docs.py tests/test_generate_gallery_html.py tests/test_demo_catalog_regressions.py tests/runtime/test_demo_launcher.py tests/test_demo_quality.py -q
python -m scripts.run_local_tests tests/test_demo_distribution.py -q
node --test tests/browser/*.test.mjs
python -m scripts.generate_demo_docs
python -m scripts.generate_gallery_html
python -m scripts.build_service_worker
mkdocs build --strict
```
