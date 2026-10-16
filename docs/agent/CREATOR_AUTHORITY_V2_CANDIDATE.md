# Candidate direct-CREATE sender profiles and authority evidence

Status: local functional implementation, not deployment approval. No released file, historical
manifest, Solidity source, dependency lock, v1 planner or historical verifier is changed by this
candidate. The released source anchor is `bd1728f067e3fd1e94d81a19142733d308de1e43`
(v1.33.0), tree `19e498dd8d082a397555ed2006269512422444fb`. Applying this tooling patch
requires a new reviewed source revision; do not attribute a modified checkout to that release.

The newly selected governor is `0xd76AD27a1Bcf8652e7e46BE603FA742FD1c10A99`.
A v2 configuration must repeat the exact checksummed selected governor in
`governor.addressAcknowledgement`. This is explicit configuration binding, not hardware-custody
attestation. The v1 historical a9eD acknowledgement policy and October 11 archive retain their
original meanings. No existing ownership transfer, balance action, new economic parameters,
funding, admission, signature or broadcast is authorized by this document.

## Scope

New files:

- `scripts/mainnet-authority.js`: exact v2 validation/planning, read-only preflight and evidence APIs.
- `authority-test/mainnet-authority.test.js`: offline functional and protocol-path tests.
- `hardhat.authority.config.js`: explicit Osaka, in-process, unforked execution harness. It loads
  the original fixture guard; it does not relax that guard or configure an external network.

The original `plan` CLI remains unsigned. New `authority-cli.js` exposes bounded read-only
preflight/verify commands through `authority-rpc.js`; `authority-verification-package.js` exports
predicted or freshly receipt-proven v2 source packages without explorer submission. All operational
commands independently observe the actual clean checkout before trusting a source label.
The original v1 transport and commands remain unchanged.

`authority-session.js` adds the separately user-run seven-operation coordinator: both actor locks,
durable handoff/signature/attempt/receipt states, exact serialized type-2 checks, read-only recovery,
and an explicitly armed one-shot raw relay. It never signs or connects a wallet. The generic
read-only signing boundary remains `executorIntegrated:false`: that report does not establish
that its caller holds an execution session or any production qualification. Actual session
commands separately acquire/verify both locks and recheck the plan. Read-only plan/preflight
outputs keep `readyToBroadcast:false`; authority evidence keeps `activationAllowed:false` and
`readyForPublicFunding:false`. See [the operator workflow](CREATOR_AUTHORITY_V2_OPERATOR.md)
for exact command inputs, supported handoff paths, stop conditions and remaining qualifications.

## Existing deployments are protected

No migration, old ownership/configuration/approval change or old fund movement is generated.
The planner reads the integrity-checked historical manifest and rejects any CREATE-derived
address in that existing graph, including the historical creator/starting-nonce combination.
Both governance destinations and their binding arguments are rebuilt exclusively from the five
new derived addresses. Edited old targets/arguments/calldata or additional old actions fail even
with a recomputed plan checksum. Preflight rejects code or a nonzero nonce at every remaining
predicted address, protecting other existing deployments too. Acceptance requires the exact
new creation receipts and runtimes before the two governor bindings qualify. Historical
verification remains read-only context; none of its semantics or records are rewritten.

## Explicit sender modes

`empty-eoa-direct-create.v1` requires exactly empty account code at the reviewed finalized pin
and the coherent latest-block read. Any delegated code or contract code fails that profile.

`delegated-eoa-direct-create.v1` is a separate opt-in profile. It requires:

- The complete 23-byte `0xef0100` delegation indicator and its exact nonzero, non-self target.
- A reviewed target runtime hash, plus explicit call-data/result-hash checks for relevant account,
  module, proxy implementation and authority state. The reviewer must determine completeness;
  a code hash and a harmless getter alone do not establish a safe delegate.
- SHA-256 identifiers for separate consensus, real-dependency fork and delegate-review evidence.
  These identify evidence; the validator does not certify its content or establish custody. No
  such production qualification bundle for the observed 6c8 sender has been produced here.
- The same checks at the pin and current coherent latest block. Any marker, code, getter, root,
  dependency, governor, nonce, pending or expected-address drift stops the sequence.

