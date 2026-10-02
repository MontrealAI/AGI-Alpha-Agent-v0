[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.23.2 — Repository setup and release reliability

This patch repairs entry points outside the demo catalog and makes the current operating path easier
to find. Start with the [repository guide](REPOSITORY_GUIDE.md), [first mission](START_HERE.md) or
[complete demo walkthrough](DEMOS.md).

## Changes

- Keep Repo-Healer candidate, validation and benchmark copies free of custom Python environments
  and nested dependency caches. Use the same file selection for comparisons so excluded dependencies
  never appear as proposed deletions. Original environments and project documentation remain untouched.

- Repair the root Docker quickstart's build context and missing compatibility package. The image now
  launches its research API, validates configuration before service imports, runs as a non-root user,
  binds the host port to loopback, reports real health and retains memory in a named volume. Add
  `--help` and `--build-only`; preserve existing `.env` files and create new templates privately.
- Add release-installer `--check-only`, strict checksum-manifest parsing, actionable input/phase errors,
  early offline-wheelhouse validation and safe refusal of existing destinations. Failed installations
  retain their partial environment and explain how to retry. Installation still requires hashes and
  a successful `pip check`.
- Update stale operator/factory guide versions and asset names, add a repository-wide navigation and
  support map, retain previous release notes, and synchronize current package, catalog and browser metadata.
- Require real quickstart-image health/non-root acceptance alongside the existing shared-container gate;
  exercise installer preflight during release packaging and input-failure cases on supported Python versions.

## Validation and preservation

Publication requires the existing complete release gates: full offline regression and coverage,
strict type profiles, dependency audits, Python and installed-wheel matrices, real native training,
browser workflows, containers, local EVM, full/minimal galleries and public-site acceptance.
The release manifest and validation archive contain results for the exact published commit, including
explicit skips and expected failures. Uploaded assets are downloaded again and checksum-verified.

All original paths, manuscript bytes, media, README text and Mermaid flowcharts remain protected by
preservation checks. No original file is removed. The 26-entry demo catalog and its 17 finite launch
contracts remain intact. Existing agent journals need no migration.

## Upgrade

Follow [Operations](OPERATIONS.md): pause, verify and back up the old state; install matching 1.23.2
assets into a new environment; restore into a new private home and test before resuming. Keep the old
environment and pre-upgrade backup for rollback. Docker quickstart users should retain the existing
root `.env`; its API now runs on localhost port 8000 with persistent memory in
`alpha-factory-quickstart-data`. The helper fixes the container port and memory path as documented.

The validated deployment scope remains bounded demos and private single-operator workflows. Optional
historical services, mainnet operation and broader scientific claims retain their documented evidence
boundaries; see [release readiness](RELEASE_READINESS.md) and [manuscript alignment](MANUSCRIPT_ALIGNMENT.md).
