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
