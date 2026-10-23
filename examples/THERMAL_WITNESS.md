# Witnessed thermal measurements: experimental workbench adapter

[Research prototype notice](../docs/DISCLAIMER_SNIPPET.md)

This is an additive fixed adapter for the **existing** SUCCESSOR workbench and its packaged native worker. It computes heat and downstream quantities from typed simulated measurement intervals. The source candidate executes through the released Python runtime and durable journal. It is not the completed AGI ALPHA product, a physically qualified instrument, or an operating Ascension enterprise.

The complete Ascension target and remaining owners are recorded in [the implementation map](../docs/agent/ASCENSION_IMPLEMENTATION_MAP_2026-10-22.md). The four-source snapshot there is **not a tested compatibility manifest**.

## Operate the source example

After the repository's documented setup, use its pinned Node 22.17.1 runtime. These modules use Node built-ins and the existing workbench source closure; they need no wallet or network service.

~~~sh
node examples/successor-workbench/thermal-witness-demo.mjs foundry > thermal-evidence.json
node examples/successor-workbench/thermal-witness-demo.mjs delivered-heat
node examples/successor-workbench/thermal-witness-demo.mjs heat-capacity
node examples/successor-workbench/thermal-witness-demo.mjs heat-recovery
node examples/successor-workbench/thermal-witness-demo.mjs --input measurement-input.json
node --test examples/successor-workbench/thermal-witness.test.mjs
~~~

The first command generates the fixed simulated acquisition, then passes **only observations** to the existing workbench and the fixed adapter. The output contains a local source descriptor and a regular workbench evidence pack. The source descriptor covers the actual nine-file native workbench closure, its manifest, the adapter, fixture generator, independent reference and demo. Every existing manifest member is checked before and after execution. This is a local source snapshot, not an installed-release attestation.

The other three examples are exact synthetic fixtures with distinct extra measurement requirements. They do not estimate the original research model's wall heat capacity or establish a physical recovery efficiency.

The optional input file uses the exact schema returned by `thermalExample()`. Integers express nanolitres, microkelvin and milliseconds; large energy values use decimal strings. Unknown fields, unsafe integers, accessors, sparse arrays, wrong versions, duplicate intervals, gaps and incomplete windows are rejected. The import limit reuses the workbench's 2 MB bound. The CLI opens a nonblocking read-only descriptor and requires a regular file; directories, named pipes and oversized files are rejected before parsing.

The repository-owned `native.mjs` installs the fixed adapter with `createWorkbench([thermalWitnessAdapter])` and exports the existing registry/example/validate/plan/run/inspect interface. The packaged native worker now exposes six families; the original five remain. The shared generator hashes the complete nine-source closure and regenerates the worker and browser artifacts. The existing browser still uses its original five-family registry; this increment does not advertise a deployed thermal UI. No arbitrary module-loading interface is added.

## The construction and the retained failure

In the retained Foundry mismatch, actual receiver flow is 92% of its command. The old calorimeter uses the command as though it were a flow measurement. Its 4.947712% agreement with the frozen prediction coexists with an 8.696402% error against the independent reference.

The new instrument interface takes a separate volume observation and a bound covering the **volume-weighted differential temperature over the whole interval**. It computes:

~~~text
heat in microjoules =
density in kg/m3 × specific heat in J/kg/K × volume in nanolitres
× differential temperature in microkelvin / 10^12
~~~

All production interval arithmetic uses BigInt. Products evaluate all endpoint combinations, including negative differential temperatures. Lower and upper energy limits are rounded outwards. The relative-error limit uses the worst distance from the estimate divided by the smallest possible absolute true heat; an interval including zero cannot establish relative accuracy.

The required `propertyModel` is `CONSTANT_WITHIN_INTERVAL` or `VARIABLE_OR_UNKNOWN`. Only the former can qualify: density and specific heat must be constant within each acquisition interval. The scalar property bands do not capture within-interval covariance with signed temperature. Variable or unknown properties remain unqualified; a future enthalpy integrator would need to account for that covariance explicitly.

A point sensor reading is insufficient unless its declared uncertainty also covers spatial coverage, temporal variation and correlation with flow. Merely giving two channels different names does not establish metrological or organizational independence. The current input mode is explicitly simulated.

