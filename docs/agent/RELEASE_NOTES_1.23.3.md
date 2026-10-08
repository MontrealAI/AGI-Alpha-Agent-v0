[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.23.3 — Repair safety and verified release identity

This patch closes concrete file-preservation and release-identity gaps found in the final review.
Start with the [repository guide](REPOSITORY_GUIDE.md), [first mission](START_HERE.md) or
[complete demo walkthrough](DEMOS.md).

## Changes

- Validate repair candidate and annotation paths before invoking tools. Absolute paths, traversal,
  ambiguous path spellings and option-like names are refused. Candidate generation honors triage.
- Reject symbolic links, hard-linked project files and special files in repair workspaces. Copying,
  comparisons and safety checks use the same project-file policy; installed environments and caches
  remain excluded. Recheck source and destination files before promoting a validated repair.
- Apply GNU patches noninteractively, using distinct temporary backups for every touched file.
  Failed patches restore each original file, including files with the same stem. Existing `.bak`,
  `.orig` and `.rej` files remain untouched. Invalid diffs fail before running the patch utility.
- Produce a structured unsafe-workspace report when the CLI refuses a repair input.
- Refresh the Insight CSS/lint toolchain to remove the unpatched `braces` dependency
  ([GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)). Compile Tailwind through
  its maintained PostCSS integration, retain the existing theme configuration and preserve all demo controls.
- Arrange the standalone Insight simulator panels in a responsive workspace with readable form controls,
  keyboard focus and theme-aware labels. Preserve its charts, archive, batch simulation, model controls,
  telemetry, debate arena and exports; require no panel overlap or horizontal page overflow at 1440,
  390 and 320 pixels after offline reload.
- Enable MuZero Stop only after a training run starts, disable duplicate starts while it runs, and
  restore controls on completion/cancellation. Browser acceptance cancels a genuinely active run.
- Verify that an already-public release tag resolves to the tested commit before treating a rerun
  as complete. Missing, mismatched or non-commit tags fail; published assets are never overwritten.
- Synchronize current package, catalog, browser metadata and operator guides for 1.23.3.

## Validation and preservation

Regression tests reproduce outside-path mutation, linked workspaces, same-stem rollback collisions,
existing user backups, links introduced by validation and stale public tags. Publication also requires
the complete existing release gates: full regression and coverage, strict type profiles, dependency
audits, Python and installed-wheel matrices, native training, browser workflows, containers, local EVM,
full/minimal galleries and public-site acceptance. Uploaded assets are downloaded and verified again.
The release manifest and validation archive bind the results, skips and expected failures to the exact
published commit. Previous-release evidence is not reused as authorization.

The full Insight npm graph is audited again, including development tools. Its migrated build must
pass TypeScript, lint, service-worker update tests and real online/offline simulation. Real MuZero
training, desktop/mobile layout, cancellation and container acceptance remain required.

All original paths, manuscript bytes, media, README text and Mermaid flowcharts remain protected by
preservation checks. The 26-entry catalog and its 17 finite launch contracts remain intact.

## Upgrade and supported operation

Follow [Operations](OPERATIONS.md): pause, verify and back up the old state; install matching 1.23.3
assets into a new environment; restore into a new private home and test before resuming. Keep the old
environment and pre-upgrade backup for rollback. No journal or identity migration is required.

Repo-Healer requires a trusted checkout with exclusive access, ordinary project files, trusted
validation commands and GNU patch. A temporary repair copy is not an operating-system sandbox.
Use report-only mode for repositories with unsupported links or special files; preserve the original
checkout and inspect the report. Do not run repair concurrently with another writer. Multi-file
promotion is not crash-atomic. The separate Docker-backed code-mission sandbox remains separately gated.

The validated deployment scope remains bounded demos and private single-operator workflows. Optional
historical services, mainnet operation and broader scientific claims retain their documented evidence
boundaries; see [release readiness](RELEASE_READINESS.md) and [manuscript alignment](MANUSCRIPT_ALIGNMENT.md).
