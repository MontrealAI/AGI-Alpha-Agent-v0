# Published-system integration and evidence boundary

This is an additive, offline research adapter. It does not install a Fleet executor, use a deployed contract, settle a job, or clear a held review. The source receipts distinguish the actual numerical output, local test evidence, integrity checks, imported history, and explicit fixture authority.

## Exact sources inspected

The repository identities and public `main` commits below were retrieved during the 2026-10-24 source audit. These are pinned observations, not a claim that a mutable branch will remain unchanged. `vendored/SOURCES.json` records exact paths, original Git blob IDs, SHA-256, licenses, and immutable URLs for every unchanged file used locally.

| Repository | Repository ID | Inspected commit | Used surface |
| --- | --- | --- | --- |
| [MontrealAI/AGI-Alpha-Agent-v0](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9) | `922805069` | `dfc79c4ae81ac612cbff9865a0af8389b6ff3de9` | Published SUCCESSOR dispatcher, typed programs, trust and authority checks, journal, descendant admission |
| [MontrealAI/AGIJobsv0](https://github.com/MontrealAI/AGIJobsv0/tree/9983478d42c32fe399f28dd9b0e0173f904b8a11) | `1031364470` | `9983478d42c32fe399f28dd9b0e0173f904b8a11` | Zero-cap receiver and native MissionPack inspection, restore, successor |
| [MontrealAI/AGIJobManager](https://github.com/MontrealAI/AGIJobManager/tree/c5958eae872458c2f3cac48fea0b4bbfadc6ac6c) | `1142965004` | `c5958eae872458c2f3cac48fea0b4bbfadc6ac6c` | Separate zero-cap USDC receiver |
| [MontrealAI/AGI-Fleet-Linux](https://github.com/MontrealAI/AGI-Fleet-Linux/tree/45759fb096faf8988f58ae5ea71248d0f35a97c7) | `1412491845` | `45759fb096faf8988f58ae5ea71248d0f35a97c7` | Source-only audit of admission, project transfer and successor import |

The audit read repository instructions, the #4850 coordination record, and existing review holds before implementing the research wrapper. The public coordinator remains the receiving owner for shared paper indexes and Pages; a branch's `protected=false` metadata is not permission to ignore that ownership. The original #4863 merge denial is not cleared by creating this wrapper, and neither the dependent #4865 lane nor held Fleet changes are copied into it. Relevant public records include [coordination comment 6377105309](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6377105309), [review hold 6347342683](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4863#issuecomment-6347342683), and the [published Alpha main source](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/alpha_factory_v1/core/runtime/successor).

## Smallest executable extension

`harness_adapter.py` imports the unchanged, hash-verified published Python modules. `framework_bridge.mjs` imports the unchanged, hash-verified published JavaScript receivers and pack modules. New scientific work resides in `numerics.py`; the integration demo and independently written checker are `demo_harness.py` and `independent_checker.py`. No core runtime file is edited.

| Source path / API | Actual local operation | Claim boundary |
| --- | --- | --- |
| Alpha `alpha_factory_v1/core/runtime/successor/jobs.py`: `JobDispatcher.seal`, `dispatch`, `execute_tool`, `complete` | Seals exact job terms, checks execution assignments, invokes one numerical handler and one checker per run, retains their output and acceptance records | Trusted installed research code; this dispatcher is not an operating-system sandbox |
| Alpha `successor/protocol.py`: `WorldProgram`, `PolicyProgram`, `CandidateReleaseManifest`, `ProofReceipt`, `AuthorityEnvelope` | Binds caller-supplied WORLD/POLICY descriptions, code, environment, evaluator, output evidence and explicit local permission | Typed records do not supply a predictive model or make their substantive claims true |
| Alpha `successor/state.py`: `SuccessorStore`, `ActionGateway` | Records current correctness evidence, admits the exact candidate, requires an explicit matching grant, rechecks before one read-only artifact inspection | Fixture permission permits a named local reader; it is not external execution authority |
| Manager `scripts/integrations/discovery-lab-work-request.mjs`: `inspectDiscoveryLabWorkRequest` | Accepts a byte-bound local handoff with `manager-usdc`, `USDC6`, `capBaseUnits:'0'` | `synthetic-local`, `DRAFT_NOT_SUBMITTED`, authority `none`, settlement `not-connected` |
| Jobs `integrations/alpha-agent/discovery-lab-work-request.mjs`: same API | Separately accepts a byte-bound local handoff with `jobs-agialpha`, `AGIALPHA18`, `capBaseUnits:'0'` | Same local-only boundary; the token route is not interchangeable with USDC |
| Jobs `packages/successor-core/src/pack.mjs`: `createMissionPack`, `verifyMissionPack`, `restoreMissionPack`, `createSuccessor` | Commits programs, measured evidence, negative knowledge and exact numerical-recipe bytes; inspects integrity; restores knowledge; retains parent-pack lineage | Integrity is `authenticated:false`; restore has no current proof, active authority or enabled execution |
| Fleet `local-runtime/supervisor/admission.mjs`, `project/transfer.mjs`, `supervisor/successor.mjs` | Source inspected; custom numerical execution not provisioned by the inspected published admission surface | No installed Fleet run or successful four-product execution is claimed |

The receiver's supplied inspection callback checks artifact/receipt binding; it does not independently recompute the numerical solution. Its numerical conclusion comes from the separately retained Python checker. The native receiver's resource units are declared bounded accounting fields, not hardware-instruction counts or expenditure.

## Public fixture and authority

The adapter reuses exactly the published [RFC 8032 §7.1 TEST 1](https://www.rfc-editor.org/rfc/rfc8032#section-7.1) keypair whose public key is already used in Alpha's `tests/runtime/test_successor_signatures.py`. The fixture public key is `d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a`. Its private bytes are public standard test data. No new identity, operational credential, API token, trust configuration outside the disposable fixture, or external account is generated. Key and API-token generators are patched to fail during the native runs.

The local controller, producer and verifier role labels deliberately share this one public test key. Their signatures exercise the source's schema and decision boundaries but offer **no authentication, independent custody, institutional review or beneficiary acceptance**. The protocol `sandbox` authority label does not establish OS isolation. No on-chain transaction occurs.

WORLD records the fixed matrix, manufactured RHS process, task size and source identity. POLICY records the fixed solver and preregistered acceptance conditions. PROOF records the separately implemented check of actual output bytes, with its full residual, backward-error and manufactured forward-error evidence. AUTHORITY is a separately signed public-fixture envelope naming the exact candidate, environment, action, tool, target, context, resource bound and expiry. Current proof alone cannot authorize the artifact reader.

## Inspectable stages and causal scope

The seven TI stages are research responsibilities, not a forced renaming of the native lifecycle. The published native compiler requires `constitution → evidence → formation → challenge → verification → admission → renewal`. The adapter fulfills that contract with source/protocol commitments, one construction, one independent calculation, byte/source reinspection, accepted local work, and retained lineage requirements. It does not add model calls or transactions to claim completeness.

| TI research stage | Inspectable evidence |
| --- | --- |
| Identify 🔍 | Fixed mission, matrix family, beneficiary limitation and repeated-setup bottleneck in the protocol |
| Out-Learn 📚 | Public data manifest, calibration records and exact source ledger |
| Out-Think 🧠 | Explicit deadline targets, uncertainty and costed decision model in the main study |
| Out-Design 🎨 | Solver recipe, preflight, independent output checker and restoration contract |
| Out-Strategise ♟️ | Frozen comparator/policy choice; no selection using confirmation results |
| Out-Execute ⚡ | Actual bounded solve, retained output, native execution assignment and separate inspection authority |
| Out-Evolve ♾️ | Negative knowledge, pack integrity, parent lineage, actual refactorization and fresh checking |

Only the observed guards support a direct local gating claim: with current evidence held fixed, a missing or expired authority grant refuses the effect; with a still-current grant, expired proof refuses the effect; a descendant without fresh proof is refused. A deliberately corrupted small solve produces a fail receipt and no admission or grant. These controls do not establish a separately identified causal effect for every conceptual TI stage, a customer-owned deployment, forecast usefulness, or Mission Alpha. The main preregistered comparisons determine those narrower scientific conclusions.

## Fixed numerical demonstration and restoration

The planned integration case is `1138_bus`, seed `1701`, `q=4`. Both the handler and checker generate a full `(n,16)` normal array and then take its first four columns. The right-hand sides are synthetic on a real-origin public matrix. The checker rereads and verifies the retained artifact, archive, matrix bytes, dimensions and nonzero count. It regenerates manufactured truth and computes each sparse row product with `math.fsum`; it does not import `numerics.quality`. It checks every column against all three preregistered tolerances.

There are exactly two engineering runs, excluded from comparative numerical trials. The first constructs `ReadinessInstrument` through the actual dispatcher. The bridge places the exact recipe bytes into a native Jobs MissionPack, verifies it, restores knowledge with `proofCurrency:'absent'`, `activeAuthority:[]`, `executionEnabled:false`, and creates a proposed successor bound to the parent digest. The second uses the restored recipe as **data**, invokes the fixed audited `ReadinessInstrument.restore`, refactorizes the matrix, repeats preflight, solves and checks a fresh output. It receives a new native fixture, evidence record and explicit grant; neither proof nor authority is inherited from the pack.

`demo-summary.json` records full process wall/CPU cost, two native runs, numerical build/preflight/solve/check components, Node route/pack work, imported-recipe handling, and orchestration. Nested numerical costs are not added again to their enclosing run. The external command timer captures final summary serialization and process shutdown omitted from the in-process summary. Unknown authoring/review/maintenance costs remain the responsibility of the main cost ledger and are not silently assigned zero.

## Failure retention and reproducibility

The early `harness-engineering-001` and `002` runs failed on native schema constraints after the seven jobs: an unsupported disclosure enum, then scientific notation in a fixed-decimal field. Their evidence directories and `FAILURE.json` records are retained. The corrected small numerical probe in `003` passed, and `harness-negative-001` recorded the corrupted-output rejection. They are development evidence, not the preregistered scientific outcomes.

After the parent study freezes the source and data, run the reviewed demonstration once into a new output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python demo_harness.py evidence/native-demo-001
```

Python requires the same pinned numerical environment as the main study, plus the published Alpha dependencies (`pydantic` and `cryptography`); Node executes local ESM source only. No network call, model call, contract RPC, financial action, paid service, credential generation or held runtime is part of this command. Repeated executions use fresh directories and count as additional engineering costs. Source and evidence hashes distinguish each run.
