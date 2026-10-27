# Existing Alpha workbench: numerical callback bridge

This folder connects a fixed Python numerical callback to the **unchanged released Alpha v1.42.0**
`createWorkbench` extension. It does not implement or install a competing scheduler. The study's finite,
predeclared foreground recipe supplies the sequence; every mission is dispatched and inspected by the
existing workbench. An imported mission cannot supply Python/JavaScript code or select an executable.

The 9 source files under `vendor/` have exact byte identities in `vendor/WORKBENCH_MANIFEST.json`.
The eight-file execution closure is the original released c352bad0 closure; `mission-store.mjs` is the
existing current-main browser history module. Each bridge process verifies all nine file identities before
accepting a request. Source/license headers are preserved. The pinned Jobs compiler emits unfunded drafts;
it does not call a Jobs service, contract, wallet or market.

```python
from runtime.workbench_client import WorkbenchClient

def fixed_callback(inputs):
    return {"valid": True, "qualified": True,
            "summary": "Result checked within the declared numerical scope.",
            "value": sum(inputs["values"])}

with WorkbenchClient() as client:
    result = client.run("example-1", "Compute a checked result", {"values": [1.5, 2.5]},
                        fixed_callback, source_hash)
    pack = result["pack"]
```

`source_hash` is the enclosing study's verified frozen source identity. A 64-digit string is structurally
required; the caller must verify it against the actual complete source manifest before launch. The workbench
cannot independently discover whether an arbitrary caller supplied an honest source label.

The bridge is a persistent Node subprocess, so the Python callback does not restart for every mission:

1. Python submits exact task JSON to the workbench.
2. Original `createWorkbench` validates/commits the mission and builds its bounded Jobs draft.
3. The installed adapter's `execute` callback asks Python to perform the fixed computation.
4. Python executes the callback once; callback failure becomes an explicit refused report.
5. Original workbench binds the result artifact, constructs its Chronicle/economic envelope and validates
   the pack. The bridge then performs an additional read-only `inspectPack` check.

Inputs and the numerical report are encoded as exact JSON **strings** within the upstream integer-only
canonical envelope. Floating-point numbers therefore retain explicit JSON bytes; they are not silently rounded
to pass the original parser. Task payload is at most 120,000 bytes and result report at most 190,000 bytes.
The mandatory report fields are `valid`, `qualified` and `summary`; additional finite JSON fields retain
the useful result, independent checker observations, costs and provenance.

## Measurement and stopping

Each return separates bridge wall time, callback wall/process CPU time and Node process CPU microseconds.
`startup_wall_ms` belongs to the enclosing process/experiment cost. Process CPU includes Python's numerical
native-library CPU, while Node CPU belongs to the workbench and transport; do not add wall time to CPU time.
The wrapper does not equate either with abstract work or money. It cannot measure operator authoring effort.
Measure source loading, input generation, ledger/history writes and the complete research run at their own
enclosing boundaries to avoid omitted costs or double counting.

`cancelled=` is checked before and after the fixed callback. Cancellation after pure computation refuses
output admission and retains callback cost in the raised `WorkbenchError.receipt`. The callback is trusted
bounded developer code: its own resource/deadline enforcement remains required. This bridge is not a sandbox
for untrusted Python. Original workbench enforces its 60-second checked phase bound; Python's transport timeout
is 65 seconds. It cannot interrupt Python code currently executing synchronously in the caller.

Process-local duplicate request IDs are refused. **Durable** idempotency, two-account resource reservations,
source/dependency binding, STOP state, retries and restore fencing belong to the surrounding study's reviewed
custody layer. No claim that the process-local ID set survives a restart is made. `inspect(pack)` is read-only
and neither reruns computation nor inherits current proof or authority.

## Scope

This is local source execution, not the installed native `CampaignOperation`, a daemon, an authenticated browser
connection or a production service. The upstream pack keeps `admission:HOLD`, `independentProof:false`, empty
authority, and `settlement:NOT_CONNECTED`. Separate checker results and research product-admission decisions
do not alter that upstream institutional status. Closing the foreground processes ends computation.

The existing browser `mission-store.mjs` offers IndexedDB CAS history with 12 records and a 2 MB per-record
cap. It is available to the browser companion without changing upstream source. Its persistence conveys no
operational authority. The browser must disclose its local mode and separately label any recorded results.

## Verification

From the project root:

```sh
python3 runtime/test_bridge.py
```

`development_bridge_tests.json` records ten source-bound development checks: actual callback dispatch,
empty proof/authority, read-only inspection, invalid receipt, duplicate request, invalid source identity,
callback failure, STOP before work, STOP after work with retained cost, and a new explicit request after
cancellation. These checks do not qualify the numerical study or prove independent institutional review.
