[Project notice](../DISCLAIMER_SNIPPET.md)

# Second Ascension deployment: October 16, 2026 preparation

Status: **NOT CLEARED FOR DEPLOYMENT OR FUNDING**. This is a preparation record for
Friday evening, October 16, America/Toronto (Montreal, UTC−04:00), and the weekend.
Source inspection baseline: `ee5401972ca53c1ef47d02179d566b4cd10f9197`.
Freeze a final reviewed commit/tree/lock and regenerate all evidence after any edit.
A source release does not deploy contracts. No transaction is authorized by this document.

## Owner-directed review policy

On October 15 the owner requested preparation without an external independent
review/audit and without a Sepolia deployment. Record these as **owner-accepted
omissions**, never passed checks, independent assurance or testnet rehearsal.
Rigorous AI-assisted review, adversarial local tests and a pinned, isolated
mainnet-fork rehearsal remain technical work. AI-assisted review is not an
external independent audit and cannot establish absence of vulnerabilities.
The earlier generic readiness guide's external-audit requirement is superseded
only for this campaign by this explicit omission record. None of the compiler,
source identity, governance, dependency, lifecycle or final verification checks
are waived. No Sepolia test was run or claimed for this preparation.

## Exact deployment scope and historical evidence

Deploy five new contracts: AscensionAccess, NovaSeed, AscensionRiskOracle,
AscensionJobMarket and AscensionMark. AscensionToken is an inherited helper;
canonical AGIALPHA is an existing external dependency, not a sixth new token.
Legacy `contracts/v2` is outside this deployment except imported Constants.
Do not substitute the separate AGI Jobs or USDC AGIJobManager stack.

The October 11 archive under `deployments/ethereum-mainnet/2026-10-11` records
five CREATEs, two bindings, two ownership proposals and two acceptances.
Preserve the entire archive, including exact source, Standard JSON, runtime,
transaction records and original toolchain. Run `mainnet:record-check` for
internal integrity; run `mainnet:record-verify` for fresh finalized chain evidence.
Archive integrity is not independent chain confirmation. Etherscan success is
operator-reported with no API transcript; independently recheck every explorer
page and preserve final responses for the new deployment.

Old profile: solc 0.8.24, OpenZeppelin 5.4.0, via IR, 200 optimizer runs, Paris.
Candidate profile: solc 0.8.37, OpenZeppelin 5.6.1, via IR, 200 runs, Cancun.
Current payout/burn balance checks and rejection-quorum revalidation are absent
from the old immutable deployment. Recompilation cannot patch the old addresses.
Review every changed transitive source and compiler setting, not just project
Solidity diffs. Require byte-identical fixture mirrors, zero link references,
compiler input/source hashes, creation/runtime bytes and immutable references.
A different whole-program compilation input can change metadata and bytecode;
use the unsigned plan's exact build for rehearsal and explorer verification.

## Open decisions and evidence gates

- The owner selected the same Ledger wallet on October 15:
  `0xa9eD0539c2fbc5C6BC15a2E168bd9BCd07c01201`. This is explicit single-signer
  governance; loss or compromise can strand or compromise administration.
  Ledger custody is owner-reported, not verifiable on-chain. The narrow opt-in
  governor object is `{ "kind": "ledger-eoa", "address":
  "0xa9eD0539c2fbc5C6BC15a2E168bd9BCd07c01201", "addressAcknowledgement":
  "0xa9eD0539c2fbc5C6BC15a2E168bd9BCd07c01201" }`. The acknowledgement must
  match exactly. Both pinned-block and latest code must be empty; delegated
  EOA code is rejected. No fallback from failed multisig checks is allowed.
  The original multisig schema/default remains available. Confirm the separate
  deployer and economic settings; wallet choice is not permission to transact.
- If using the multisig alternative, verify its implementation, modules, guard, fallback handler, owners and
  control. Runtime hash alone does not bind proxy implementation or authority.
- Fresh finalized mainnet block/hash, independent provider cross-check, token
  behavior/source/proxy authorities, ENS roots/expiry and namespace custody.
- Complete forced production/fixture compilation, full contract tests and
  current locked development-tool dependency advisory check. Explicitly label
  unavailable checks. Cached build or an old audit result is insufficient.
- Exact-candidate fork lifecycle and invariant evidence, with real AGIALPHA and
  ENS implementations, remains required. Previous deployment rehearsal does
  not cover different code, compiler or dependencies.
- Final clean commit/tree/lock, actual public configuration and unsigned plan,
  simulation, fresh nonce, fees and gas, operator signing review, receipts,
  finalized read-back and explorer verification remain outstanding.

## Isolated fork rehearsal specification

