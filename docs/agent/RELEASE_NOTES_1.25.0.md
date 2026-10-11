[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.25.0 — A welcoming first experience

New visitors can now [start with a guided first plan](../start/index.html), prominently linked from the
homepage, repository and documentation. The dedicated English/French page offers large controls,
adjustable text, a three-step Choose → Review → Keep journey, field-specific errors and a useful download.
It requires no account, wallet, payment, installation, model download or AI service key.

The four-task planner reuses the tested allocation engine. It compares all 16 combinations against the
user’s time limit and importance points. Results show selected and omitted tasks, used time and time left.
Export requires an explicit review; changing inputs clears the prior result and review. Task names are
rendered as text, never HTML. Text and JSON downloads carry the inputs, outcome and review limitations.
The page sends no task data to a server and creates no persistent task storage.

Read the [getting-started guide](ONBOARDING.md) or continue to [Decision Studio](../studio/index.html),
[SUCCESSOR Ω](../successor/index.html), or the [installation guide](START_HERE.md).
The source template generates the entry point during full and minimal builds. Release acceptance covers
homepage discovery, English/French completion, keyboard use, validation, review invalidation, downloads,
small screens, larger text, no-JavaScript guidance and automated accessibility checks. The same journey
must pass on public HTTPS before publication. Existing release gates remain required.

## Deployment, contracts and recovery

The supported [Hardhat deployment path](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/tests/contracts/README.md)
remains a verified disposable local rehearsal. No Solidity ABI, token, balance, identity, journal format
or contract binding changes in this release. Native installation is separate from contract deployment;
no migration or funded network transaction is performed by the onboarding page.

Use all native installer, wheel, lock, packs and checksums from the same release. Follow
[operations](OPERATIONS.md) for checkpoint-aware backup, installation into a new environment and recovery.
Browser users should download unfinished work before refreshing. Existing workspaces and historical
flowcharts remain available. The native runtime remains scoped to private single-operator use.

The static entry point reduces server work; this release does not establish billion-user capacity,
comprehensive accessibility certification, independent AGI qualification or production-chain readiness.
The release manifest and validation archive identify the exact accepted commit and checks.
