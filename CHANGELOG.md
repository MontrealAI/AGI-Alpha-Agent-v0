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
