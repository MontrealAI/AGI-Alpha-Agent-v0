# Actual Alpha runtime integration for BLOOM

This directory contains a narrow, unchanged snapshot of published Alpha runtime
code plus a new local adapter. The scientific experiment remains separately
identified. No Writer 6 implementation or results are a dependency.

## What actually runs

`native_workflow.execute_stages` invokes the real pinned Alpha APIs:

1. `SuccessorStore.create_institution` and `register_release`.
2. `JobDispatcher.seal` on a real `JobGraph`.
3. For each source-bound installed pure callback: `dispatch`, `execute_tool`, and
   `complete` using the real `ExecutionAuthorization`, `JobContract`, and
   `JobResult` types.
4. `SuccessorStore.recover` and `Journal.control(True)` to finish stopped.
5. Actual `Journal.verify`, `backup`, and `restore`, then explicit graph, policy,
   environment, source and artifact revalidation. The restored institution stays
   stopped, the global controller paused, and proofs/grants empty.

All eight upstream Python files are unchanged from Alpha commit
`dfc79c4ae81ac612cbff9865a0af8389b6ff3de9`. Their public source URLs, original Git
blob IDs, bytes and SHA-256 values are in `vendor/SOURCE.json`. The custom package
initializer preserves relative imports under a narrow namespace. It does not
pretend that the entire Alpha distribution was installed. The upstream Apache
license is retained at `vendor/LICENSE`.

The installed runtime used here is Python 3.12.14, Pydantic 2.14.0, and
cryptography 50.0.2. The two nonstdlib versions are pinned in `requirements.txt`.
No provider, model, wallet, RPC, Docker service, or credential is needed for this
local fixture.

## Public fixture signing material

The fixture uses deterministically derived **public test signing bytes** and a
literal public dummy API token. The source makes every byte reproducible. No API
server starts; no external service accepts these identities. The wrapper refuses
an execution mode other than `synthetic-local` and authority other than `none`.
The keys are intentionally unsuitable for production or independent evidence.

No `AuthorityEnvelope` is issued. Local execution assignments and work-acceptance
signatures enforce native development-tool boundaries inside this disposable
fixture; they confer no external authority. The controller, producer and verifier
are separate local roles under the same experimental control, not independent
organizations. Native backup truthfully reports that it contains private-key
material; the wrapper adds the fact that this material is public TEST ONLY.

The wrapper accepts only installed Python callbacks whose code file appears in
the explicit frozen `source_paths`. It does not execute code supplied by JSON
imports. Like the upstream `execute_tool` API, it relies on those installed
callbacks being reviewed pure application code. It is not an isolation boundary
for arbitrary Python or hostile plugins. Source bytes are rechecked before and
after each callback.

## Use the native runner

From the study directory, import:

```python
from integration.native_workflow import execute_stages
```

Call `execute_stages(output_dir, stages, mission_id=..., objective=...,
source_paths=[...], bindings={"execution_mode":"synthetic-local",
"authority":"none"})`. The output directory must be new; an earlier attempt is
never overwritten. Each stage is a dictionary with:

- `id`: unique identifier; the standard display IDs are listed below.
- `handler`: installed function `handler(inputs)` returning bounded JSON data.
- Optional `depends_on`: IDs of earlier stages; defaults to the immediately
  preceding stage.
- Optional `family` and `label`.
- Optional `accept`: a separately installed local function of the complete
  returned artifact. Without it, acceptance means structural work completion
  only and never asserts scientific success.

The `inputs` dictionary contains exact previously accepted artifacts, indexed by
stage ID. The scientific value is under `inputs[stage_id]["result"]`. The wrapper
also retains input and output commitments, measured callback and stage CPU/wall
time, declared invocation counts and native history.

Callback floats are encoded as explicit decimal strings in native records;
original raw scientific files remain authoritative for statistical analysis.
NaN/infinity and unsupported objects reject. Keep stage summaries small and link
large raw evidence by hash: upstream canonical objects and retained graph history
have a 2 MB limit. Numpy arrays/scalars should be explicitly converted by the
installed callback before returning.

| Display stage | Default native job family | Concrete obligation |
|---|---|---|
| `identify` | `constitution` | Bind the user problem, scope and inputs. |
| `out_learn` | `evidence` | Prepare admitted observations and assumptions. |
| `out_think` | `challenge` | Challenge the options and binding-constraint diagnosis. |
| `out_design` | `formation` | Construct, repair or retain the selected operator. |
| `out_strategise` | `admission` | Decide whether the local plan fits qualification and resource criteria. |
| `out_execute` | `verification` | Execute the bounded task and check the returned result. |
| `out_evolve` | `renewal` | Assess an actually dependent successor, or record a normal stop. |

