# Writer 10: verified foundations and integration boundary

## Observed source identities

This audit reads public source and executes local synthetic modules. No repository mutation, public-chain transaction, provider call, release qualification, or production authority is established.

| Repository | Source read and locally exercised |
|---|---|
| AGI-Alpha-Agent-v0 | `197147ffd22c5ae13113162afffaf3ce9c10aa2e` |
| AGIJobManager | `c5958eae872458c2f3cac48fea0b4bbfadc6ac6c` |
| AGIJobsv0 | `9983478d42c32fe399f28dd9b0e0173f904b8a11` |
| AGI-Fleet-Linux | `45759fb096faf8988f58ae5ea71248d0f35a97c7` |
| Alpha selected by both native route harnesses | `0385df4c9728db19c396e039cd04678eebfddb9e` |

The two route harnesses deliberately require an earlier exact Alpha commit. Their immutable pin was respected. A current main checkout cannot silently replace the selected native source. The audit is a snapshot of moving repositories; it does not claim those heads remain latest.

Alpha `AGENTS.md` and Fleet `AGENTS.md`, `CONTRIBUTING.md`, and `docs/DEVELOPMENT.md` were read. Local work preserves runtime, policies, source pins, historical evidence, and original publication paths. No vendor code was modified; selected modules are copied byte for byte with digests and licenses for reproducibility.

## Three source manuscripts

All three were read from the Alpha snapshot, rather than earlier conversation summaries. `source-pins.json` retains SHA-256 and byte counts.

* [Transformational Intelligence](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/197147ffd22c5ae13113162afffaf3ce9c10aa2e/docs/Transformational_Intelligence.pdf), SHA-256 `d7170e8217e3bf6aa1b84868c1c76c5994c6995c5297ed092d7e72a6430c664f`. Its operational distinction is between improving a solver within a formulation and constructing a better formulation while preserving the authorized intent. It explicitly distinguishes purpose, formulation, and evaluation instrument. The finite causal example admits an unrestricted optimal-planner tie; it is not evidence of a new universally superior solver or a frontier-model achievement. Writer 10 should apply that discipline to an operational bottleneck and retain the matched competitor.
* [Invent the Economy](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/197147ffd22c5ae13113162afffaf3ce9c10aa2e/docs/Invent_the_Economy.pdf), SHA-256 `61e92a47b32cbca12b705094b982dddaca03b3dfe2b7f657bbf30eb8d56bba79`. It separates correctness, participant benefit, profitability, liquidity, and realized exchange. Its numerical examples are supplied-model arithmetic, not observed customer commitments. The discussion permits productivity to reduce billable operations and token activity. Writer 10 contributes the copying/replication test; it must not import the earlier hypothetical prices as measured demand.
* [The Possibility Foundry, edition 1](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/197147ffd22c5ae13113162afffaf3ce9c10aa2e/docs/papers/possibility-foundry-v1.pdf), SHA-256 `906b63fe49294fc6c7fb4963f8cfea0e59863058c2f2845778e1bf8ad777ccca`. The actual path is `docs/papers/possibility-foundry-v1.pdf`, not a top-level `papers/` directory. It reports a synthetic spectroscopy construction, equality of scientific outcomes with cheaper competent builders, partial transfer, and 0/128 narrow-line stress success. It explicitly leaves native spectroscopy admission, physical validation and full commercial value unestablished. Its historical exposure accounting is not adopted as Writer 10's cost basis: detector acquisitions and computational scoring must remain separate units.

The directions of Writers 8 and 9 remain scope distinctions, not evidence for Writer 10's conclusions. This study does not use Writer 6 assumptions or findings.

## What the two routes actually implement

