# Structured graph-to-reduction candidate

This directory is the **candidate/proposer**, not the evaluator or authority service. It compiles a bounded graph mission into exact integer rows that the existing four-repository CSV route can execute. The first capability performs weighted manufacturing bill-of-materials propagation. A successor adds a Boolean kernel for software dependency impact, retaining the graph representation and normalizer.

The original contribution under evaluation is **reuse of exact, separately scoped module qualification while every mission receives a fresh input/output check**. Generic DAG algorithms, dynamic programming, typed composition, and authority separation are prior techniques. The candidate constructs a typed executable program from a finite preimplemented module catalog. It does not autonomously synthesize new source code.

## Run the public development checks

Use Node **24.19.0**, the runtime used for the recorded candidate experiments. No package installation, model provider, wallet, or gas purchase is needed for these checks.

```sh
node study/enterprise/development.test.mjs
```

The final development log is `evidence/runtime/enterprise-development-04-lineage-v2.txt`: 12 tests passed. These are public development examples, not the independent scored mission bank. The seven evaluated source modules are pinned in `evidence/runtime/enterprise-source-manifest-v2.json`; root SHA-256 is `71fed4b4befecc4f5d142b4b9bcfb7123aa737991b84d5f243f22aeeb87ee592`.

The first scored source had a metadata defect: repeated reuse attached a capability to itself as its parent. Its original files, manifest, test log, and results remain under `study/results/scored-v1/`. The v2 correction preserves the prior parent when the content identity is unchanged. Algorithms and task population were unchanged. The root evaluator recorded the original blinded epoch and a separately labeled confirmation on the now-known population.

## Minimal API

```js
import {
  createWorkspace, solve, exportWorkspace, restoreWorkspace
} from './compiler.mjs';

const mission = {
  schema: 'tae/mission-v1',
  missionId: 'assembly-example',
  kind: 'bom-demand',
  graph: {
    nodes: ['assembly', 'left', 'right', 'shared'],
    edges: [
      {from: 'assembly', to: 'left', weight: 2},
      {from: 'assembly', to: 'right', weight: 3},
      {from: 'left', to: 'shared', weight: 5},
      {from: 'right', to: 'shared', weight: 7}
    ]
  },
  seeds: [{node: 'assembly', amount: 2}],
  targets: ['shared']
};

const parent = solve(mission, {
  workspace: createWorkspace({id: 'example-enterprise'}),
  variant: 'full-loop',
  budget: {operations: 1000000, hashBytes: 10000000, elapsedMs: 10000}
});
// parent.rows === [{group: 'shared', amount: '62'}]

const childWorkspace = createWorkspace({
  id: 'example-successor', parent: parent.workspace
});
const child = solve({
  ...mission, missionId: 'impact-example', kind: 'remediation-impact'
}, {workspace: childWorkspace});
// child.rows === [{group: 'shared', amount: '1'}]
// This small example isolates algebra. The scored successor also changes topology.

const portable = exportWorkspace(child.workspace);
const restored = restoreWorkspace(portable);
const symbolicSwap = restoreWorkspace(portable, {modelId: 'dfs-v1'});
```

`solve` is synchronous and returns immutable plain data. No returned object certifies its own scientific correctness. The separately owned evaluator must check the canonical artifact before delivery.

## Input and mathematical semantics

Graph direction is **source assembly/package → required part/dependent service**. Nodes and output labels match `/^[A-Za-z0-9_-]{1,48}$/`. Limits are 64 nodes and 256 edges. Graphs must be acyclic; all endpoints must exist. Parallel edges are permitted and retained. Edge weights are positive safe integers. Seeds are a nonempty bounded list of nonnegative safe integers. Duplicate seeds add for weighted propagation and combine by Boolean OR for reachability. Targets are nonempty, unique, declared nodes. Input order does not determine the canonical label order.

For `bom-demand`, a node's exact demand is its own seed plus each incoming predecessor demand multiplied by that edge's weight. Every distinct path and parallel edge contributes. The implementation uses BigInt, with a 4,096-digit internal safety ceiling.

For `remediation-impact`, a node is affected if its seed is positive or an affected node can reach it. Outputs are `"0"` or `"1"`; multiple paths do not multiply an affected service. Edge weights do not affect Boolean reachability. This algebra differs from weighted demand, so reusing the arithmetic kernel would be wrong even when the graph parser remains valid.

For `flat-reduction`, the input is instead:

```json
{"schema":"tae/mission-v1","missionId":"flat-example","kind":"flat-reduction","rows":[{"group":"part","amount":2},{"group":"part","amount":-1}]}
```