The original failure remains `RETAINED_UNDETECTED_FAILURE`, with its exact published quantities. It is not replaced by the new conditional success. The historical runtime residual and true-error values remain distinct.

## Executed numerical result

A separately written four-state RK4 reference reproduces the original 180-second reset and 720-second pulse/recovery mission. Its fixed 1/32-second step uses 28,800 steps and 115,200 right-hand-side calls. Its true heat is evaluator-only.

For the reference mismatch:

| Quantity | Result |
| --- | ---: |
| Original independent heat | 5009.624457673767 J |
| Original commanded-flow calorimeter | 5445.281559253151 J |
| New imperfect-volume-witness estimate | 5035.816195 J |
| New lower heat bound | 4943.354615 J |
| New upper heat bound | 5129.056527 J |
| Conservative relative-error bound | 1.8862% |

The new volume meter is deliberately biased by +0.3% within a declared 1% bound. Differential temperature has +0.002 K bias within a declared +/-0.005 K calibration bound. A conservative temporal-integration allowance and integer quantization are included. These are simulated calibration assumptions, not a physical calibration certificate.

The independent reference and production adapter use different calculations: RK4 integrates the physical model's heat state; the adapter multiplies measured volume and bounded temperature using exact integer arithmetic. The worker never receives hidden actuator multipliers, true parameters or reference heat. Six additional public nominal/mismatch/history combinations check interval containment. These are known public numerical cases, not unseen physical trials.

A wider +/-0.05 K differential-temperature uncertainty fails the 5% useful-accuracy requirement. Missing volume observations, command-derived observations, shared source labels, unknown coverage, exhausted work, zero denominators and impossible energy boundaries remain unqualified. A conventional instrument with identical measurements ties the result.

## Three downstream mission families

| Mission | Reused capability | Additional requirement | Result |
| --- | --- | --- | --- |
| Delivered heat | Whole-flow witnessed calorimetry | Complete window, material-property and calibration bounds | Signed heat interval and useful-heat target decision |
| Material heat capacity | Measured delivered heat | Independent sample temperature-rise, loss and container-storage bounds; one-sample energy model | Heat-capacity interval; a zero rise or uncertain energy balance remains inconclusive |
| Process heat recovery | Measured recovered heat | Independent total input-energy bound and separately bounded stored-energy release | Unclamped recovery-ratio interval and target decision |

Downstream ratios compute all four signed numerator/positive-denominator endpoint combinations, preserving ordered bounds even for rejected negative-energy cases. A denominator interval containing zero has null finite bounds. `ENERGY_BOUNDARY_NOT_RESOLVED` means uncertainty includes both feasible and infeasible balances; `ENERGY_BOUNDARY_INCONSISTENT` means the modeled bounds exclude every feasible balance. Both prevent qualification.

Downstream uncertainty is evaluated independently of calorimeter precision. A precise heat estimate does not automatically qualify an imprecise capacity or recovery estimate. The existing-workbench integration is designed to give each changed mission a distinct semantic commitment; the actual Node integration test for this behavior passes. Hosted acceptance for a later source head remains separately required. No result inherits capability acceptance or authority.

These are computed mission families around one measurement capability. The thermal enterprise successor lifecycle and independent promotion still require the existing enterprise integration path. The separate [compounding experiment](../docs/agent/COMPOUNDING_CAPABILITIES.md) actually exercises the merged mathematical enterprise controller; its accepted AST inventory cannot be replaced by attaching thermal JSON.

## Execution, recovery and evidence

One work unit is one bounded interval reduction. Up to 960 intervals and a one-hour window are admitted. Validation and fixed-size final arithmetic are separately bounded by this schema; the count is not a claim about CPU instructions or economic cost. The independent fixture's fixed simulation work is separate acquisition/evaluator work and must be included in any future total-cost ledger.

Every reduction calls the existing checkpoint. Cancellation propagates without producing accepted evidence. Budget exhaustion returns explicit partial coverage and `EXHAUSTED`; it cannot masquerade as a completed negative experiment. A private input snapshot prevents later caller mutation from changing an in-progress computation.

