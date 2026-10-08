## 1.24.0 — 2026-10-08 (candidate)

- Add the SUCCESSOR Ω bounded mission lifecycle, exact candidate/proof/authority bindings and explicit succession.
- Preserve Ascension semantics with exact rich-job/market assignment adapters and useful negative-evaluation settlement.
- Add a bilingual browser/native rehearsal and content-preserving release packs below 450,000,000 bytes per file.
- Require new lifecycle, preservation, installed-artifact and public-site gates alongside all existing acceptance.
- See [candidate release notes](docs/agent/RELEASE_NOTES_1.24.0.md) for scope, migration, rollback and qualification limits.

## 1.23.3 — 2026-10-03

- Refresh the audited Insight build toolchain and correct MuZero Start/Stop availability.
- Reject unsafe repair paths, links and special files before mutation and recheck files before promotion.
- Preserve user backups and restore each original file after a partial patch failure.
- Require an existing public release tag to match the tested commit before accepting an idempotent rerun.
- Retain all original files, flowcharts, media and research, with unchanged state formats.
- See [release notes](docs/agent/RELEASE_NOTES_1.23.3.md).

## 1.23.2 — 2026-10-02

- Repair the root Docker quickstart, local binding, persistent memory and non-root API health checks.
- Add read-only release-installer preflight and actionable, state-preserving failure diagnostics.
- Refresh current operator guides and add a repository-wide starting-point and support map.
- Preserve all original files, flowcharts, media and research.
- See [release notes](docs/agent/RELEASE_NOTES_1.23.2.md).

## 1.23.1 — 2026-10-01

- Complete catalog-wide read-only preflight with human-readable and JSON reports.
- Fix stale walkthrough counts and synchronize every current demo heading style.
- Retain installed-wheel, repeat-run, failure-reporting and visual preservation checks.
- See [release notes](docs/agent/RELEASE_NOTES_1.23.1.md).

## 1.23.0 — 2026-10-01

- Synchronize all 26 catalog entries, current launch guides and gallery destinations.
- Add `--new-run` to retain previous evidence; verify all 17 finite demos in both installed-wheel modes.
- Preserve image rendering, Mermaid diagrams, original source and research artifacts.
- Retain complete failure-aware validation reports and enforce catalog acceptance in PR CI.
- Include Sovereign session cleanup and prevent obsolete release runs from blocking publication.
- See [release notes](docs/agent/RELEASE_NOTES_1.23.0.md) for upgrade steps and qualification boundaries.

## 1.13.1 — 2026-09-28

## 1.14.0 — Governance Workbench

- Add nine inspectable proposal gates, five adversarial cases and exact Python/browser replay.
- Export five-file evidence bundles and input-bound Ascension verification jobs.
- Correct the legacy update-rate explanation and repair optional-runtime fallback.
- Preserve original manuscripts, diagrams, presentations and archived research content.


Business 3 now presents a compact research collection, a styled original replay with explicit units, and a dossier-backed candidate value landscape. Original diagrams, media and controls are retained. Browser release gates verify the new visuals and original data.

## 1.13.0 — 2026-09-27

- Deliver Business 3 Enterprise Studio: exact constrained portfolio planning, five editable cases, downside stress and seven portable evidence files with Python/browser parity.
- Export reviewable goal/metric/bounty jobs accepted by Ascension; preserve the existing full lifecycle and clearly distinguish unsubmitted plans from deployed enterprises.
- Repair the Python and console entry points, offline container launcher and executable Colab notebook; add Business 3 to all 15 finite installed-wheel launch contracts.
- Make optional research inference and integrations explicit, restore caller settings, close clients correctly and reject unsupported proof or model-update claims.
- Preserve original flowcharts, PDF/PPTX and historical research material; require exact public assets, notebook execution, real Docker isolation, accessibility and offline acceptance before publication.

## 1.12.2 — 2026-09-27

- Package all six demo CSV samples and 11 unchanged Insight scenario fixtures; run all 14 finite demos from the wheel outside the repository with Python network calls blocked.
- Add read-only prerequisite checks, fail before launching incomplete installs, prevent output-directory module shadowing, and report output errors without losing data.
- Pin finite offline examples to packaged inputs and provider-free settings; retain all advanced launch paths and parent credentials.
- Add a complete demo walkthrough, refresh all 26 additive launch sections, and extend the installed-wheel acceptance matrix across Python 3.11–3.13.
- Preserve every original demo, diagram, media asset and manuscript; retain the existing native/operator and local-EVM release gates.

## 1.12.1 — 2026-09-27

- Reject contradictory signed approvals and boolean/float aliases in native result verification.
- Repair the mirrored Protocol Desk and require exact published assets, receipt downloads, keyboard/accessibility and offline acceptance.
- Include starting, factory and protocol guides in release assets and a linked operator-guide archive; reject dirty tracked release sources.
- Bind public protocol acceptance to the exact release commit/version and retain all original paths, diagrams, media and manuscript bytes.

## 1.12.0 — 2026-09-27

- Updated the Alpha-Factory entry point, operating guide, deployment paths and scope labels while preserving original flowcharts and media.
- Added packaged examples and a native Ascension handoff: exact FusionPlan commitments, tamper checks, reviewed-result binding and externally anchored signature verification.
- Unified cross-platform launchers, corrected source paths and Python support, added an operator-only preflight, and made failed/partial installations stop visibly.
- Added native/JavaScript/Solidity interoperability and package preservation acceptance gates. No journal or contract migration.

## 1.11.0 — 2026-09-27

Add an integrated Ascension Solidity reference suite: ERC-721 Nova-Seeds, expiring validator risk oracle,
MARK curve AMM, plan-bound Sovereign treasury, ENS/stake-gated auctions, reserved reviewer capacity,
artifact-bound validation, exact $AGIALPHA payout burns, failure recovery and successor lineage.
Add a native-agent/local-EVM acceptance run, public transaction desk and continuous validation.
All existing contracts, papers, demos and capabilities remain. See [the protocol guide](docs/agent/ASCENSION_PROTOCOL.md).

[See docs/DISCLAIMER_SNIPPET.md](docs/DISCLAIMER_SNIPPET.md)

## Breaking Changes Policy
Incompatible updates are announced in advance whenever possible and remain deprecated for at least one minor release. Each release includes a dedicated `### Breaking Changes` section describing removed features or behavioural differences. Consult that section when upgrading.

The initial release is tagged `v0.1.0-alpha`.

For the full changelog, see [docs/CHANGELOG.md](docs/CHANGELOG.md).

### Migration Note
Production modules previously under `src/` now reside in
`alpha_factory_v1.core`.
Update imports accordingly.

## [Unreleased]
- Upgraded `rdkit` to version `2023.9.5` for Python 3.12 support.
- Adopted 18-decimal AGIALPHA token (`0xa61a3b3a130a9c20768eebf97e21515a6046a1fa`) and removed multi-token support along with `setToken` functions. Existing deployments should scale token amounts by `1e12` when migrating from the previous 6-decimal token.

## [0.1.0-alpha] - 2024-05-01
- Initial alpha release.
- Git tag `v0.1.0-alpha`.
- This tag points at commit `0ff79a4f`.
 - If cloning from a snapshot without tags, recreate it using:
    ```bash
    # Verify the release tag
    git tag -l v0.1.0-alpha
    # Recreate the tag when missing
    ./scripts/create_release_tag.sh HEAD
    git push origin v0.1.0-alpha
    ```
 - The package exposes `alpha_factory_v1.__version__ = "0.1.0-alpha"` at this release.
