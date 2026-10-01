[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.23.1 — Whole-catalog preflight and complete guide synchronization

This patch completes the remaining catalog work from PR #4753 on top of the published 1.23.0 release.
All 26 entries, original research, diagrams, media, signed evidence and repeat-run behavior are retained.

## Start here

Install using the [release guide](START_HERE.md), then inspect the complete local installation:

```sh
alpha-factory demo check --all
alpha-factory demo check --all --json
alpha-factory demo run finance_alpha --new-run
```

The check reports 23 launch commands and three guide-only entries. It checks declared Python modules
and bundled files without importing optional training backends, downloading models, launching services
or creating run directories. Exit code 0 means those declared prerequisites are present; code 2 means
one or more commands lack prerequisites. Guide-only entries do not count as failed commands.
Use `check NAME` and that entry's guide for details. Model weights, services and provider access
require the separate checks described in each guide.

## Corrections

- Accept the documented `alpha-factory demo` commands and `info` alias. The existing `demos`
  and `show` forms remain supported; inspecting a command never starts the orchestrator.
- Tie planning-lab Start/Stop controls to active execution and clear cancelled exports. Browser
  acceptance waits for actual training before stopping and checks that cancelled results cannot be downloaded.
  Cancellation is session-local and acknowledged by the training generator before restarting; repeated stop/restart
  checks prevent in-flight progress updates from restoring cancelled results.
- Merge the remaining catalog-wide prerequisite report and installed-wheel acceptance into the
  published launcher, preserving `--new-run`, output-directory import protection and failure reports.
- Generate walkthrough counts from the catalog; remove stale references to 15 and 16 finite examples.
- Synchronize all current heading styles, including Discovery, Curriculum and both MuZero guides.
  Reject ambiguous generated regions before any document is written. Original historical text is retained.
- Correct source-checkout-only prerequisites for demos that also ship in the installed wheel.
- Keep gallery navigation, image rendering, replay evidence and all 1.23.0 fixes.

## Validation and delivery

Publication requires the unchanged exact-commit release acceptance pipeline: full regression,
Python runtime/lab matrices, installed-wheel demos with Python network blocked, native training,
Docker isolation, full/minimal galleries, browser workflows, dependency advisory audit, preservation,
public HTTPS acceptance and uploaded-asset checksum verification. Inspect the release's validation
archive and `release-manifest.json` for results and commit identity; skipped checks are not passes.

The installed-wheel check now also parses the all-catalog prerequisite report before running every
finite demo twice. It verifies that the report is complete, all packaged samples exist, no network
was attempted and checking did not create run state.

## Upgrade and scope

No removed CLI flags, schema changes to existing reports, journal migration or signed-packet changes.
The new aggregate report uses `agialpha.demo.inventory-prerequisites.v1`; per-demo reports and finite
validation retain their existing schemas. Follow [release readiness](RELEASE_READINESS.md): pause,
back up, install matching 1.23.1 assets in a fresh environment, verify identity and journal head,
then resume. Keep the previous environment and backup for rollback; use only one process per home.

The supported scope remains bounded demos and private single-operator operation. Optional services,
independent validation, long-running operations, mainnet deployment and paper-level AGI/ASI claims
retain the evidence requirements in the [manuscript map](MANUSCRIPT_ALIGNMENT.md).
