# Marker-bearing EOA: narrow direct-origination candidate

This additive offline candidate preserves `empty-eoa-direct-create.v1`, the older strict `delegated-eoa-direct-create.v1`, all five production contracts and historical deployment verification. The older strict profile still requires its original delegate-state calls and three evidence references. The new explicitly selected `marker-eoa-direct-create.v1` uses ordinary type2 null-destination CREATE and does not invoke the creator's delegation as an execution mechanism. It does not remove or change an existing marker.

The five contracts are permissionlessly deployable, with no creator allowlist or Ledger-brand requirement. Creator and governor are distinct explicit inputs. The three Ownable contracts assign transferable ownership directly to the selected governor in their constructors; dependency immutables and two governor-only one-time graph bindings have different semantics. No new action targets an old deployment. Unsupported factory, self-call, batch, type4 authorization, relayed user operation, CREATE2 and contract-wallet execution must receive a separately modeled workflow rather than a silent fallback.

## Exact profile and observation scope

The new sender object has exactly these keys:

- `mode`: `marker-eoa-direct-create.v1`.
- `delegationCode`: exact lowercase 23-byte EIP7702 indicator, `0xef0100` followed by its 20-byte target.
- `target`: exact target address, nonzero and distinct from the creator. The target must have nonempty code when observed. The target/creator cannot alias dependencies invoked during preflight or the new five-contract graph.
- `targetCodeHash`: exact 32-byte runtime keccak256. This is a drift observation, not a safety or exclusive-control conclusion.
- `storageChecks`: zero to 32 explicit `{address,slot,value}` observations, with address limited to creator/target and exact lowercase 32-byte slots/values. No duplicate slots, guessed storage layout or broad probing is performed. An empty list asserts no reviewed storage dependency; it does not prove there is no external controller.
- `qualification`: exactly `consensusEvidenceSha256` and `directExecutionEvidenceSha256`, each the SHA256 of its canonical report object.

Every pre-sign/pre-import/pre-relay gate retains independent clean-source/build/input revalidation, exact chain/canonical pin, code/marker/target drift, selected storage, fresh latest/pending nonce, budget and receipt-prefix checks. The transport only permits declared storage slots. It rejects `eth_call` to creator or marker target before any HTTP request. Dependency/new-graph getters retain their exact bounded read scope. Verification of completed historical creation facts retains the existing distinction from current retired-creator state.

This profile does not require invoking arbitrary delegate getters or proving the wallet uncompromised. Out-of-band authority may still consume nonce/balance or interfere. A code hash or known address does not establish custody, exclusive signing control or absence of other activity.

## Source-derived review request and accepted reports

The plan CLI gains `qualification-scope` alongside `plan`. Both commands independently observe the actual complete clean checkout; output must be outside it. With the new marker profile only, a scope request requires explicit `qualification: null` and an input object containing `config` and the coordinated cross-project `journal`. It returns a source-derived review request with `readyToSign:false` and `readyToBroadcast:false`. It cannot be used as a signing plan.

After the trusted operator independently accepts the actual reports and artifacts, populate the two report digests and pass `config`, `journal` and `directOriginationEvidence` to the existing `plan` command. Missing reports, changed report bytes, changed scope, false disposition or nonzero claimed creator/target invocation are refused. Scope binds source commit/tree/lock, compiled closure, configuration pin, actors, marker/target code, selected storage/dependencies/roots and every one of the five source-derived CREATEs: index, name, sender, nonce, null destination, zero value, predicted address, initcode keccak256 and full-envelope SHA256 including fees/gas/chain/type/access list.

The evidence bundle schema is `agialpha.marker-direct-qualification-evidence.v1`. The consensus report's exact limited disposition is `direct-type2-create-does-not-invoke-origin-code`. The execution report's disposition is `five-direct-creates-no-creator-or-target-invocation`, with zero creator and target invocations and content-addressed source-call-graph/initcode-call-graph/trace artifacts. A reference string and checksum bind data; they do not authenticate a reviewer, make a factual claim true or establish independent review. The trusted Mac must separately verify the artifact contents and their provenance. Synthetic test reports must never be reused for the selected account or production approval.

The v2 predicted and receipt-proven packages include the profile, its limited review proposition and `origination-evidence.json`. Receipt export still independently re-verifies all five successful canonical creation receipts, both governor bindings, exact runtime/immutable/getter/event state and final fresh-graph authority. It never converts an unverified report into explorer acceptance or activation permission.

## Direct CREATE and trace limits

EIP7702 permits transaction origination from a valid marker-bearing EOA. Delegation resolution occurs when execution calls that account; a direct type2 transaction with a null destination enters CREATE and executes its supplied initcode. This top-level rule is narrower than a claim that arbitrary initcode cannot call back into the creator or target. All exact constructors and their dependencies must therefore be checked.

Primary references:

- https://eips.ethereum.org/EIPS/eip-7702#transaction-origination
- https://eips.ethereum.org/EIPS/eip-7702#delegation-indicator
- https://eips.ethereum.org/EIPS/eip-1559
- https://eips.ethereum.org/EIPS/eip-7825

