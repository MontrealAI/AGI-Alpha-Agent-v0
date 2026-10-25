# AGI ALPHA · Strategy Succession Companion

**Plan a release. Check the result. Keep a method only when its declared benefit repays its costs.**

This is a finite research adapter over the released AGI ALPHA 1.42.0 `createWorkbench(adapters)` seam. The eight vendored upstream modules are unmodified. It is not an installed agent service, a production runtime update, a wallet, or a physical execution system.

The useful output is a crew-constrained schedule with prerequisites, a capacity calendar, releases and an optional locked prefix after a disruption. A separate checker verifies every delivered result. A deadline miss can still be a valid feasible schedule; it does not count as a deadline-qualified output. Optimality is claimed only when the schedule meets the independently recomputed registered lower bound, or is separately attributed to the native exact solver's specified objective.

## Requirements

- Node.js **24.22.1**; only built-in modules are used.
- Python **3.12.14**; the independent checker uses only the standard library.
- For the optional native MILP comparison: NumPy **2.4.6**, SciPy **1.17.0**. The native solver is not needed by the browser or the standard mission stream.

The complete package also includes `../review/check.py`, `../protocol/MAIN_PROTOCOL.json`, the top-level freeze verifier, browser files and the source manifests. Keep their relative paths.

## Start a useful bounded run

From the complete package's root:

```bash
node companion/run.mjs --out my-release-run
```

The default is a six-mission synthetic demonstration: two ordinary plans, two tighter plans and two disruption repairs. It starts once and selects the remaining permitted phases without additional prompts. All stage and total budgets remain finite. The default selective gate can refuse every proposed strategy; that is a valid result.

The output directory contains the configuration, events, raw results, workbench packs, an atomic checkpoint, a separate monotone recovery guard and a concise summary. A directory with an existing checkpoint is never silently overwritten.

For the explicitly separate construction diagnostic:

```bash
node companion/run.mjs --diagnostic --out construction-diagnostic
```

This mode permits correctness-qualified methods to be retained for research even if their economic gate says to hold. Its five-million-unit ceiling does not fund production action or financial settlement. The output labels correctness-only retention separately from net-benefit admission.

## Stop and recover

The browser exposes STOP. The CLI provides a reproducible bounded interruption:

```bash
node companion/run.mjs --out interrupted-run --stop-after 1
node companion/run.mjs --out interrupted-run --resume
```

Recovery independently rechecks saved accepted schedules, verifies source/configuration identity, and consults the monotone guard. It imports no current proof or authority. If a process died after a durable execution intent but before a measured completion, its entire reserved work ceiling is charged as uncertain cost. This is conservative accepted-effect idempotence, not a claim of exactly-once CPU execution.

The Node process performs work while it is running. A saved checkpoint does not execute itself. Browser computation stops when its tab/process stops; closing a tab does not leave a hosted agent running.

## Reproduce the registered study

The study requires the exact source/independent-checker freeze and a new output directory:

```bash
python3 scripts/freeze_study.py
node companion/experiment.mjs --confirm --out results/reproduction-01
```

The launcher verifies every frozen scientific source before materializing inputs, including the independently authored Python checker. It creates each input configuration once, rejects cross-split seed or semantic-input overlap, and reuses those exact inputs across arms. The finite launch runs all registered streams, budget sensitivities, diagnostic ancestry treatments and the preselected native-solver reference subset. It writes `SUMMARY.json`, `COST_BREAKDOWN.json`, `DIAGNOSTIC_SUMMARY.json`, `ARM_RESULTS.csv`, compressed raw results/packs and every individual checkpoint.

**Do not run `bind-source.mjs` on a frozen publication to make changed code pass.** A changed implementation requires a new explicit research namespace and a newly declared protocol. `bind-source.mjs` is a development/freeze preparation tool, not a reproduction repair command.

Before the original freeze, the driver was exercised using the disjoint public development namespaces only:

```bash
node companion/experiment.mjs --development-smoke --out development/another-driver-smoke
```

A development smoke is not confirmation. Its small sample and diagnostic outputs must not be substituted for the registered main results. The supplied-input overlap guard may refuse replaying a prior development smoke into the same exposed namespace; use the preserved smoke evidence to inspect the original check.

## Files and interfaces

| File | Purpose |
|---|---|
| `core.mjs` | Bounded deterministic planning interpreter and metered algorithms |
| `learning.mjs` | Fixed training-only racing, exact candidate identity, fresh qualification, two admission gates |
| `adapter.mjs` | Actual released workbench registration, current result check and local receipt |
| `stream.mjs` | Finite mission selection, paid retention, budgets, STOP, atomic recovery, retirement and rollback |
| `scenarios.mjs` | Prespecified synthetic distribution; importing it does not create confirmation inputs |
| `seed-registry.mjs` | Global seed/scope and exact semantic input-disjointness checks |
| `checker-client.mjs` | Bounded JSONL IPC to the separate Python checker |
| `specialist.py` | Time-indexed SciPy/HiGHS reference; deadline feasibility and makespan modes are distinct |
| `experiment.mjs` | Single bounded confirmation launch and raw artifact capture |
| `analyze.py` | Registered paired stream bootstrap and descriptive summaries |
| `fault-tests.mjs` | Actual process restart, lost acknowledgement, duplicate request, invalid receipt, timeout, scope, budget and rollback tests |

Browser-friendly entry points contain no Node imports:

```javascript
import {runMission} from './companion/adapter.mjs';
import {createMissionStream} from './companion/stream.mjs';
import {demoConfiguration} from './companion/scenarios.mjs';

const row = await runMission(task, {
  budget: 100000,
  check: independentlyImplementedBrowserChecker,
});

const stream = createMissionStream({
  ...demoConfiguration(),
  check: independentlyImplementedBrowserChecker,
  storage,
  onEvent: event => render(event),
});
await stream.start();
```

The storage backend supports `save(snapshot)`, `load()`, `saveGuard(guard)` and `loadGuard()`. The full browser uses persistent local storage and warns when persistence is unavailable. The browser's checker has a separate implementation, but its authorship/custody limitations remain explicit.

## What the costs mean

The primary resource is a published **counted-work model**, comprising named deterministic operations and structural metadata blocks. It includes discovery, rejected proposals, current checks, control, storage, lookup, upkeep and recovery. Telemetry number formatting is normalized for accounting so measured elapsed-time strings cannot change an algorithm's deterministic cost. Actual file sizes and wall/CPU times are reported separately.

The independent Python checker uses its own explicit reference-operation model. The native MILP internals are opaque and are never assigned invented JavaScript work counts. Native model construction, solve, current check and startup times are reported separately.

Common synthetic WORLD-input generation is measured outside the conditional per-arm mission-work endpoint. Engineering, assistant authoring, commissioning, machine ownership and human labor are unpriced. These results do not establish profit, paid demand, commercial growth, general intelligence, or a self-accelerating production service.

## Inspectable strategy succession

The declared chain is a dispatch rule → a bounded lookahead policy that executes that rule as its rollout evaluator → a repair policy whose construction and/or qualification invokes the inherited planner. Actual inherited-call counters, exact ASTs and parent identities are retained. Fresh mission removal, independent reconstruction and equivalent-recipe replacement tests distinguish method content, acquisition cost and historical identity. A parent reference alone is not treated as proof of beneficial transfer.

The equally enabled conventional strategy learner runs literally the same mechanism. A tie is an informative result. The ordinary portfolio begins with competent methods, including an inexpensive stable-order repair policy, and remains available whenever capability construction is refused.
