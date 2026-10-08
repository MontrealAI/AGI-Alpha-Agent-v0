[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.24.1 — Keep SUCCESSOR visible after gallery generation

The gallery build regenerated the homepage from a template that omitted the new SUCCESSOR entry
points. The mission workspace worked at its direct address, but the generated homepage did not expose
it. This patch adds the navigation link and a dedicated introduction to the source template, so local
builds, release packs and GitHub Pages retain them. Existing Ascension links and workspaces remain.

Start from the [homepage](../index.html), open [SUCCESSOR Ω](../successor/index.html), or follow the
[English/French field guide](SUCCESSOR.md). New operators can [start here](START_HERE.md).
The browser needs no account, wallet, API key or model
download. It runs bounded local computation; independent qualification and production authority
remain absent.

## Validation and publication

Generated-homepage regression checks cover SUCCESSOR navigation, its introduction and the existing
Ascension entry point. Public browser acceptance checks the actual deployed entry point before
publication. All existing Python, platform, Docker, contract, browser, preservation and package gates
remain required on the exact integrated commit. The release manifest and validation archive record
the accepted revision and results; passing tests alone does not mean publication has completed.

This patch includes the [1.24.0 implementation and operator improvements](RELEASE_NOTES_1.24.0.md).
It does not replace the v1.24.0 tag or change its recorded evidence.

## Upgrade and recovery

Use all installer, wheel, lock, packs and checksums from the same release. Follow the
[installation and upgrade guide](OPERATIONS.md) and
[checkpoint-aware recovery procedure](SUCCESSOR_OPERATIONS.md#private-disaster-recovery-same-identity-and-keys).
No journal, protocol or contract migration is required by this homepage patch. Preserve backups,
independently retained checkpoints and later revocations when recovering or rolling back.

Reload the website online to receive the updated homepage and content-versioned cache. Keep exported
evidence before clearing browser storage. The supported Hardhat path remains a disposable local
rehearsal; this release performs no external-chain deployment or token migration.