The existing workbench supplies source and mission commitments, artifact hashes, zero-funded job compilation, time/cancellation controls and inert import. Reloading an exported pack verifies its integrity and restores **no authority or proof**. This is evidence-pack recovery. The Python runtime additionally persists signed run records, verifies exact request identity, retains local review, and exercises explicit interruption/resume. Completed records remain reusable under schema-compatible source upgrades without refreezing or rerunning them; unfinished work refuses changed executable-source identity before consuming another attempt. These tests do not establish payment recovery, independent review, or the held enterprise facade.

The worker's most favorable decision is `CONDITIONAL_BOUNDS_MET`. Its proposal still sets `acceptedCapability:false`. Independent acceptance remains an external obligation. The workbench retains `admission:HOLD`, `independentProof:false` and `settlement:NOT_CONNECTED`.

## Native operation and evidence

This registration is in the source candidate, not the historical v1.38.0 package. After the repository setup (Python operator dependencies from `requirements-agent.lock` and Node 22.17.1), run:

~~~sh
python -m alpha_factory_v1.core.runtime.cli successor-work registry
python -m alpha_factory_v1.core.runtime.cli successor-work example thermal-witness --output thermal-mission.json
python -m alpha_factory_v1.core.runtime.cli --home ./thermal-operator successor-work run thermal-mission.json --run-id 7dd5a437-9c44-468c-8ea6-8d68d402d700 --output thermal-run
python -m alpha_factory_v1.core.runtime.cli --home ./thermal-operator successor-work show 7dd5a437-9c44-468c-8ea6-8d68d402d700
~~~

Choose new mission/output paths; existing files are preserved. `successor-work control RUN_ID --state paused|stopped|retired` uses the existing controls. An interrupted run requires explicit `--resume` and a fresh output directory; stopped or retired work cannot resume. The original three-attempt limit remains. The exact-result `review` command records a **local** operator decision with `independent:false`; it creates no council approval or capability/financial authority. `export` preserves the result and receipt.

## Test status and integration boundary

The original portable 51-case result remains [historical V8 evidence](../docs/agent/thermal-witness-portable-execution.json). On public head175d8a5, the actual hosted mission workflow passed17 workbench groups with no failures/skips; [run39863200779](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/39863200779) is a different source boundary from this native candidate.

After the workspace recovered, pinned Node22.17.1 and Python3.12.14 executed the native candidate: **19 Node groups and26 Python cases passed**, including all three quantities, actual packaged-worker process invocation, canonical transport, inert imports, mission identities, filesystem refusal, signed journal idempotency, exact-result local review, interruption/resume, source-change refusal and the three-attempt bound. Independent source review and generator/cache byte reconciliation are retained in [the evidence directory](../evidence/thermal-witness-20261022/README.md). Initial sandbox process refusals and a test expecting the wrong rejection layer are retained alongside corrected results. Required hosted/release checks are not replaced by local tests.

Twelve predeclared additional numerical cases also ran as actual Node child processes against unchanged public source175d8a5. All twelve passed the six frozen criteria: maximum conservative error bound1.9398%, maximum observed reference error1.0872567589%. These are public bias-corner cases across two fixed regimes, not unseen physical trials or a broad dynamics benchmark. The 180-second reset almost erases the tested initial-history differences. The exact source bundle, original protocol, failed sandbox receipt and approved process receipts are [retained together](../evidence/thermal-witness-20261022/heldout-node/README.md).

No workflow, dependency, permission, contract, credential or live provider was changed. Actual enterprise-facade integration, independent Fleet acceptance, real-source local-EVM lifecycle, tested four-package installation, thermal browser placement and software release qualification remain outstanding. PR#4863's explicit review restriction and the current publication owners remain respected. Native execution and durable journal recovery are implemented and exercised; that does not clear the separate full-product obligations.

## Scientific provenance

- [Foundry v2 study and exact public assets](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/tag/study-foundry-v2-2026-10-22-r1).
- [Published manuscript source](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/19a13e4440da93668dd42c537ac43a011cd2a0c2/docs/papers/autonomous-enterprises-foundry-v2.tex).
- [Retained study data embedded in the research experience](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/0b6630a15c8d2765b5c242856a4525e5490bdb83/docs/reports/thermal-fluid-foundry-v2/experience.html).
- [Existing workbench extension interface](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/61532fb82621a065e668fd11e57289dcfb65c67b/examples/successor-workbench/engine.mjs).
