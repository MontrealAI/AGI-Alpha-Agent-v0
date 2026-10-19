# SUCCESSOR Ω: bounded Computer Use

The optional native adapter lets a configured model inspect screenshots and propose mouse and keyboard
actions in a disposable Chromium browser. It supports current OpenAI Responses `computer` calls and a
substitutable OpenAI-compatible vision/JSON supplier. The five default local work adapters need neither.

This implementation supports a browser in a Linux Docker container. Full desktop application control,
personal browser profiles, logins, arbitrary shell/code execution, uploads, payments and message sending
are outside this adapter's scope. There is no host-browser fallback when isolation is missing.

## Prepare the runtime

The operator needs Docker and a reviewed, locally available image built from an immutable base digest.
`examples/successor-workbench/computer/Dockerfile` uses the separate hash-locked Playwright environment;
it does not change the agent's dependencies. Resolve and record the platform-specific base digest before
building. These commands are setup operations, not automatic downloads performed by a model:

```bash
docker pull mcr.microsoft.com/playwright/python:v1.63.0-noble
docker image inspect mcr.microsoft.com/playwright/python:v1.63.0-noble --format '{{index .RepoDigests 0}}'
docker build --build-arg BASE_IMAGE=REVIEWED_REPOSITORY_AT_SHA256 -f examples/successor-workbench/computer/Dockerfile -t successor-computer .
docker image inspect successor-computer --format '{{.Id}}'
```

Retain the resulting `sha256:...` image ID with the source and dependency inventory. The native runtime
requires an immutable image reference, uses `--pull=never`, mounts no host directory, exposes no port,
and gives the container no network. It limits CPU, memory, process count and temporary storage, runs as
a non-root user, drops capabilities and prevents privilege escalation. Containerization is not an
absolute guarantee against kernel or browser vulnerabilities; shared-host threat models need a VM too.

## Prepare a task and provider

Start from `examples/successor-workbench/computer/task.json`. It contains a small local report editor,
the user's goal, declared input rights, review capacity, exact optional GET URLs and finite action/turn/time
limits. Model, provider endpoint and image are operator configuration, never page-controlled settings.

Set the provider key through your normal secret-management process. Do not put it in a task or command-line
argument. Choose an available model for your account explicitly; model access and charges vary by provider.
Configure provider-side spending limits before paid use. Turn/output ceilings are not a measured dollar budget.

```bash
alpha-agent successor-computer prepare examples/successor-workbench/computer/task.json --image IMAGE_SHA256 --model YOUR_COMPUTER_MODEL
alpha-agent --home operator successor-computer run examples/successor-workbench/computer/task.json --image IMAGE_SHA256 --model YOUR_COMPUTER_MODEL --permit PREPARED_COMMITMENT --output computer-result
```

The preparation performs no model call. Execution requires the exact displayed commitment, which binds
the task, rights, limits, provider configuration, installed worker source and image. Substitution changes
that commitment. A local compatible supplier can use `--provider vision-json --base-url http://127.0.0.1:PORT/v1
--model MODEL`; remote endpoints require HTTPS and the named `--key-env` credential. The supplier must
support image input and bounded JSON output. Compatibility is tested per supplier, never assumed from its name.

## Choose a model for the work

Use current frontier capability for a consequential task, then qualify the actual combination of model,
tools and environment. The model is a native operator setting; selecting a flagship opportunity does not
select a provider, incur a charge or connect an additional executor.

| Work | Current documented option | Selection basis |
| --- | --- | --- |
| Difficult scientific reasoning and mathematical exploration | `gpt-6-astra` | OpenAI recommends Astra for its hardest scientific research tasks |
| Source inspection, software reasoning and screenshot-based Computer Use | `gpt-6.1-sol`, or `gpt-6-astra` when task quality warrants it | Compare accepted output and full task cost, rather than model price alone |
| Another available vision/JSON supplier | Explicitly tested compatible model | Establish image, schema and task compatibility before operational use |