Keep existing `hardhat.config.js` and fixture mutation guards unchanged. They
intentionally reject forks/external endpoints. Use a separately reviewed harness
with only an in-process Hardhat provider; never connect a mutation-capable signer
to the source RPC. Its fork upstream must be read-only and pinned by block number
AND independently verified block hash. Confirm chain ID, fork metadata, instance
identity and absence of externally configured networks before local mutations.
No production keys, signed transactions, broadcast method or deployment on
Sepolia belongs in this harness. Impersonation is local simulation only and
cannot prove actual signer/controller consent. Do not install mock token/ENS
bytecode into the real-token fork. Never interpret a loopback URL alone as proof
that the target is disposable.

Bind rehearsal to the exact unsigned plan and compile inputs. Exercise full
seed sealing, review, funding/buy/sell, bloom, plan proof, job auction, award,
submission, approval/rejection, payout/burn, refund collection and reclamation.
Also test revoked/expired identities, changed ENS ownership, stale approvals,
validator capacity/locks, duplicate votes, missing quorum, deadlines, malformed
proofs, non-exact transfers/burns, insufficient balances and malicious callbacks.
Retain token balance/supply changes, stake >= locked, reserve/lots consistency,
terminal-state single payment/refund, committee-lock release and no excess claim
invariants. Real-token failures are deployment blockers, not reasons to swap in
a mock. Record fork limitations and all untested branches.

## Operator sequence and interrupted execution

Only after unresolved gates are satisfied, follow MAINNET_READINESS.md to create
the exact unsigned plan and read-only preflight. Review all five CREATE payloads,
chain ID 1, zero value, deployer, consecutive nonces, predicted addresses and
constructor arguments. Signing/broadcast and spending remain the operator's
separate action. Check each receipt/status and expected address before the next
CREATE. A failed/replaced CREATE consumes or changes nonce assumptions: stop,
reconcile journal and actual chain, and rebuild the unexecuted plan. Never
blindly rerun or skip to later predicted addresses.

After creation, the selected governor sends the two one-time binding calls as
CALL, never DELEGATECALL. Direct governor constructor ownership means no old
handover transactions should be copied from October 11. If a bind fails, read
actual state before retrying; an incorrect irreversible binding needs a fresh
unfunded deployment. Preserve all receipts and finality. Run `mainnet:verify`
from the same clean reviewed build before admissions or funding, export exact
Standard JSON/constructor files and confirm explorer acceptance. Keep live-use
approval separate from deployment success and source-verification success.

## Old obligations, incident response and transition

There is NO global pause, upgrade proxy or arbitrary treasury rescue. Admission
revocation gates some new activity but is not an emergency stop: existing
settlement, timeout and withdrawal paths can continue. Token-level pause or
blacklisting can also prevent exits; this stack does not control that authority.
Do not label incident response as pausing the protocol.

Before routing anyone to new addresses, inventory the old deployment at a pinned
finalized block: owners and pending owners, seed/campaign/job counters, each
campaign phase/reserve/supply and lot holder, open auctions and bids, assigned or
submitted jobs/deadlines, escrow/refunds, staked/locked balances, validator
capacity, unclaimed terminal refunds and allowances to old contracts. Derive
participants from complete events and reconcile getters and token balances;
missing history is an unresolved obligation, not a zero balance.

Keep old address/chain labels and claim instructions available. Preserve seed
lineage and evidence; new IDs/addresses do not automatically represent old NFTs
or claims. Let authorized participants settle, timeout, collect, withdraw and
reclaim under the old contracts' rules. Do not move tokens, revoke allowances,
reassign claims or promise automatic migration. Any exception needs a separately
reviewed and expressly authorized plan. Monitor old and new deadlines/exposure,
ENS expiry, token upgrades, owner changes and unexpected balance movements.
Define initial exposure limits and who can revoke admission, communicate an
incident and reconcile claims before approving first public funding.

## Fresh historical-instance verification — October 15

The existing read-only verifier executed against a public HTTPS RPC at
`2026-10-15T20:08:37.316Z`, finalized block **26,200,139**,
`0x5ba89450466ec7979fd0ab037d86077799089630aab9d8923cf63753a7cb11be`.
The [complete new report](../../deployments/ethereum-mainnet/2026-10-15/record-verification.json)
confirms the original deployment transactions, exact original-profile runtimes,
bindings and completed governor ownership. It records `externalTransactions: false`
and `readyForPublicFunding: false`. It uses the original archived compiler profile;
it does not qualify the new compiler, hardening, candidate or participants. No
independent second-provider cross-check is claimed.

The complete local contract suite passed **111 tests** on the preparation source
`b07798b571286a9ce4d7104a69e8cd4b30d8d40f`, using its locked JavaScript tools and a
Python environment with the required chain extra. New source or configuration
still requires exact-candidate qualification. The signing window is Friday evening,
**October 16, 2026, America/Toronto (Montreal, UTC−04:00)**, continuing over the weekend;
the owner controls the exact signing time.

| Omitted check | Campaign status |
| --- | --- |
| External independent audit | NOT PERFORMED — OWNER-ACCEPTED OMISSION |
| Sepolia rehearsal | NOT PERFORMED — OWNER-ACCEPTED OMISSION |