The offline trace analyzer requires successful complete supplied local traces, at most 100,000 steps and 32 MiB, a supported opcode/frame model, top-level termination, full call stacks and pinned runtime bytes for every CALL/CALLCODE/DELEGATECALL/STATICCALL destination. It rejects creator/target calls, missing/extraneous code observations, marker-bearing secondary callees and nested CREATE/CREATE2/destruction. The secondary-marker refusal is necessary because a different CALL destination can itself delegate execution to a blocked target. Receipt-block code is end-of-block state, not automatically execution-time state: another transaction in the same block could change a designation. The disposable fixture requires exactly its one transaction in each traced block and excludes in-transaction code changes. Real-chain qualification needs separately trustworthy execution-time code/state attribution; trusted local trace provenance and exact source inspection remain essential. Shape checks cannot prove that an untrusted provider supplied a truthful or untruncated trace.

The retained disposable tests install synthetic marker state in an unforked Osaka EVM, sign with ephemeral test keys, execute the five exact initcodes, retain full traces, verify nonce+5 and unchanged observed marker/target storage/code, then perform both governor bindings and receipt-proven export. A separate actual synthetic alias-marker counterexample proves why destination-only tracing is insufficient. The local network uses chain 1 solely to exercise the exact envelope; synthetic funding, dependencies and latest-as-finalized are explicit. These tests do not establish real 6c8 target safety, current account state, mainnet consensus/finality, hardware custody or actual provider-fork qualification. EIP7825 gas<=16,777,216 remains enforced; blob/beacon/peer-consensus differences remain outside scope. No public debug RPC is allowlisted.

## Mac authority, Ubuntu and one physical signature at a time

The owner uses trusted Mac Studio plus physical Ledger USB approvals, with Ubuntu Hardhat as an experimental proposal/relay environment. Mac owns independently reviewed clean source/toolchain/build/config, accepted evidence, exact intent, authoritative journal and final verification. Ubuntu's own checksum or verdict is not a source anchor. Do not run transferred Ubuntu scripts/hooks on Mac merely because they claim to be reviewed.

The signing interface remains SDK-independent. Mac independently reconstructs and validates exact type2 bytes and recovers the selected sender from the returned signature. The owner physically approves every transaction; no private key, automatic signing or blanket wallet permission is requested. The coordinator can automatically perform approved preparation, readback, configuration bindings and verification between signatures. It must not turn each automatic verification step into a manual CLI task.

Mac may explicitly release one exact already-signed transaction to Ubuntu for one authorized bounded broadcast. This is permitted architecture, not an implemented or authorized live transfer here. The signed bytes are a broadcast capability: Ubuntu cannot alter signed fields without invalidating the signature, but can disclose, withhold, replay the same hash or affect timing/order. Retain the exact hash, intent and release/uncertainty in Mac's journal before transfer. Ubuntu receives neither keys nor future capabilities. Mac independently reconciles the exact canonical hash/receipt and nonce before the next signature. A missing response is uncertain submission, never a reason to generate a replacement or retry blindly. Do not put raw signatures, device sessions or capabilities in public artifacts.

The existing `external-broadcast` session mode retains a signed/handoff operation and blocks advancement until exact receipt recovery; `status`, `handoff`, `recover`, `reconcile` and `finish` expose the phase machine. The seven-operation CLI is reusable for this sender profile. A physical-device UI/bridge and cross-host one-shot release protocol still require their own qualified integration; no claim is made that this delta alone implements that hardware/cross-host layer.

Both actual actor locks use sorted/deduplicated `${chainId}-${sender.toLowerCase()}` keys and durable journals. They coordinate cooperating processes on one filesystem only. An Ubuntu lock does not reserve a Mac nonce. The authoritative Mac must serialize Alpha/Jobs/Manager and exclude other-machine/manual activity. Wallet selection before handoff requires fresh source/evidence/nonce/predictions and a new plan. Any prior handoff/signature/submission must be reconciled first; separate creator locks alone do not implement a universal cross-wallet campaign cancellation barrier.

## Qualification status and next acceptance

The qualified core PR4826 head remains separate from this delta. Local offline tests and the additive hosted workflow must be reviewed against the exact new source before publication. The workflow retains all 111 historical regressions and 38 existing candidate cases, adds seven profile cases/full traces and a separate real-clean-checkout marker CLI campaign. A non-Git overlay cannot claim that campaign passed locally. The source observer, normal TLS verification and output containment remain mandatory. The serial native job budget increases from 30 to 45 minutes to accommodate the third clean-checkout campaign; the prior two-campaign hosted job took 24 minutes. No test is skipped or made advisory.

The selected account's fresh observation is currently unverified after a preserved DNS EAI_AGAIN at the approved public endpoint; no chain response was received. Older observations are stale context, not evidence of rejection or compromise. No provider retry, fork, delegation mutation, live signing, broadcast, old-deployment action, independent security audit or automatic unpause is authorized by these files. Real-account/provider/fork, Mac/Ledger device/display, explorer, external authority/economic readiness and activation approvals remain separate gates.