These options follow the current [GPT-6.1 Sol documentation](https://openai.com/index/introducing-gpt-6-1-sol/)
and [GPT-6 Astra documentation](https://openai.com/index/gpt-6-astra/), not a universal model ranking.
The Responses integration uses the
[current structured Computer Use interface](https://developers.openai.com/api/docs/guides/tools-computer-use).
Provider access, behavior and prices can change. Record the actual model identity, configuration and evidence
for each authorized trial. The CLI does not automatically switch models or expose a reasoning-effort setting.

Frontier research demonstrates a broader opportunity than this browser adapter alone implements.
OpenAI's [October mathematical release](https://openai.com/index/sharing-ai-progress-in-mathematics/)
and [supporting repository](https://github.com/openai/math) describe results from an unreleased internal model,
with differing verification status. Those results are not evidence that a selected public model or this runtime
has solved the same problems. A mathematical candidate needs appropriate expert and proof-tool checks;
a software candidate needs actual execution and validation before either can be described as established.

## Continue a flagship project

The flagship can export an inert `successor-alpha-computer-handoff/v1` mission for this same native adapter.
It retains the exact serialized project and its SHA-256, the flagship source identity, declared input rights,
the bounded computer task, an explicitly unverified value hypothesis and a strategy plan. Level 3 records at least
two hypotheses, a proposed combination and measurable success criteria. Level 4 records an alternative formulation. The
operator chooses `baseline`, `combine` or `reframe`; these descriptions remain hypotheses until actual
work and review support a result. A reframing does not expand the task's permissions or change its goal
without a new, explicitly reviewed handoff.

The default flagship mission reads the public Computer Use runtime at
[released v1.34.0](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/70dac8e5ce739978f5cd96d0fc190b6ebfcdf8d7/alpha_factory_v1/core/runtime/successor/computer.py).
It asks for an implementable improvement to redundant work, latency or operating cost, preserving task limits,
stop behavior and usage accounting. The visible deliverable is a source-linked patch proposal or a justified
decision to retain the design, plus a reproducible validation plan. Source inspection is performed in a bounded
reading pane; the work-product editor remains available when switching sources. The runtime does not execute
the proposed patch, run its benchmarks or establish savings. A research mission similarly delivers a concrete
mechanism and falsifiable experiment; the mathematics lane delivers a candidate argument, proof outline or
explicit unresolved gap. Supply relevant primary sources before asking for a literature-grounded conclusion.

For Level 3, compare genuinely different strategies and preserve unsuccessful attempts. For Level 4, ask whether
a different representation or workflow removes unnecessary work while preserving the required useful outcome.
Changing the acceptance contract starts a different comparison. Code execution, performance measurement and
formal proof checking need separately connected and qualified tools; preparing their plan does not run them.

Use the exported mission file in the existing commands:

```bash
alpha-agent successor-computer prepare successor-computer-handoff.json --image IMAGE_SHA256 --model YOUR_COMPUTER_MODEL
alpha-agent --home operator successor-computer run successor-computer-handoff.json --image IMAGE_SHA256 --model YOUR_COMPUTER_MODEL --permit PREPARED_COMMITMENT --output computer-result
```

Project bytes, strategy choices and source identity are bound into the existing task/provider/image permit
through `digest('computer-handoff', handoff)` as its execution context. Changing any of them requires a new
permit. Each explicitly prepared attempt has a fresh UUID, allowing separately authorized strategy/model
comparisons to retain distinct history. The runtime never creates or retries an attempt automatically.
The page supplies neither a provider credential nor an image, and importing or preparing a mission
performs no model call. The native parser checks project root fields, identity, size, history bounds and exact
bytes; the flagship's existing project validator checks the full catalog-cycle semantics. Native parsing does
not independently qualify project history or execute anything contained in that history.

After execution, `computer-result/computer-return.json` carries the project binding, observed provider/model,
image and worker identity, existing receipt and signature, and final visible text when available. Return this
file to the flagship to review the work alongside the same project. Screenshots remain separate files named
and hashed in the receipt; retain the complete output directory for visual review. An interrupted run also
produces a return when its native receipt is available, preserving reserved effects and unknown costs.
Importing that return does not establish signer trust, independent review, payment or settlement. Verify the
signed receipt against a separately trusted source key and review the actual artifacts before accepting work.

The handoff and return schemas use sorted compact UTF-8 JSON commitments. `projectSha256` hashes the exact
`projectRaw` UTF-8 bytes; `handoffSha256` hashes the canonical handoff. Tasks in a handoff include every
`ComputerTask` field and `schema_version: 1`, including defaults, to preserve cross-language commitment bytes.
Strategy text is bounded: original goal 2,000 characters, two to six hypotheses of 500 characters each,
combination and reframing 1,000 characters each, and one to six success criteria of 500 characters each.
The actual executable task goal remains subject to its separate 4,000-character limit.

OpenAI's [current Computer Use guide](https://developers.openai.com/api/docs/guides/tools-computer-use)
documents ordered `computer_call.actions` and screenshot returns using `computer_call_output` with
`computer_screenshot`. This adapter uses that structured path and rejects unsupported tool calls.
It preserves Responses reasoning continuation data only in process memory, requests `store=false`, and
does not export it. Provider-side data handling remains subject to the chosen service's policies.

## Execution and security boundary

The model receives the goal and screenshots, never host credentials, wallet keys, profiles, filesystem
mounts or the Docker socket. Screen/document text is untrusted. Every proposed action must pass the
fixed primitive schema, coordinates, key restrictions and remaining aggregate action budget. No model-
supplied JavaScript, shell or Python is evaluated. Safety-check requests stop for operator review;
the runtime never automatically acknowledges them.

The browser cannot reach the network directly. A parent read broker permits only exact operator-listed
HTTPS URLs with GET/HEAD, resolves only public IPs, pins the chosen IP for the TLS connection, and checks
the original hostname's certificate. It never forwards page cookies, authorization headers or request bodies.
Redirects, private IPs, additional query strings, writes, WebSockets and service workers are refused.
This permits bounded public-document workflows without creating an unrestricted browsing proxy.

Before each billed call and UI action, the private signed journal reserves a unit and retains its intent.
The operator/global stop and deadline are checked between bounded calls and immediately before actions.
An in-flight provider/network request may finish during its timeout; its reservation is not refunded.
Unknown charges or effects remain unknown. Requests never automatically retry. Screenshots and final
visible text are retained separately; a model's completion message remains an unverified claim for review.

For already commissioned institutions, `action_gateway(computer, action, session_commitment)` binds one
specific action to `ActionRequest.context_digest = digest('computer-action', {session, action})` and one
`computer_actions` unit. Use the existing `SuccessorStore.dispatch_action/execute_action` with genuine
current proof and grants. No new authority type or bypass is introduced. The standalone CLI records an
explicit local operator task; it does not claim institutional production permission.

## Stop, recovery and verification

`computer-result/run.json` is written before launching the worker. It gives the run ID even if interrupted:

```bash
alpha-agent --home operator successor-computer show RUN_ID
alpha-agent --home operator successor-computer stop RUN_ID
alpha-agent successor-work verify-receipt computer-result/signed-receipt.json --source-key TRUSTED_PUBLIC_KEY_HEX
```

There is deliberately no resume/replay command for effectful computer sessions. Inspect all screenshots,
the signed receipt and reserved-but-unobserved actions; reconcile the target before authorizing a new task.
The same task/provider/image commitment cannot open a second session until the operator records
`successor-computer reconcile RUN_ID --record-digest CURRENT_RECORD_DIGEST --note "Observed outcome and reconciliation"`.
This records the operator's judgment without refunding reservations or asserting independent proof.
Container removal is verified. Failed cleanup quarantines the session and must be resolved by the operator.
Exports carry observations and local attribution, no credentials, active grants or inherited trust.

## Qualification record

Control tests use explicitly labeled supplier/actuator doubles to test bounds, refusals, substitution and
unknown outcomes. The separate real-container test types into a real page and checks screenshots and
visible output; its scripted advice does **not** qualify a live model. Set `SUCCESSOR_COMPUTER_IMAGE` to
the reviewed image to run it. Live provider qualification requires an authorized credential, model ID,
provider request/usage evidence, screenshots, artifact review and recorded costs. Those checks must not
be replaced by a fixture or described as completed when credentials are unavailable.

The proposed $40 trillion/year opportunity is the owner's estimate. It is not a measured result or an
independently sourced market claim in this release.

## Provider usage and elapsed evidence

Each HTTP request attempt is recorded before network I/O. Completed provider
responses may supply bounded integer token counts, retained as
`PROVIDER_REPORTED`; absent or malformed usage remains `UNKNOWN`. A timed-out
request is never assumed free and is not retried automatically. The receipt
keeps billing `UNKNOWN` and per-attempt cost `null`: token observations are
not an invoice, a dollar budget, or evidence of economic benefit. Total
`elapsed_milliseconds` measures the local session through cleanup. Human
review time remains separately supplied rather than inferred from runtime.

The Responses wire contract was checked on 2026-10-18 against the
[official computer-use guide](https://developers.openai.com/api/docs/guides/tools-computer-use).
The adapter uses the current `computer` tool and action arrays, matches each
`computer_call_output` to its call ID, and retains encrypted reasoning in
stateless history (`store: false`). Unsupported tools and pending safety
checks stop for operator review. The alternate vision-JSON supplier has a
different contract; these modes do not imply arbitrary provider compatibility.
An empty, reasoning-only, refusal-only or commentary-only response cannot complete a session. Completion
requires a nonblank final text message, and its content still remains an unverified model claim.

A real Chromium laboratory test with scripted provider-shaped responses is
useful protocol evidence, but cannot establish live-model correctness or
production Docker isolation. Those require their own exact-source trials.
