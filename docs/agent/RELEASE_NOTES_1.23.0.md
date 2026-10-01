[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.23.0 — Complete demo catalog and repeatable evidence

This release makes every catalog entry discoverable and gives repeat experiments a safe,
single-command path. It includes the Sovereign session cleanup prepared for 1.22.1. All original
demos, research narratives, presentations, media, manuscript bytes and flowcharts are retained.

## Start here

Follow the [installation guide](START_HERE.md), then run:

```sh
alpha-factory demo list
alpha-factory demo info finance_alpha
alpha-factory demo check finance_alpha
alpha-factory demo run finance_alpha --output-dir ./demo-runs --new-run
```

`--new-run` creates and prints a unique directory under your selected output directory. Repeating
the command retains earlier evidence. Leave it off when you intend to reuse persistent history.
The [walkthrough](DEMOS.md) describes the output and next steps for each supported path; the
[complete inventory](DEMO_VALIDATION.md) distinguishes 17 finite offline demos from nine entries
with separate acceptance or prerequisites.

## Improvements

- Generate both complete inventory tables and current launch headings from the executable catalog,
  and reject drift in CI. All 26 entries now show their current modes and requirements.
- Link Governance, MuZero Planning, MuZero × MCTS × LLM and Insight v1 to their own maintained
  experiences. Preserve Decision Studio and its eleven cases.
- Serve actual image bytes in generated guides while preserving linked badges, source links,
  code examples and Mermaid diagrams.
- Retain validation results for every finite command, including timeouts and missing prerequisites;
  save the report before returning failure. Inventory-only checks do not claim execution.
- Check all 17 finite demos both normally and with `--new-run` from the installed wheel outside
  the repository, with Python network calls blocked and prior output bytes compared afterward.
- Clear Sovereign drafts and review notes when locking, retain saved mandates, and isolate delayed
  unlocks and file reads from later sessions. See the [session cleanup notes](RELEASE_NOTES_1.22.1.md).
- Cancel obsolete release runs that cannot pass the current-main guard, preventing them from
  blocking newer releases. Deployment serialization and every acceptance gate remain in place.

## Validation and delivery

The [dated audit](DEMO_AUDIT_2026-10-01.md) records the local evidence and its limits. The release
workflow gates publication on the exact committed source: dependency advisory audit, full Python
regression, Python 3.11–3.13 runtime/lab matrices, native training, installed-wheel demos, real
Chromium journeys, Docker isolation, manuscript/preservation checks and public HTTPS acceptance.
It packages the tested site without rebuilding it, binds receipts to the commit, and re-downloads
uploaded draft assets to verify their checksums before publication.

Keep `release-manifest.json`, `SHA256SUMS` and the versioned validation archive with the source,
wheel and operator guide. Inspect skipped and expected-failure tests in their JUnit reports;
they are not passing qualifications. The publication workflow's final result is the evidence for
this release, not results copied from an earlier commit.

## Breaking changes and upgrade

No removed demos, journal migration, signed-packet change or mandatory output-path change.
`--new-run` is additive. Machine consumers should recognize `agialpha.demo.validation.v2`, which
adds overall status and explicit separate-acceptance coverage. Consumers of the earlier report
schema should update before parsing new reports.

Pause the old agent, verify and retain a private backup, install matching 1.23.0 assets in a fresh
environment, and restore into a new private home. Verify identity and journal head before resuming.
Keep the previous environment and backup for rollback; never run two versions against one home.
See [release readiness](RELEASE_READINESS.md) for exact scope and upgrade procedures.

The supported scope remains bounded demos and private single-operator operation. Optional external
integrations, independent validation, long-running production operation, mainnet deployment and
paper-level AGI/ASI claims retain their separate evidence requirements in the
[manuscript map](MANUSCRIPT_ALIGNMENT.md). Passing finite examples does not establish those claims.
