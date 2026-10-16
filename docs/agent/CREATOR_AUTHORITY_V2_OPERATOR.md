# Alpha v2 operator workflow candidate

This is a reviewable operator implementation, not a production-qualified deployment approval.
No real transaction was signed or relayed while implementing it. Its tests use disposable
unforked Osaka fixtures and mock dependencies. The current 6c8 delegate/wallet, real-dependency
fork, external authority inventory, economics and explorer acceptance are not qualified.
The previously blocked independent review has not been performed or substituted by these tests.

## What this workflow supports

Exactly five direct type-2 CREATE transactions, followed by two direct governor type-2 CALLs.
The creator and chosen governor must differ. Access, Oracle and Market receive the governor as
constructor owner immediately; ownership is transferable Ownable2Step storage, not immutable.
NovaSeed and MARK have no administrator in this source. Constructor dependency immutables and
the two governor-only one-time bindings are different mechanisms.

The supported creator profiles remain empty-code EOA and separately qualified delegated EOA
with exact EIP7702 marker/target/code/state checks. No factory, CREATE2, contract wallet, relayer,
batch, self-call or type4 creation path is accepted. The governor must have empty code. A wallet
must return an exact serialized signed type-2 transaction without wrapping or changing it.
A wallet that only auto-broadcasts is not supported by the signed-byte verification path.
There is no bundled hardware-wallet adapter, and a signature does not prove Ledger custody.

The original v1 commands, historical governor policy and recorded deployment verifier remain
unchanged. New actions cannot target archived deployment addresses. Do not migrate or modify
old deployments through this workflow.

## Before running any operational command

Use the exact clean reviewed candidate checkout and source-matching locked artifacts. Every CLI
obtains commit/tree/lock through reviewedRevision(); there is no plan-trust override. Keep all
operator JSON, journals, packets, raw files and output directories outside that checkout.
Mutable output, package, journal/head/command-lock and shared actor-lock paths are enforced
outside the checkout, including ignored directories and symlink aliases. Path validation occurs
before an operational command creates evidence or acquires locks; no trust-the-path override exists.
The /tmp development tree is deliberately not a clean Git checkout and is not a deployment
workspace. Its tests inject a separately verified source anchor; the operational CLI does not.

Use the existing qualified Node 22 runtime and locked dependencies. Do not install a different
compiler or silently rebuild artifacts with different settings. Obtain separately approved
configuration, economics, sender/delegate/wallet evidence and a fresh canonical block/nonce
allocation coordinated with Jobs and Manager. A hash naming a report does not certify its quality.
Old observed nonce values are not reservations or permission to deploy.

Select one existing absolute real directory as DEPLOYMENT_LOCK_DIRECTORY for all repositories.
The session acquires creator AND governor locks, sorted/deduplicated in the common namespace
`1-<lowercase actual sender>`, with creator-nonce-lock-v1 owner records. It holds both until
successful finalized completion. This protects cooperative executors sharing that filesystem,
including different creators sharing one governor. Explicitly prohibit other machines, wallets
and out-of-band signing; a local lock cannot stop them or delegate-induced CREATE nonce changes.

Read-only commands use ALPHA_READ_ONLY_RPC_URL (HTTPS, no embedded credentials/redirects).
The bounded adapter only allows reviewed address reads, exact transaction hashes and bounded
five-address graph logs; it cannot sign or send. Its total budgets are 2,000 requests, 100 MiB,
5 minutes, 20 seconds/request, 2 MiB/response, and 100,000 blocks/10,000 logs with 1,000-block
chunks. These maxima can only be lowered by programmatic callers. Failure stops the adapter.
Provider observations and finalized tags are trusted read evidence, not independent consensus
proof. Hashless recovery is further limited to 512 blocks and never retries on budget exhaustion.

## Plan, preflight and source package

From tests/contracts in the clean reviewed checkout:

1. `npm run mainnet:authority-plan -- CONFIG_AND_JOURNAL.json NEW_PLAN.json`
   The input has exactly config and journal. See CREATOR_AUTHORITY_V2_CANDIDATE.md for the strict
   v2 schema and qualifications. The package's deliberately invalid example must be completed
   from fresh approved evidence; never substitute a historical plan or configuration.
2. Create PROGRESS.json with exactly creationHashes, governanceHashes and journal. Initially
   both hash arrays are empty; journal is the current coordinated allocation snapshot.
   `npm run mainnet:authority-preflight -- PLAN.json PROGRESS.json NEW_PREFLIGHT.json`