Flat input is limited to 2,000 rows and absolute amount ≤1,000,000 per input. All output rows use **canonical decimal strings**, with lexicographic codepoint group ordering. Native delivery additionally requires absolute amount ≤1,000,000 per normalized output group and absolute **signed aggregate** ≤1,000,000. A valid exact internal result outside these delivery limits is returned as `status: "complete"` with `delivery.status: "infeasible"`; the integration boundary refuses it.

## Stable module boundaries

| Module | Named public API | Purpose |
|---|---|---|
| `protocol.mjs` | `createMeter`, `canonical`, `digest` | Explicit limits, immutable data, counted events and SHA-256 byte accounting |
| `representation.mjs` | `parseGraph`, `topologicalOrder`, `buildRepresentation`, `bindQuery` | Canonical graph parsing, DAG invariant, query binding and adjacency representation |
| `kernel-weighted.mjs` | `weightedReduce(representation, {seeds, targets}, {meter})` | Exact sum-product propagation |
| `kernel-boolean.mjs` | `booleanReduce(representation, {seeds, targets}, {meter})` | Idempotent reachability |
| `normalizer.mjs` | `flatReduce`, `normalizeRows` | Exact group reduction, canonical CSV, delivery feasibility |
| `direct-specialist.mjs` | `directReduce` | Supplied deterministic specialist comparison; not a recruited human expert |
| `compiler.mjs` | `createWorkspace`, `solve`, `executeProgram`, `exportWorkspace`, `restoreWorkspace`, `sourceManifest` | Typed program construction, trace, lineage and reversible state |

All APIs accept only local data and standard-library instrumentation. The source inventory discloses the **whole installed catalog**, including the Boolean module. The parent **capability's executable grammar and module membership** contain only weighted propagation. The distinct successor adds the Boolean module to that grammar. This distinction prevents a claim that the implementation invented a new algorithm at runtime.

## Result, variants, and instrumentation

The result schema is `tae/candidate-result-v1`. Important fields are `missionId`, `kind`, `variant`, `status`, `failure`, `rows`, `csv`, `delivery`, `inputHash`, `outputHash`, `sources`, `capability`, `reuseLedger`, `validationRequest`, `trace`, `metrics`, and `workspace`. Status is `complete`, `refused`, `exhausted`, or `interrupted`. Partial calculations do not become deliverable output.

Variants are `full-loop`, `no-inheritance`, `no-construction`, `wrong-algebra`, `old-representation`, and `direct-specialist`. The two deliberate stage ablations may produce structurally valid but semantically wrong output; the independent checker must reject that output. No-construction refuses graph tasks and retains the supported flat path. No-inheritance reconstructs only the requested mission's grammar. Direct specialization avoids capability construction and can be faster.

The connected trace uses Identify, Out-Learn, Out-Think, Out-Design, Out-Strategise, Out-Execute, and Out-Evolve. Inputs, selected representation, construction/reuse, output hashes, failure reasons, and stage costs are recorded. Flat/direct variants explicitly explain skipped construction stages. These stage names do not establish human superiority or general autonomy.

Metrics separate construction, execution, and control **instrumented events**; every SHA-256 byte operation performed inside `solve` is counted separately. These events are not CPU instructions, model tokens, dollars, or an economic objective. Wall time and process CPU are separately measured. `maxRSSKiB` is a process high-water mark, not incremental per-mission memory. Provider calls and financial transfers are zero for the candidate. Full development/model/human-time monetary costs are not established.

Budgets cap instrumented events, hash bytes, and monotonic elapsed time. An `AbortSignal` is checked at instrumented boundaries. No signal grants transaction authority. Code only computes and reads its own declared source files.

## State ownership and qualification limits

Exports preserve program definitions, exact module hashes, provenance, and mission history. Their checksum detects accidental changes; it is not a signature or permission. Descendants and restored workspaces always begin with `currentProof: null` and `authority: []`. Caller-supplied parent proof is historical, explicitly untrusted evidence only. Costs remain available in separately retained full result records; the compact workspace history contains hashes and status rather than cumulative monetary accounting.

Kahn and DFS are actual different symbolic traversal strategies. Swapping them preserves supported answers in the recorded three-generation audit, requests fresh representation qualification, and receives a new mission-output check. A learned-model/provider swap remains unverified.

The evaluator lives outside this directory and owns its bank, qualification cache, criteria, and proof receipts. The separation is source/process ownership under one controller; it is not hostile operating-system isolation or independent institutional review. Finite qualification tests are not a theorem of unbounded program correctness.

See `../integration/README.md` for the joined native source route and its precise limitations.
