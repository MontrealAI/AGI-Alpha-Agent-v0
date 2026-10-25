# Fixed Strategy executor transport

This is an additive engineering contribution for the existing Strategy Succession
owner. It does not change the frozen experiment, original Harness, Fleet,
publication ownership or production authority. It is not repository maintenance
or a general desktop executor.

`strategy_executor.py` reuses the actual Alpha runtime `Journal`, `ActionGateway`
and `RequestBoundary`. Its narrow application exposes only the fixed strategy
routes and optional three operator-installed static assets. It does not weaken
CORS or expose the unrelated runtime operations.

## Operator interface

Import `SourceFile`, `Limits`, `ExecutorPolicy`, `create_strategy_app`. Supply the
existing configured `Journal`, the reviewed fixed worker instance, and a policy.
Do not initialize another journal automatically or create a credential in this
transport. `create_strategy_app` reads the existing journal's `api.token`.

`SourceFile(label, path, sha256)` lists every operator-installed worker/scientific
source whose identity is part of approval. Paths stay local. The public envelope
shows only their combined hash. Missing, linked, changed or oversized files fail
closed. These checks do not sandbox code or establish review eligibility.

`Limits(service_work, improvement_work, native_calls, native_solve_seconds)` has
separate service and construction accounts. `ExecutorPolicy` maps the installed
methods to per-plan limits and specifies aggregate limits, maximum request count,
approval lifetime, request lease and `allow_native` (false by default). The
browser cannot provide these settings. A changed policy is refused against an
existing transport journal record; a legitimate reviewed change needs its own
explicit operator migration/installation decision.

Approval also binds the existing home/database filesystem incarnation through a
nonsecret digest. A copied/restored journal in another home does not inherit
execution approval. The private backup still verifies as historical evidence;
the transport refuses to operate its inherited grants. This creates no new key
or persistent credential.

Supported method names are `run-mission`, `construct` and `run-journey`.
`run-mission` cannot spend construction units; `construct` cannot spend service
units. `run-journey` reserves both accounts in one transaction. It may execute its
fixed successive phases after one approval without additional browser prompts.

The worker implements:

```python
execute(method, payload, limits, checkpoint) -> {
    "result": {...},
    "costs": {"service_work": 0, "improvement_work": 0, "native_calls": 0,
              "native_solve_seconds": 0.0, "unknown_costs": ["human effort"]},
    "source_hash": limits["source_hash"], "verified": True
}
```

Worker-facing limits also contain `wall_seconds`, `allow_native` and
`source_hash`. The source hash covers the operator-listed implementation files;
the original scientific freeze identity should be reported separately inside the
result. The worker must validate its exact fixed input schema. Browser input is
data; it cannot select a command, module, host path, executable or endpoint.

Call `checkpoint()` before every bounded phase. Call
`checkpoint(native_calls=1, native_solve_seconds=2)` before each fixed two-second native attempt and pass exact known work
increments as they become available. Each increment is retained before the next
operation. Final cumulative counters must cover these increments and remain
within the approved caps. The legacy field `native_solve_seconds` means charged
solve allowance seconds, including failed or uncertain attempts. Actual observed
solver time, process CPU and wrapper wall time remain separately labelled
telemetry. Work units are not money, CPU or revenue.

After an actually checked phase, the fixed worker may call
`checkpoint(receipt=partial, **increments)` before proceeding. The optional
partial has exactly `phase_index` (0–2), `receipt_hash`, `task`, `result`,
`checker`, and `selectedmethod`. Its original receipt hash binds the fixed
scientific source and current executor source, with empty proof/authority lists.
The transport checks its integer-only canonical bytes and adds a separate digest
binding the current plan and local policy. At most three ordered receipts fit
within the installed output-byte cap, and they commit to the signed journal
before the callback acknowledges them. They survive STOP, exceptions, restart,
reconciliation and export even when the overall request remains unknown.

An exact duplicate partial does not append another artifact. It must not repeat
cost increments; that combination is refused atomically. Different contents at
an existing phase index, out-of-order phases and relabelling an existing
receipt/task identity as a new phase are refused. Each new increment
is recorded once; the wrapper must not automatically resend acknowledged
increments. Partial results never grant automatic continuation or authority.

The callback must itself impose finite process/time bounds and terminate its
child process on checkpoint failure. The transport cannot forcibly preempt an
arbitrary in-process Python callback. Only reviewed fixed code is permitted;
there is no generated-code, host-shell or imported-code execution API.

## Browser protocol

Every API call uses `Authorization: Bearer ...` with the existing operator token.
Keep it only in browser memory, clear the credential input after connection, and
never put it in URLs, HTML, browser storage, logs or exports. Mutation requests
must be same-origin and have unambiguous bounded Content-Length framing.

| Request | JSON fields | Response |
| --- | --- | --- |
| GET `/api/strategy-executor/status` | none | State, exact plans, observed usage, aggregate reserved/spent/total, source availability, identity, record digest |
| POST `/api/strategy-executor/prepare` | `method`, `input`, `request_id` | Exact plan with `plan_id`, `plan_digest`, caps, source, identity, expiry |
| POST `/api/strategy-executor/approve` | `plan_id`, `plan_digest` | Exact locally approved plan |
| POST `/api/strategy-executor/run` | `plan_id`, `plan_digest` | Synchronous committed plan and outcome; poll status concurrently |
| POST `/api/strategy-executor/control` | `state`: `ready`, `paused` or `stopped` | Current state |
| POST `/api/strategy-executor/reconcile` | `plan_id`, current status `record_digest`, `note` | Inspected uncertain plan, permanently non-replayable |
| GET `/api/strategy-executor/export/{plan_id}` | none | Signed portable evidence; no credential or active grant |

The UI should describe local execution, disconnected/paused/stopped states,
approval expiry and unknown outcomes plainly. `completed` means the fixed worker
verification passed and the result was committed. A known verification failure is
retained as `rejected`, with its measured costs and no replay. Local attribution is
not independent verification or production admission.

## Stop, recovery and costs

Only one request executes per process/journal. Journal transactions also refuse
a second active request across service instances. A plan reserves its complete
caps before action dispatch. Completion commits the outcome hash and actual
separate counters before acknowledging the HTTP response. Duplicate delivery of
the same completed input returns that committed result, without executing again.
Reusing an idempotency identity for changed inputs is refused.
The existing journal-wide pause is checked at preparation, approval, reservation,
every worker checkpoint and completion, in addition to the strategy-specific
controls.

An exception, STOP, expired lease or lost process before commit leaves an unknown
outcome with its full cap reservations retained. A stale `running` record is not
treated as a safe failure. Inspect status/evidence, then reconcile using the
exact current record digest and an operator note. Reconciliation does not refund
unknown work or reopen the plan. New work requires a fresh plan and explicit
approval within remaining protected capacity. STOP is permanent for this
installed envelope. Pause fences active work at its next bounded checkpoint;
resume does not replay that interrupted request.

Closing the browser does not stop an already running local process. That process
may finish its explicitly approved finite request. Closing/stopping the local
executor process prevents further progress; no unattended service or scheduler
is installed by this contribution.

Run the separate boundary tests with Alpha on `PYTHONPATH`:

```sh
PYTHONPATH=/path/to/alpha:/path/to/transport python -m pytest -q -c /dev/null /path/to/transport/test_strategy_executor.py
```

These are engineering tests. They do not execute or alter the frozen scientific
confirmation inputs, results or acceptance criteria.