The historical creator `0x6c8B8897Fb6b08B4070387233B89b3E9A94eD00E` has no trusted-address
exception. Any supported, explicitly configured separate creator uses the same rules.
Creator=governor is rejected because retained governorship conflicts with zero creator privilege.
Contract-wallet, factory, relayer, EntryPoint, self-call, batch, CREATE2 and type-4 creation paths
remain unsupported. Do not treat a delegated account as an empty EOA or strip its code check.

## Protocol basis and qualification limit

[EIP-7702](https://eips.ethereum.org/EIPS/eip-7702) permits origination by an account carrying a
valid delegation indicator. Its type-4 set-code envelope has a non-null destination; delegation
is followed when execution is addressed to that account. The candidate therefore models the
separate [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559) type-2, null-destination creation
path. These rules do not establish that a wallet UI, delegated self-call or batching transport
will preserve that path. [EIP-684](https://eips.ethereum.org/EIPS/eip-684) requires collision
failure for existing code or nonce; preflight checks both at every remaining predicted address.

The target block 26205019 timestamp 1792152791 follows mainnet Osaka and BPO2. The candidate
harness now explicitly selects Osaka and rejects transaction gas limits above 16,777,216 under
[EIP-7825](https://eips.ethereum.org/EIPS/eip-7825). It also tests actual engine rejection above
that cap and permits the exact cap. The normal 30,000,000 block limit avoids Hardhat's special
solidity-coverage gas-cap override. Earlier Prague evidence is preserved as a weaker historical
functional run, not relabeled as current-mainnet qualification.

Installed Hardhat 2.29.1 / EDR 0.12.0-next.23 exposes Osaka, but not Amsterdam. The official
[Geth mainnet schedule](https://raw.githubusercontent.com/ethereum/go-ethereum/master/params/chainspecs/mainnet.json)
and [Fusaka specification](https://eips.ethereum.org/EIPS/eip-7607) place Osaka and BPO2 before
the pin; the [Glamsterdam notice](https://blog.ethereum.org/2026/09/17/glamsterdam-testnet-announcement)
still lists mainnet activation as undecided. This is a schedule-based inference to recheck before
any approved fork, not fresh provider consensus evidence. BPO blob schedule/fees, PeerDAS,
beacon consensus/finality and full block-validation conformance are unqualified by these tests.
Only non-blob type2 creation is modeled; the local type4 fixture installs disposable delegation.

The offline test uses a newly generated disposable local creator key, a genuinely signed local
7702 authorization and type-4 transaction to install delegation, then actually serializes and
executes five type-2 creation transactions. It reconstructs public transaction signatures and
hashes. An actual call to the local delegate performs CREATE and increments the delegated
account's nonce; the next preflight rejects that race. This demonstrates the selected local
engine path. It does not prove the actual 6c8 wallet transport, target safety, exclusive custody,
mainnet-fork behavior or mainnet consensus finality. Test chain ID 1 exists only in the verified
in-process unforked engine; no HTTP node is used. Test finality is deliberately latest-as-finalized.
Token, ENS and wrapper are local mocks. Unsupported consensus features remain explicit gates.

## Exact plan and envelope

The v2 checksum binds configuration, source commit/tree/lock, complete compiler input and source
closure, bytecode, ABI, immutable references/getter mapping, constructor arguments, governance
calls, sender profile, evidence identifiers, nonce allocation snapshot and fee/gas limits.
`checkPlan` reconstructs the whole plan from the current exact compiled sources, rather than
accepting a recomputed checksum on edited bytecode or constructor data. Operational callers must
pass the actual independently observed clean reviewed revision; the CLI obtains it with
`reviewedRevision()`. This is a required argument, never defaulted to the plan's own label:
`checkPlan(plan, compiled, observedRevision)`,
`preflight(plan, rpc, observedRevision, creationHashes, currentJournal)` and
`verifyAuthority(plan, rpc, evidence, observedRevision)`. The preflight API additionally accepts
a sixth governanceHashes argument for the exact 0/1/2 completed binding prefix. Missing or mismatched anchors fail
before the first provider read. The returned evidence records `observedRevision`. Programmatic
callers own this trust boundary: copying `plan.revision` into that argument is not independent
verification. Offline tests inject the separately verified baseline anchor and reuse exact
source-bound artifacts; they do not claim that the disposable /tmp tree is a clean Git checkout.
A recalculated checksum on an edited commit/tree/lock is only self-consistency, not source proof.

Every CREATE envelope has exactly:

`type`, `chainId`, `from`, `nonce`, `to`, `value`, `data`, `gasLimit`, `maxFeePerGas`,
`maxPriorityFeePerGas`, `accessList`.

The only supported values are type 2, chain 1, selected creator, consecutive reviewed nonce,
`to:null` (not zero address), value `"0"`, exact initcode including ABI-encoded constructors,
reviewed gas/fee bounds and an explicitly empty access list. Missing or additional fields,
authorization lists, destination substitutions and calldata wrapping fail. The operator must
review these exact unsigned values. Private keys never belong in inputs. The separate user-run
session may import externally signed serialized bytes only after the human has authorized and
performed signing; no real signing or relay was performed during this implementation.

The governor's two calls are `Oracle.bindMarketplace(Market)` and `Market.bindMark(MARK)`,
zero-value direct CALLs. The creator never owns Access, Oracle or Market. Ownership is
constructor-set Ownable2Step storage and remains transferable by the governor. It is not an
immutable variable. Constructor graph dependencies are immutable; the two stored graph bindings
are only writable once by the governor. A wrong completed binding requires a replacement
unfunded graph, not an ownership renunciation or copied historical transfer/accept sequence.

## Shared creator coordination and resumability

A v2 plan requires an `ethereum.cross-project-nonce-journal.v1` allocation snapshot with the
selected chain/sender, canonical block, matching latest/pending starting nonce, all three projects
in scope (`alpha`, `jobs`, `manager`) and nonoverlapping nonce intervals. Exactly one Alpha
interval contains five consecutive CREATE nonces. It is planning evidence, not an on-chain
reservation, exclusive lease or substitute for the live executor's durable transaction journal.
Changing this snapshot requires plan reconciliation/rebuilding.

The agreed external executor boundary is shared with Jobs and Manager:

1. The operator selects the same existing `DEPLOYMENT_LOCK_DIRECTORY` for every repository.
2. Before nonce reads/signing, acquire atomic directory locks for every actual transaction sender,
   including creator and governor, named `${chainId}-${sender.toLowerCase()}`. Deduplicate and
   lexically sort those keys before acquiring any lock to avoid cross-project deadlocks. The `creator-nonce-lock-v1` owner record contains
   chainId, creator, absolute journalPath, an ownership token and lock path. Hold it for the whole
   Alpha creation and binding sequence. Never automatically break a stale lock. Different creators
   sharing a governor still share that governor lock. Each governor CALL requires a separately
   reviewed current nonce/fees and durable exact intent; a creator-only lock is insufficient.
3. Fsync each `creation-intent-v1` record before possible submission. Alpha's `creationIntents`
   exports the shared fields: chainId, creator, transactionMode `eoa-create`, nonce, `to:null`,
   value `"0"`, dataHash, startBlock, address (predicted CREATE address), and gasLimit. The
   accompanying signing-boundary record additionally binds the full type-2 envelope and sender
   policy hashes; `transactionMode` alone never qualifies delegated origination.
4. Recheck latest=pending nonce, delegation/state and exact envelope while holding the lock.
   Save transaction hash and canonical matching receipt durably after submission.
5. A saved intent with uncertain submission is unresolved even when no transaction is currently
   seen. Perform read-only sender+nonce recovery against the exact immutable intent. Do not
   retry a send, reuse the nonce, silently skip a failed creation or release a lock as "complete".
6. Reconcile Jobs and Manager project-local journals when rebuilding an Alpha plan. Their own
   staged files do not reserve future Alpha nonces, and separate directories are not coordinated.

This protects cooperative executors on the same shared filesystem only. The operator must
exclude simultaneous signing on other machines/wallets and out-of-band actions. Calls into a
delegated creator may independently consume nonces even while the lock is held. No local lock
prevents those races or proves exclusive control of a private key.

Read-only planning does not acquire a misleading nonce lock. The separate session coordinator
acquires both actor locks, journals exact intents before handing off packets and treats any
possible submission as unresolved until receipt/source recovery. Its one-shot relay must be
explicitly armed by the user; read-only plan/preflight/recover/verify/export paths cannot relay.
The available coordinator is not evidence that an arbitrary preflight caller holds the locks.
No result is production execution approval. Crash command locks/torn journals require deliberate
manual reconciliation; no automatic stale-lock takeover or force-resume path exists.

For a partial run, supply exactly the contiguous prefix of canonical successful creation hashes.
Each public signed transaction is reconstructed and checked for chain/type/from/nonce/input,
value, fees, gas, access list, receipt block/address and exact runtime/immutables. Already-created
contracts are rechecked; uncreated addresses must have no code and zero nonce. Unexpected nonce
consumption, replacement, missing receipt, reorg or modified runtime stops continuation. Historical
creation facts remain valid after the retired creator changes its own code or nonce: acceptance
does not impose a permanent empty-code restriction on that address.

## Fresh authority matrix and honest boundaries

Before acceptance, the verifier requires five canonical successful direct CREATE receipts and
two canonical governor-binding receipts, in order, through a finalized acceptance block. It checks
exact runtime including every immutable word, owner/pending owner, graph/economic getters,
root bindings and fresh seed/job counters. Creator admission, names/eligibility, stake, locks,
active jobs, capacity and reputation must be empty/zero.

The complete five-contract log interval must contain only the three direct zero-to-governor
ownership events and the two exact binding events. Any other admission, registration, operator
approval, NFT transfer, participant action or unknown event fails fresh commissioning. This
intentionally strict empty-graph acceptance rule is not a verifier for a used protocol. Events
and getters must be reconciled rather than deleting obligations or pretending a used graph is fresh.

No owner/admin exists in the exact NovaSeed or MARK source/ABI; zero fresh seed/job counters,
matched code and the complete event interval bound their business-state authority. Public
permissionless rights remain available. Later governor grants, NFT/operator approvals and
ownership transfers can change the authority matrix.

Unresolved activation gates remain explicit: real external token/proxy and ENS/controller
permissions, indirect creator control, off-chain custody/access, actual delegate/wallet and
real-dependency fork qualification, independent security review under its existing restrictions,
explorer acceptance, reviewed economics and operational/participant commissioning. The code
cannot establish literal zero influence forever. There is no automatic unpause or funding path.

## Offline commands and observed limits

Use existing pinned Node 22.17.1 and locked dependencies; do not install or update packages for
this candidate. Compile source as usual before a new clean checkout's tests. In this bounded
local exercise, existing exact-source artifacts were verified and reused read-only.

- `npm run test:authority`: candidate functional and protocol-path suite, no compilation or public-provider network (numeric-loopback mock HTTP is used for transport tests).
- `npm test -- --no-compile`: unchanged fixture regressions.
- `npm run mainnet:authority-plan -- CONFIG_AND_JOURNAL.json NEW_OUTPUT.json`: unsigned plan
  from an exact clean reviewed checkout. Input has only `config` and `journal` fields.

Tests cover address permutations and both modes, exact selected governor, unsupported envelopes,
source/constructor edits with recomputed checksums, drift and reorgs, collision checks, shared
intent compatibility, actual signed delegated origination, ownership-negative calls, one-time
bindings, receipt/runtime mismatch, interrupted prefixes, delegated nonce races and authority grants.
No test result replaces the separately blocked independent review or qualifies production signing.

The expanded suite also exercises the actual seven-operation coordinator for empty and delegated
creators, one-shot local relay versus external broadcast, missing/lost/pending/conflicting/reorg
receipts, hashless exact-nonce recovery, crash locks/torn journals, failed output after durable
handoff, a separate process sharing the governor, and receipt-proven v2 source export. Raw signing
uses disposable fixture keys only. No hardware wallet, production HTTPS relay or provider fork
was qualified. An SDK-independent external adapter remains necessary for a physical wallet.