These are explicit harness allocations, not claims that the display labels are
upstream synonyms. Upstream `compile_jobs` requires all seven lifecycle families
and rejects cycles, missing typed dependencies and self-acceptance. An application
can supply a different truthful mapping or more than one job per display stage.

Native `stage_calls` count invocations. They are not CPU instructions, detector
acquisitions or money. All callbacks, native transitions, source checks, local
acceptance, backup and restoration are included in the measured total, apart from
final receipt serialization and the caller's own work. Scientific CPU/scoring/
measurement costs must still be reconciled in the study ledger. Failed or
uncertain calls retain their reservations and native history; there is no retry
loop.

Native journals contain actual timestamps and measured timings, so their complete
byte hashes change across fresh executions. Each recorded run has its own exact
custody hash. Deterministic scientific result comparison must use the declared
semantic fields and retain timing variability separately.

## Minimal meaningful smoke

```bash
python3 -m integration.smoke_native --output /tmp/bloom-native-smoke-new
```

This runs seven trivial local callbacks solely to check the adapter, verifies
the real signed journal and real backup/restoration, then attempts dispatch from
the restored stopped state and requires rejection. Its results are explicitly
integration-smoke evidence, not scientific advantage measurements.

## Native structural records for a finished study

`adapter.py` creates genuine validated `MissionConstitution`, `WorldProgram`,
`PolicyProgram`, `CandidateReleaseManifest`, `ComparatorManifest`, `ProofProtocol`
and `ProofReceipt` objects using the same unchanged Alpha module. They are an
**unsigned local structural translation**. They are not inserted into the native
trust store, do not become active proof, and do not grant execution permission.

```bash
python3 -m integration.adapter export . results/summary.json results/native-records --metadata integration_metadata.json
python3 -m integration.adapter restore results/native-records/native_records.json . results/native-records/restored.json
```

The explicit metadata file requires `mission_id`, `objective`, `protocol_path`,
`source_paths`, at least two `comparators`, and actual `thresholds`. Optional fields
bind graph, policy, environment and artifact files, cost budgets, analysis and a
reported correctness verdict. Missing results default to `insufficient_evidence`
and zero asserted evaluation units. Example field shape:

```json
{
  "mission_id": "bloom-dependency-impact-v1",
  "objective": "Use the actual frozen study objective here.",
  "protocol_path": "protocol.json",
  "source_paths": ["experiment.py"],
  "graph_paths": ["protocol.json"],
  "policy_paths": ["protocol.json", "experiment.py"],
  "artifact_paths": ["results/raw.jsonl"],
  "comparators": [
    {"id":"reference","role":"incumbent","status":"measured","source_paths":["experiment.py"]},
    {"id":"expert","role":"specialist","status":"measured","source_paths":["experiment.py"]}
  ],
  "thresholds": [{"name":"exact-correctness","unit":"fraction","direction":"exact","threshold":"1","hard_gate":true}],
  "receipt": {"outcome":"insufficient_evidence","evaluation_units":0,"measurements":{}}
}
```

Replace those illustrative values with the actual study protocol; example names
are not empirical assertions. All evidence paths must resolve inside the study
directory. Exact raw bytes are hashed; floating result files are not silently
rewritten. The full publication ZIP must include every manifest path because the
structural JSON is an index, not a copy of all raw evidence.

The native wrapper's `frozen_at` is the **packaging time**. The original scientific
protocol hash and any supplied original freeze timestamp are retained separately.
This prevents post-study packaging from pretending that it was a pre-study
registration. Restore revalidates records, file hashes and runtime context,
remains stopped, empties active proof/grants, and requires authority revalidation.
Changed files are reported as failed revalidation rather than silently accepted.

## Four repositories and contracts

The Alpha native development path above is executed. Manager and Jobs Discovery
receivers accept only their current finite-campaign payloads, with zero currency
caps and no operational authority. An arbitrary new research task is not a
qualified native campaign merely because its JSON resembles that schema. Fleet
installed external execution is not provisioned in this fixture. The source audit
documents these real interfaces and their limitations.

`EVM_NOT_RUN.json` records the installed-module probe: Hardhat, ethers, solc,
OpenZeppelin and the required test plugins were unavailable. No dependencies were
installed and no contract execution was attempted. The audit maps all five
contracts to actual source and records the disposable upstream test paths.
MARK `bloom` performs the implemented Funding-to-Bloomed transition only; changed
Merkle plans need a fresh seed and explicit authority. No successor, revenue,
token price or profitable economy follows from that transition by itself.
