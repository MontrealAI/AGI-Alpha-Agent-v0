# Bounded four-repository delivery

This additive research integration calls actual pinned public implementations from AGI ALPHA Agent, AGIJobManager, AGI Jobs, and AGI Fleet Linux. It does not modify their source or replace an existing Harness, owner, review, or release workflow.

## What ran

`study/results/journey.json` contains the actual two-mission journey in project `writer4-graph-enterprise`. Parent `bom-demand-00` produced groups `n4=25`, `n5=25`, `n6=25`, `n7=50` (total125). Its genuinely different successor `remediation-impact-03` produced `n1=1`, `n10=0`, `n4=1`, `n9=0` (total2). Both passed the external graph checker and the actual native worker/internal arithmetic checks. Every output group was compared, not only the aggregate total. One native project retains both cycle IDs and the parent-cycle digest.

The recorded source composition took 5,650.504ms across the two missions. This is a local measurement, not a production latency guarantee. `study/results/source-scope.json` supplies the concise source inventory and cost/coverage limitations; the full journey preserves raw nested artifacts and identifiers.

## Reproduce the joined run

Use Node24.19.0 and Git. Checkouts must be at these immutable commits, without modifications to the loaded source closure:

| Directory | Repository | Commit |
|---|---|---|
| `repos/alpha` | `MontrealAI/AGI-Alpha-Agent-v0` | `9cb90e8c189f146eff7d166e249d9474792c4864` |
| `repos/manager` | `MontrealAI/AGIJobManager` | `3153ac394d37eeecb03e825ecce37559427bc6c3` |
| `repos/jobs` | `MontrealAI/AGIJobsv0` | `ca6cfb74a36c233e5f04bd591a5e2179299774a1` |
| `repos/fleet` | `MontrealAI/AGI-Fleet-Linux` | `45759fb096faf8988f58ae5ea71248d0f35a97c7` |

Manager's unchanged verifier also needs its selected immutable builder source. Fleet's fixed worker imports its existing lockfile dependencies:

```sh
git -C repos/manager fetch --depth 1 origin 2478198819227d4414e17fe90a04e8137d543241
npm ci --prefix repos/fleet/fleet --ignore-scripts --omit=dev
node study/integration/admission.test.mjs
node study/integration/run-journey.mjs study/results/journey-inputs/examples.json repos study/results/journey.json
node study/integration/ownership-audit.mjs
```

The final inputs are previously generated current-source candidate results. `run-journey.mjs` rechecks their exact structured missions with the external scientific checker and then executes the native source route anew. It does not describe old captured native traces as fresh execution. The root evaluation commands produce fresh candidate results separately.

No wallet, gas purchase, provider API, or financial authority is required. The source verifier invokes read-only Git processes. In the managed execution environment, ordinary child-process creation was restricted; the bounded local source computation was reviewed and allowed with those Git reads. No held action, denied browser objective, native installation qualification, or protected review was rerouted.

## Actual repository contribution

| Repository | Called source API | Executable contribution |
|---|---|---|
| Alpha | `examples/successor-project/engine.mjs`: `createProject`, `nextCycle`, `appendRecord`; `examples/successor-workbench/{engine,mission-record}.mjs` | Durable mission/project history, exact CSV workbench run and source-bound mission records |
| Manager | `site/assets/successor/alpha-project.mjs`: `importAlphaProject`, `advanceAlphaProject`; normal `scripts/successor/build.mjs` | Explicit same-row mapping, local exact-arithmetic candidate, separate unsigned USDC6 plan and ordinary selected-source verification |
| Jobs | `integrations/alpha-agent/project-transfer.mjs`: `importAlphaProject`, `runProjectTransfer` | Nested history inspection, unfunded AGIALPHA18 work graph and local adapter execution |
| Fleet | `local-runtime/project/transfer.mjs`: `createProjectRequest`; `local-runtime/worker.mjs`: `perform('agent', task)` and `perform('node', reviewTask)` | Fixed bounded local worker plus artifact/arithmetic check, with the exact inherited project |

