[Project notice](../DISCLAIMER_SNIPPET.md)

# Release readiness — 1.5.1

This release supports a useful, bounded agent on a private operator machine and a self-contained
browser research workspace. It does not establish general intelligence or a production autonomous
economy. Assess it against your workload and the evidence below, rather than an unqualified “10/10”.

## Choose a starting point

| Your goal | Start here | What you receive |
|---|---|---|
| Explore the original white-paper vision | [Ascension Lab](../ascension/index.html), choose a scenario, select Discover | Computed portfolio/schedule, encrypted recovery capsule, modeled economics and downloadable evidence |
| Solve a bounded task with your own inputs | [Browser workspace](../index.html), choose a mission and edit its data | Checked research, allocation, schedule or forecast; explicit review and export |
| Keep a persistent identity, private journal and operator controls | [Install the agent](OPERATIONS.md) from the matching release assets | Five native mission kinds, signed evidence, recovery, optional inference and verified payment receipts |
| Explore earlier experiments | [Demo catalog](DEMO_VALIDATION.md) | Preserved launch paths with explicit execution modes and optional requirements |

Pages needs no sign-in, wallet or API key for its built-in computation. The lightweight workspace
works offline after installation; model text generation needs its separate initial download. Export
work you want to keep. Browser storage is not a substitute for a downloaded recovery capsule and its
separately retained passphrase. See [privacy and offline recovery](PAGES_GUIDE.md).

## What the release gates establish

| Area | Required evidence | Practical limit |
|---|---|---|
| Correctness | Independent algorithm/accounting tests, full Python regression, strict types, Solidity checks | Bounded input domains and finite tests; no general correctness proof |
| Security controls | Authentication/origin checks, private files, signed journal, tamper tests, real Docker isolation | Private single-operator host; not a public multi-tenant service or perfect sandbox |
| Dependencies | Hash-locked installation, full operator Python advisory audit, existing browser audits | A dated advisory snapshot; historical environments and host OS need separate maintenance |
| Recovery | Signed backup/restore, pause, corruption detection, persistent container restart | Backups contain secrets; archive limit 256 MiB; independent checkpoints detect rollback |
| User experience | Real Chromium workflows, mobile 320/390 px, cancellation, offline reload, public HTTPS checks | Browser acceptance covers Chromium; no comprehensive accessibility certification or other-engine certification |
| Delivery | Same tested source/site, exact-commit CI, immutable tag/assets, upload re-download checksums | Hosting and GitHub remain trusted services; freshness checks cannot make separate API writes atomic |
| Preservation | 2,125 baseline paths, README/flywheels, original paper checksum and full catalog | Retention of an experiment does not certify its optional integrations |

Download `release-manifest.json`, `SHA256SUMS` and the versioned validation archive from
[the release](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/tag/v1.5.1). The manifest identifies
the tested commit and workflow. JUnit reports distinguish passing, skipped and expected-failure tests.
The Python audit includes package names/versions, scan time and the exact lock digest; failed or skipped
audits block publication. Prior releases remain immutable recovery checkpoints.

## Upgrade without losing your work

1. Pause the old agent. Verify its journal, make a private backup, and retain its checksum and journal
   head separately. Keep its existing environment and state directory.
2. Download matching 1.5.1 assets and use `install_agent.py` to create a new environment. It checks
   wheel/lock checksums, installs hashed dependencies and runs `pip check`.
3. Restore the backup into a **new** private home. Verify identity and journal head, inspect your
   configuration and confirm the agent remains paused.
4. Stop the old process before using the restored home. Resume deliberately and test representative missions. For rollback, stop the
   new process and restore the pre-upgrade backup into another new home with the prior environment.

There is no journal schema migration in this patch. Existing Ed25519 identities and Nova-Seed formats
remain compatible. Do not run two versions on the same home or discard your pre-upgrade backup.
Exact commands, Windows paths and container operations are in [the operator guide](OPERATIONS.md).

## Boundaries that still require separate evidence

The Ascension economics, Council and governance are browser protocol simulations. The runtime verifies
local-EVM payments; this release has not demonstrated mainnet operation, deployed minting authority,
live DEX activity or an independently audited production token economy. Paper-level AGI/ASI, formal
invariants and physical/economic guarantees remain research claims; the
[implementation map](WHITEPAPER_IMPLEMENTATION.md) records the mathematical corrections and missing evidence.

Long-running service reliability, public internet exposure, additional browsers, comprehensive
accessibility conformance and organization-specific load targets have not been qualified by these
release gates. Operate within the documented private-host scope. Keep your browser, host, Docker and
backups maintained; review new advisories and preserve a tested rollback path for each upgrade.

## Repository administration

The September 26, 2026 audit found main branch protection disabled and no repository rulesets. The
release workflow still gates deployment and publication, but that does not protect direct pushes.
The connected repository API supports the code/release work and does not expose administration writes;
the separate browser session requires sign-in. An administrator must enable the repository rule.

In the repository, open **Settings → Branches → Add classic branch protection rule**. Set the branch
pattern to `main`, enable **Require status checks to pass before merging** and **Require branches to
be up to date**, and select the GitHub Actions checks **Lint (ruff)** and **Smoke tests**. Keep force
pushes and deletions disabled, then save. These are the check-run names reported by GitHub; the
workflow-qualified labels in preserved historical README instructions are not the API context names.
The current [CI enforcement guide](../CI_ENFORCEMENT.md) and helper use the corrected names.

An administrator with an existing appropriately scoped token can alternatively run
`python scripts/verify_branch_protection.py --apply --branch main` and then the same command without
`--apply` to verify. Do not put a token in source, a command argument or a support transcript.