3. Optional predicted source package:
   `npm run mainnet:authority-package -- plan PLAN.json NEW_DIRECTORY`
   This accurately labels all addresses predicted, not deployed or explorer-verified.

No command overwrites output. Existing real parent directories are required. Every output is a
new local artifact; a failed file write can leave partial evidence and must be investigated.

## Seven-operation session

Command input files use explicit local paths. The session command is:

`npm run mainnet:authority-session -- ACTION COMMAND.json NEW_OUTPUT.json`

All actions independently bind the clean source revision and reconstruct the plan. No action
imports a private key, mnemonic, wallet connection or remote signing account. The code never
calls eth_sign, personal_sign or eth_sendTransaction.

1. `start`: COMMAND has exactly `{ "plan": "PLAN.json", "journal": "NEW_SESSION.jsonl",
   "mode": "raw-relay" }`. Choose external-broadcast instead if the operator will broadcast
   validated bytes separately. Modes cannot change during a session. Start obtains both actor
   locks and fresh preflight before creating the fsynced append-only journal.
2. `prepare`: COMMAND has exactly plan, journal and governorEnvelope. Use governorEnvelope:null
   for the first five CREATEs. For the last two operations supply a path to a separately reviewed
   JSON envelope with exactly nonce, gasLimit, maxFeePerGas, maxPriorityFeePerGas and accessList.
   All fee/gas values are decimal strings; accessList must be []; nonce is an integer matching
   fresh latest=pending governor nonce. This is not a creator nonce allocation.
   Prepare verifies phase state, sender nonce and maximum-gas affordability. The operator handles
   balances; the tool never tops up. It fsyncs handed-off state BEFORE exporting the packet.
   NEW_OUTPUT.packet contains the exact envelope and unsignedSerialized bytes for the signer.
   An output failure leaves a handed-off intent, not permission to prepare a second transaction.
   To recover the original packet, `handoff` takes exactly plan and journal and returns that
   persisted deployment ID/index/intent hash/envelope/unsigned serialization without changing
   the journal or calling a provider. It cannot revise fees or create another intent. Original
   handoff uncertainty remains; retrieval is not evidence that signing or broadcast did not occur.
   Retrieval does not check current chain state or actor-lock ownership and is not fresh signing
   or nonce authorization. Fresh preflight and the import/relay gates still apply.
3. The human signs that exact packet in a separately authorized, qualified wallet. Retain the
   serialized signed hex in an ordinary local RAW.txt file. Do not include keys or credentials.
   The tool does not perform this step. Signed bytes are executable transaction capabilities;
   protect them locally and do not paste them into public logs or review bundles.
4. `import`: COMMAND has exactly plan, journal and signedRawFile. The coordinator parses raw
   serialization, recovers the signer and checks every field against the persisted intent,
   including type/chain/from/nonce/null-to or new-graph target/input/value/gas/fees/accessList.
   It rejects noncanonical serialization, another signer, type4/auth/blob fields or substitutions.
   After the human signing delay it also rechecks the current phase, source/delegation/governor,
   actual-sender nonce, block/gas and affordability while holding both locks. Then it persists
   the known transaction hash and raw-byte hash, never the raw bytes or private key. Treat this
   as transient evidence and broadcast promptly; if any delay or state uncertainty arises, run
   a fresh read-only preflight before external broadcast. No local check can prevent a later
   out-of-band state change.
   If the import result file fails after the signature hash was journaled, do not import again.
   `status` takes exactly plan and journal and recovers the durable signed state and exact
   relayAcknowledgement to a fresh output path. It does not sign, broadcast or revise the intent.
5. For raw-relay mode, obtain `relayAcknowledgement` from a `status` command (plan and journal).
   The acknowledgement binds the exact plan, deployment ID, index, intent and signed hash.
   A `relay` COMMAND has exactly plan, journal, signedRawFile and acknowledgement. The user must
   also set ALPHA_ENABLE_USER_RUN_RAW_RELAY=I_REVIEWED_THIS_EXACT_TRANSACTION and explicitly
   supply ALPHA_RAW_RELAY_RPC_URL. This guarded command rechecks live state and the raw envelope,
   fsyncs submission-attempted BEFORE its one eth_sendRawTransaction call, and never retries.
   These flags are deliberate operator acknowledgements, not on-chain consent or proof of review.
   Do not invoke this command on a real chain without separate transaction authorization.
   In external-broadcast mode the relay command is forbidden. The operator broadcasts the exact
   validated bytes externally; handed-off uncertainty and both locks remain throughout.