The wrapper verifies 103 statically imported repository files against their actual Git HEAD blobs: Alpha10, Manager24, Jobs19, Fleet50. Manager's normal builder verifier separately checks its selected source inventory. The source bridge itself has SHA-256 `14f321b2fe04563e60ae1b088f9a2337b52ab52f7146c25f5d794d5eecd92b70`; its composed source binding is `684cc3e243ab81e0f513670f2b37e8fed813ea145f82b3d090bb1021e181e866`.

## Scientific admission and exact bindings

`createMissionDelivery({repositories, check, concurrency: 2})` requires a checker installed by the trusted caller. The enterprise cannot replace this callback. It accepts `(mission, candidateResult)` and returns `{accepted, artifact, proof}`. `artifact.mjs` constructs the declared canonical artifact and calls the external `checkArtifact(artifactBytes, inputBytes, criteriaBytes)` implementation. Only that evaluator emits the scientific proof receipt.

`prepareDelivery` independently enforces row/amount bounds, empty candidate permission/proof fields, exact mission/input/output binding, the typed capability digest, and canonical CSV equality. Proof input/artifact hashes use the evaluator's stable key-order JSON plus a newline. Candidate hashes use stable JSON without a newline; both are explicitly recorded rather than conflated.

Each Alpha/Manager/Jobs/Fleet envelope has a separate transfer binding to the graph mission input, normalized output, capability ID and full manifest, canonical scientific artifact, and external proof. Native CSV arithmetic checking does **not** establish graph semantics. That gap is closed only by the external semantic checker on the bound mission/artifact.

The local queue is limited to two concurrent deliveries and at most32 waiting deliveries. Identical pending deliveries share a result; rejected attempts can be retried. Interruption is enforced before admission and before native launch. The fixed native API exposes no mid-call cancellation; an interruption observed afterward suppresses release and retains the native result in the error. No in-flight preemption claim is made.

`evidence/runtime/integration-admission-02-bounded.txt` records eight passing boundary checks, including wrong-algebra semantic refusal, altered input/output/capability/CSV rejection, oversized output, forged candidate authority, initial/queued interruption, queue ceilings, concurrent deduplication, retry after rejection, and receipt rebinding refusal. Queue controls were tested before native execution, using controlled evaluator waits. They are not a full native load campaign. The separate native bridge has nine passing existing source-boundary checks in `evidence/runtime/bridge-tests-03-current.txt`.

## Explicit gaps and preserved decisions

This is **local source composition**, not a joined installed four-repository release. Manager and Jobs installed profiles select older exact Alpha inputs; those selectors were not changed. Fleet main lacks the newer Discovery/enterprise receiver present in separate unmerged work. The route uses existing main public-data APIs, preserving unsupported links as gaps.

The fixed Fleet worker is invoked directly in process. Native supervisor admission, protected-boundary review, namespace isolation, installed-distribution acceptance, and production readiness were not established. Worker and internal checker roles execute separately under the same controller; this is not institutional independence.

Manager's USDC6 plan remains separate from Jobs' AGIALPHA18 plan. Both are unfunded; source-adapter settlement is `not-connected` and actual funds moved are zero. Local EVM contract evidence is a separately bound experiment owned by the contract lane. No source bridge result asserts a live transfer or mainnet authorization.

Harness #4863/#4865 holds, Fleet #61's stopped review/unknown narrower denial, the four named held native/site probes, and the original denied browser objectives remain untouched. `evidence/runtime/AUDIT.json` and `browser-denial-scope.json` record the public action boundaries.

`ownership-audit.mjs` records export/restore, three generations of history, proof/authority reset, no self-parent edges, and an actual Kahn→DFS symbolic strategy change followed by a fresh external mission-output check. The requested representation qualification remains a request until the evaluator issues it. Learned-provider replacement, customer demand, realizable revenue, live profit, and fully attributable development costs remain unverified.