The Manager receiver is [`scripts/integrations/discovery-lab-work-request.mjs`](https://github.com/MontrealAI/AGIJobManager/blob/c5958eae872458c2f3cac48fea0b4bbfadc6ac6c/scripts/integrations/discovery-lab-work-request.mjs). The Jobs receiver is [`integrations/alpha-agent/discovery-lab-work-request.mjs`](https://github.com/MontrealAI/AGIJobsv0/blob/9983478d42c32fe399f28dd9b0e0173f904b8a11/integrations/alpha-agent/discovery-lab-work-request.mjs). Their public exported interface is `receiveDiscoveryLabWorkRequest(raw, {expectedBindings, expectedCommission, inspectCampaign, ...})`.

Both call an independently selected installed Alpha inspector. Request JSON does not select executable code or provision its own trusted context. Manager's denomination is USDC, six decimals; Jobs' denomination is AGIALPHA, eighteen decimals. Each laboratory request in this audit has a zero cap, `authority: none`, `DRAFT_NOT_SUBMITTED`, and unprovisioned external execution. They are alternative currency branches of one frozen logical commission, with no conversion or shared balance.

The unmodified native harness authenticates Git objects and SHA-256 identities, captures the 26-file catalog plus inspector in a private snapshot, constructs a real native synthetic mission, replays its actual checker, and creates admission receipts. This is substantially stronger than a transport checker double, but remains a finite local synthetic mission and a single operator's execution.

### Executed observations

Commands run under Node 24.19.0:

```
node AGIJobManager/scripts/integrations/discovery-lab-native-test.mjs /absolute/alpha-route-pinned > manager-native.json
node AGIJobsv0/integrations/alpha-agent/discovery-lab-native-test.mjs /absolute/alpha-route-pinned /absolute/shared-workspace.json > jobs-native.json
```

The second invocation reopened the first invocation's retained workspace. Both produced workspace digest `809019026a7b3eda0e1d6754a7e0342accda1a7f8b5106c3e7de8729a07f4ee5`.

| Case | Manager USDC | Jobs AGIALPHA |
|---|---|---|
| learn, think, design, strategise, execute, evolve | Six `local-checked` receipts | Six `local-checked` receipts |
| Stronger successor with preserved accepted predecessor | `local-checked` | `local-checked` |
| Missing inspection reserve | `inconclusive` | `inconclusive` |
| Rehashed invalid measurement | `local-rejected` | `local-rejected` |
| Retained native history | accepted, rejected, inconclusive, accepted | Same frozen history |
| Currency cap / authority | 0 / none | 0 / none |

The result is 18 receiver observations across the two routes, including four negative/inconclusive cases. It is not 18 independent scientific trials. The duplicate native source and shared workspace are intentional continuity evidence, not independent replication. The full JSON preserves source custody, logical resources, encoded storage and measured elapsed costs. Their logical units must not be relabeled as monetary cost or combined with hardware acquisitions.

The scheduling/capacity experiment introduced by Writer 10 is a different domain. These results establish native route behavior on the existing supported mission; they do not qualify arbitrary new scheduling payloads for native admission, external Fleet dispatch, review, or settlement. That remaining adapter boundary must be explicit in the paper.

## Actual reusable modules for Writer 10's execution-evidence ledger

### Jobs purpose-bound signed records

[`packages/successor-core/src/signatures.mjs`](https://github.com/MontrealAI/AGIJobsv0/blob/9983478d42c32fe399f28dd9b0e0173f904b8a11/packages/successor-core/src/signatures.mjs#L42-L281) exports `generateSigningIdentity`, `trustKey`, `signPayload`, and `verifySignedPayload`. It uses Node's Ed25519 implementation, canonical JSON, explicit signer role, scope, validity, revocation, and fixture/live separation. Context has exact fields `institutionId`, `missionId`, `environment`, and `mode`. Keys generated by the local bridge are ephemeral fixture keys held only in process memory; public keys and signed records may be published. No live credential or production trust root is generated.

`registry-bridge.mjs` accepts an actual JSON research result and exercises these unchanged modules. Six attacks are rejected: changed payload, cross-mission replay, expired key, wrong purpose, unknown signer, and revoked key. An intentionally false statement signed by the trusted local recorder is accepted. This negative control is essential: a signature proves a binding to the chosen key, not physical truth, correct scientific measurement, independent custody, or authority to operate a successor. The bridge labels its independence I0.

### Fleet actual outcome ledger

[`fleet/successor/outcomes.mjs`](https://github.com/MontrealAI/AGI-Fleet-Linux/blob/45759fb096faf8988f58ae5ea71248d0f35a97c7/fleet/successor/outcomes.mjs#L9-L117) exports `OutcomeLedger`, `verifyLedger`, `summarizeOutcomes`, and `exportAttemptObservations`. The bridge appends and reopens actual hash-chained attempt, unknown-cost, completion, and internal-review records. Mutating a historical entry without reconstructing its chain is rejected. The system accurately reports zero externally attested accepted outcomes, unknown compute/provider cost, unknown human effort, and `productionQualified: false`.

A hash chain alone does not prevent an operator from rewriting an entirely unanchored history or presenting two forks. Publication, independently retained checkpoints, or a consensus log changes that threat model; none is asserted by local chaining. The recorded review is internal, not a fabricated independent reviewer. No paid estimate is substituted for unknown invoices.

### Alpha bounded resource optimizer

The current source contains a reusable, finite min-sum implementation at [`examples/successor-capability/out-execute/`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/197147ffd22c5ae13113162afffaf3ce9c10aa2e/examples/successor-capability/out-execute). It is suitable for a separately declared finite allocation projection:

* `model.mjs:35-68`: strictly validates complete finite factor tables; nonnegative integer cost and `null` infeasibility; domain and size limits.
* `engine.mjs:240-261,351-391,394-447`: `startExecution`, `advanceExecution`, `inspectCompletion`, `retainCompletion`, and `execute`. A completion carries the resource ledger, exact source identities, model, decomposition, witnesses, current acceptance, and zero external authority.
* `source-manifest.mjs:10-30`: `installedSource()` hashes the actual compiler/checker import closures. This authenticates local bytes, not an external attestation.
* `baselines.mjs:5-13,17-53`: independent full enumeration and a sufficient fixed-certificate reuse control. The latter can beat a more general machinery on constant factor shifts; the implementation does not hide that possibility.

The main research experiment should use this where its model semantics fit, or state clearly that it only consumes the existing signatures/ledger and that operational scheduler integration is new. The audit does not label the optimizer executed unless a separate retained run is included.

## Seven-stage journey and four distinct objects

| User journey | Verified source interface | What the local native route exercise established |
|---|---|---|
| Identify | `workspace.createWorkspace`, `discovery-lab.validateCharter`; independent frozen mission and source context | Explicit fixed purpose, budget, allowed operations; no independent autonomous opportunity discovery claim |
| Out-Learn | `runCampaign`, `ARTIFACT_KINDS[0]`; native learn builder and checker | Finite synthetic measurement program, actual current checking |
| Out-Think | `ARTIFACT_KINDS[1]` | Finite explanatory/model artifact bound to preceding evidence |
| Out-Design | `ARTIFACT_KINDS[2]` | Constructed finite artifact under declared grammar and resources |
| Out-Strategise | `ARTIFACT_KINDS[3]` | Bounded compiled strategy with native acceptance |
| Out-Execute | `ARTIFACT_KINDS[4]` | Local synthetic execution and its resource record; no physical instrument or provider |
| Out-Evolve | `ARTIFACT_KINDS[5]`; `recordDiscoveryEvent`; stronger descendant checks | Accepted predecessor preserved; rejected and inconclusive attempts retained; new descendant examined |

These are actual source stage discriminators, not invented generic APIs. The new research question maps onto the journey conceptually; each new domain connection needs its own explicit adapter and retained result.

The native Alpha protocol separately defines [`WorldProgram` and `PolicyProgram`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/197147ffd22c5ae13113162afffaf3ce9c10aa2e/alpha_factory_v1/core/runtime/successor/protocol.py#L356-L387) and [`ProofProtocol`, `ProofReceipt`, `AdmissionDecision`, and `AuthorityEnvelope`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/197147ffd22c5ae13113162afffaf3ce9c10aa2e/alpha_factory_v1/core/runtime/successor/protocol.py#L596-L684). World is explanatory/predictive state; Policy proposes decisions; Proof is a scoped attributed examination; Admission is a separate accountable decision; Authority is an indivisible, current permission. The grant path [`state.py:435-469`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/197147ffd22c5ae13113162afffaf3ce9c10aa2e/alpha_factory_v1/core/runtime/successor/state.py#L435-L469) enforces context, controller identity, budgets, validity, admissions and prerequisite proofs; local receipts do not establish production evidence. These Python paths were read, not executed by this audit. The two route demonstrations correctly retain `authority: none`.

## Reproduction and evidence

`reproduce-routes.py --work /absolute/new-directory` creates fresh sparse checkouts at the exact required commits and runs the two unmodified native harnesses. It requires Python 3, Git with network read access, and Node 24. It refuses an existing work directory. No wallet, RPC, model API, provider credential, or external submission is used.

`node registry-bridge.mjs /absolute/result.json > registry-evidence.json` executes the exact vendored Jobs/Fleet modules against a bounded research result. Retain public fixture trust alongside the record, never private keys. Its bundled fixture is an API exercise only; the final paper should use the final actual experimental record.

Evidence files: `manager-native.json`, `jobs-native.json`, `shared-workspace.json`, `registry-bridge.json`, `source-pins.json`, and `vendor-manifest.json`. The route JSON and signatures contain nondeterministic IDs, timestamps, keys and timings; reproducibility means rechecking the same semantic outcomes and source identities, not expecting byte-identical receipts across runs.