6. `recover` has exactly plan, journal and transactionHash (null if unknown). It is read-only.
   Known hashes are inspected directly; otherwise bounded canonical blocks are scanned by exact
   sender+nonce. Signature, complete envelope, successful receipt, block, derived address and
   exact runtime/source are checked. Missing/pending/failed/conflicting/reorg/pruned evidence
   stays unresolved. Absence is never proof of no submission. No resend, replacement, fee bump,
   nonce reuse or skipped creation is available.
7. `reconcile` takes those same fields and performs the recovery again under the session command
   lock. Only a successful finalized receipt plus the expected current graph phase advances the
   journal. Repeat prepare/import/(relay or external broadcast)/reconcile for all seven operations.
   The exact order is Access, NovaSeed, Oracle, Market, MARK, Oracle.bindMarketplace(new Market),
   Market.bindMark(new MARK). Prefix checks model each creation and 0/1/2 completed bindings.
8. `finish` takes exactly plan and journal. It requires seven finalized receipts, reruns the full
   fresh authority verifier, fsyncs the complete authority evidence inside the journal, then releases
   only its own actor locks. If command-output creation or a release fails, retry only `finish` with
   a fresh output path. It re-verifies the original finalized acceptance block and exact saved
   evidence, accepts already-absent locks, and releases remaining matching-owner locks. A replacement
   owner or incomplete lock always blocks cleanup. No admission, funding or activation action is
   performed. Status/evidence retain activationAllowed:false.

Read-only recover does not require removing an actor lock or command lock. Normal mutation
commands take an exclusive `<journal>.command-lock`; another process or crash leaves them blocked.
No TTL, PID check or automatic stale-lock deletion exists. A process crash leaving its command gate,
torn write, missing complete journal row, incomplete lock (for example loss between owner-file removal and directory removal),
failed CREATE, unresolvable nonce conflict or missing historical provider data requires explicit
manual reconciliation. Preserve all files. Establish that no earlier executor can still run, resolve
all handed-off/signed intents and canonical effects, and obtain a deliberate recovery decision
before any lock ownership transfer or journal repair. This release does not provide an automatic
crash-lock takeover or unsafe "force resume" command. Such exceptional cases are stop conditions,
not claims that the campaign can always recover or continue.

Each fsynced journal append is followed by an atomically published, separately fsynced
`<journal>.head.json` checkpoint. Missing heads, journal-ahead/head-ahead, and interrupted head
publication all stop; no checkpoint mismatch is automatically repaired. Preserve pending head
files as evidence. The local filesystem is trusted for cooperative execution. Journal hash chains
and head checkpoints detect accidental corruption/loss; they do not authenticate against an attacker able to rewrite the whole journal or run
arbitrary local code. On-chain receipt/source checks remain mandatory before advancing.

## Final receipt verification and explorer evidence

RECEIPTS.json has exactly creationHashes (five), governanceHashes (two), and acceptanceBlock
with number/hash of a finalized block. Always use the actual new graph's receipts.

- `npm run mainnet:authority-verify -- PLAN.json RECEIPTS.json NEW_AUTHORITY_REPORT.json`
- `npm run mainnet:authority-package -- receipts PLAN.json RECEIPTS.json NEW_DIRECTORY`

Receipt-proven export repeats the authority verification using the bounded read-only transport;
it does not trust a saved success label. It includes exact Standard JSON/compiler/constructors,
creation receipts and source/plan/report checksums, with truthful receipt-proven address labels.
Submit the source package to the explorer only through a separately authorized operator workflow.
Credentials are not placed in exported files. Retain final accepted explorer verification; a
submission GUID is pending. The scripts never upload or submit explorer requests themselves.

The exact fresh graph must contain only the three direct zero-to-governor ownership events and
two bindings, with zero creator admission/roles/approvals/stake/business state. Any unexpected
activity stops acceptance. This is not a migration verifier for a previously used deployment.
Governor ownership can later transfer; dependencies and one-time graph bindings cannot be treated
as the same authority mechanism. Token/proxy/ENS/external controllers and off-chain roles remain
separate inventory requirements. Successful functional/receipt checks alone never authorize
funding, participant commissioning or activation.
