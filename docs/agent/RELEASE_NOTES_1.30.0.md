# 1.30.0 — MARK Mainnet wallet with recoverable transaction state

This release adds a wallet workspace alongside the preserved Protocol Desk. It connects an injected
wallet, checks the archived deployment, prepares and simulates an allowlisted action, opens the user's
wallet only after explicit confirmation, and verifies the resulting transaction and finalized receipt.

- [MARK Mainnet wallet](../ascension-protocol/mainnet/index.html): account/network selection, exact
  $AGIALPHA amounts, bytecode/binding checks and English/French guidance.
- Eligible recovery and existing obligations can use real wallet-managed transactions. New funding,
  seeds, campaigns, deposits and new work commitments remain blocked for the archived deployment.
- An exact nonce and bounded gas limit are included in the preview. The public intent is saved locally
  before handing it to the wallet. Storage failures stop signing; same-browser tabs share an exclusive lock.
- Unknown submissions survive reload. Export/import and hash reconciliation recover original or replacement
  transactions. Unfinalized and reorganized receipts keep the barrier active. Cancellation or a different
  replacement never appears as successful execution of the original action.
- The wallet loads from the network and is excluded from the shared offline cache, preserving cold-checkout
  installation and offline SUCCESSOR workflows.
- The generated Protocol Desk retains the wallet link. Existing contracts, recorded deployment artifacts,
  economic rules, flowcharts and local-EVM evidence remain unchanged.
- Targeted wallet tests and rendered browser journeys now gate the integrated release. Packaged and public
  acceptance bind the exact commit, release version and wallet assets; all previous release gates remain.

Read the [wallet operating guide](MARK_WALLET.md) before signing. Browser acceptance uses synthetic
injected-provider responses with archived bytecode. It is not a physical hardware-wallet trial, independent
security audit or observed Mainnet settlement. No real transaction was required for release testing.
Physical wallet/device compatibility and operational commissioning remain separately unverified.

The [deployment record](MAINNET_DEPLOYMENT.md) explains the immutable October 11 settlement differences.
Publishing this interface does not upgrade that deployment or authorize new public funding. The existing
contract development lock retains its previously reported low-severity dependency findings; this release
makes no zero-warning or flawless-contract claim.

The release manifest and validation archive identify the accepted source, workflow evidence and checksums.
The recovery journal covers this origin/browser profile; separate wallets and devices require coordination.
Browser data can be cleared or edited, so keep an exported backup. Imported records never authorize signing.

Begin with [START_HERE.md](START_HERE.md) for the preserved installation and operator workflows.
