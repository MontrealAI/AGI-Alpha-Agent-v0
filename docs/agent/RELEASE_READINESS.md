[Project notice](../DISCLAIMER_SNIPPET.md)

# Release readiness — 1.22.1 manuscript edition

Sovereign adds a private portfolio → schedule → evidence workflow, explicit result-bound reviews,
durable recovery and independently verifiable exports. Its public page exposes recorded native fixtures;
local operator approval is distinct from independent validator consensus.
[Start the Sovereign workspace](../demos/sovereign_agentic_agialpha_agent_v0.md).

Finance Alpha adds a standard-library paper-research terminal, exact ledger/replay checks,
Python 3.11–3.13 calculation gates and real browser/notebook acceptance. See
[the finance guide](../demos/finance_alpha.md) for the supported
local scope and the separately unverified legacy/testnet integration.

The supported deployment profile is a private, single-operator agent with a persistent signed journal,
plus a self-contained public browser workspace. The final 198-page manuscript is the versioned research
specification. Installation, execution, review, evidence export, recovery and publication have explicit
acceptance gates. The [manuscript map](MANUSCRIPT_ALIGNMENT.md) records implemented behavior and the
research obligations that still need external evidence.

The additive [Ascension protocol](ASCENSION_PROTOCOL.md) is a local-EVM-verified reference suite;
it is not part of the commissioned mainnet deployment profile. Its public [Protocol Desk](../ascension-protocol/index.html)
shows the executable lifecycle and explicit fixture boundaries. Existing agent state requires no migration.

## Choose a starting point

| Your goal | Start here | What you receive |
|---|---|---|
| Review a governance proposal | [Governance Workbench](../solving_agi_governance/index.html) | Nine conditional gates, reproducible dossier and input-bound verification jobs |
| Make an operational decision with your records | [Decision Studio](../studio/index.html) | Eleven cases, editable data, constrained plans, proof backlogs and replayable dossiers |
| Measure whether a learned capability helps new tasks | [Compounding Lab](../compounding/index.html) | Frozen policy, four measured arms, learning/review costs, negative controls and a complete Evidence Docket |
| Turn a claim into reviewed work and retained capability | [Proof Bloom](../bloom/index.html) | Claim → jobs → evidence → review → promotion → memory, with revocation and native signed returns |
| Explore opportunities and test an agent firm | [Insight Atlas](../insight/index.html), choose an expedition | Exact scenario ledger, training/holdout comparisons, claim dossiers and replayable capability history |
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
| Security controls | Authentication/origin checks, measured 512 KiB request limit and 15-second body deadline, private files, signed journal, tamper tests, real Docker isolation | Private single-operator host; not a public multi-tenant service or perfect sandbox |
| Dependencies | Hash-locked installation, full operator Python advisory audit, existing browser audits | A dated advisory snapshot; historical environments and host OS need separate maintenance |
| Recovery | Signed backup/restore, pause, corruption detection, persistent container restart | Backups contain secrets; archive limit 256 MiB; independent checkpoints detect rollback |
| User experience | Real Chromium workflows, mobile 320/390 px, cancellation, offline reload, public HTTPS checks | Browser acceptance covers Chromium; no comprehensive accessibility certification or other-engine certification |
| Delivery | Same tested source/site, exact-commit CI, versioned tag/assets, upload re-download checksums | Hosting and GitHub remain trusted services; checksums do not establish GitHub-enforced release immutability or make separate API writes atomic |
| Manuscript fidelity | Original 198-page PDF, canonical Markdown and 31 figures checked against a pinned source commit | A paper is a research specification, not proof that every proposed scientific capability has been established |
| Transfer evidence | Frozen A-only learning, unseen B tasks, failure/ablation controls, full prior learning charges, cross-runtime replay and all 13 docket sections | Bounded synthetic forecasting; independent evidence, strongest-agent comparisons and calibrated α-WU remain HOLD |
| Preservation | 2,125 baseline paths, README/flywheels, original paper checksum and full catalog | Retention of an experiment does not certify its optional integrations |

Download `release-manifest.json`, `SHA256SUMS` and the versioned validation archive from
[the release](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/tag/v1.22.1). The manifest identifies
the tested commit and workflow. JUnit reports distinguish passing, skipped and expected-failure tests.
The Python audit includes package names/versions, scan time and the exact lock digest; failed or skipped
audits block publication. Retain the matching checksums with prior release assets as recovery checkpoints.

## Upgrade without losing your work

1. Pause the old agent. Verify its journal, make a private backup, and retain its checksum and journal
   head separately. Keep its existing environment and state directory.
2. Download matching 1.22.1 assets and use `install_agent.py` to create a new environment. It checks
   wheel/lock checksums, installs hashed dependencies and runs `pip check`.
3. Restore the backup into a **new** private home. Verify identity and journal head, inspect your
   configuration and confirm the agent remains paused.
4. Stop the old process before using the restored home. Resume deliberately and test representative missions. For rollback, stop the
   new process and restore the pre-upgrade backup into another new home with the prior environment.

There is no journal schema migration in this release. Existing Ed25519 identities, Nova-Seed formats
and v1 Bloom Chronicle events remain compatible. The transfer protocol uses a separate versioned JSON
format and does not rewrite native mission history. Do not run two versions on the same home or discard your pre-upgrade backup.
Exact commands, Windows paths and container operations are in [the operator guide](OPERATIONS.md).

## Boundaries that still require separate evidence

The Ascension economics, Council and governance are browser protocol simulations. The runtime verifies
local-EVM payments; this release has not demonstrated mainnet operation, deployed minting authority,
live DEX activity or an independently audited production token economy. Paper-level AGI/ASI, formal
invariants and physical/economic guarantees remain research claims; the
[latest manuscript map](MANUSCRIPT_ALIGNMENT.md) records the remaining obligations; the
[original white-paper map](WHITEPAPER_IMPLEMENTATION.md) retains its mathematical corrections.

Long-running service reliability, public internet exposure, additional browsers, comprehensive
accessibility conformance and organization-specific load targets have not been qualified by these
release gates. Operate within the documented private-host scope. Keep your browser, host, Docker and
backups maintained; review new advisories and preserve a tested rollback path for each upgrade.

## Repository administration

The September 27, 2026 audit found main branch protection disabled and no repository rulesets. The
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

## Curriculum Lab acceptance

The [Meta-Agentic AGI v3 guide](CURRICULUM_LAB.md) defines the finite grammar and independent review boundary. Release acceptance requires exact Python/JavaScript runs and bundles, answer-leakage and sandbox regressions, royalty accounting checks, wheel launch, mobile/browser accessibility, hostile imports, offline replay, preservation hashes and a public receipt bound to the release commit and exact assets.
