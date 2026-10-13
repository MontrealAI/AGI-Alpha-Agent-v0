# SUCCESSOR Ω: useful local work

This additive workbench preserves the existing personal lab, aggregation workshop, lifecycle,
native commands, journals and deployed contracts. Open [the workbench](../successor/work/index.html),
choose a mission, run the example, inspect its files, and save your working HTML copy.
No account, provider key, wallet or token is required for these five adapters.

## What actually runs

| Family | User-controlled inputs | Actual computation and deliverable | Deliberate boundary |
|---|---|---|---|
| Reliability | `contains` source, interval, test cases | Execute a finite range-function grammar; test four repairs; export source, patch and runnable Node checks | One closed-interval utility; arbitrary repositories are not executed |
| Performance | Integer values, repeats, repetitions | Measure Set/sort against sort/deduplication; alternate order; check output equality; export timings and selected source | Local timings, no guaranteed advantage or monetary claim |
| Documentation | Markdown with `successor-example` JSON blocks | Execute URI encoding/decoding and UTF-8 operations; retain failures; propose corrected examples | Three explicitly supported operations, not an arbitrary SDK |
| Public data | Two-column `group,amount` CSV, units | Parse rows, group and reconcile integer totals; export editable CSV, JSON and HTML | Public/synthetic/licensed nonpersonal inputs; no inferred data rights |
| Numerical | Polynomial coefficients, interval, even step count, tolerance | Calculate exact rational quadrature and analytic integral; compare trapezoid and Simpson errors | Polynomial quadrature, not general scientific validation |

Each family runs different domain logic. Changing permitted inputs changes execution and its commitment.
Changing a display name or interface language does not create stronger evidence. Failed candidates and negative
comparisons remain in the result. A locally completed task can still require repair or retain its incumbent.

Input policies and limits are checked before execution. Unknown fields, duplicate JSON keys, unsupported source,
missing rights, unsafe integers and unbounded inputs are refused. CSV exports neutralize formula-like group labels;
HTML reports escape supplied text. Imports are inert data, never plugin installers or trust registries.

## Native operator and machine interface

Use the existing installed `alpha-agent` with Python 3.11–3.13 and Node 22 or later. Existing Python-only
missions keep their dependencies. From a fresh directory outside the source checkout:

```bash
alpha-agent successor-work example reliability --output mission.json
alpha-agent successor-work plan mission.json
alpha-agent --home operator successor-work run mission.json --output result
node result/check.mjs
```

The JSON response includes the run ID, state, result digest and output directory. Keep that run ID for
`show`, `review`, `control` and `export`. In the following commands, substitute the returned values:

```bash
alpha-agent --home operator successor-work show RUN_ID
alpha-agent --home operator successor-work review RUN_ID --result-digest RESULT_DIGEST --decision accepted --note "Reviewed the source and all failures"
alpha-agent --home operator successor-work export RUN_ID --output another-copy
alpha-agent successor-work restore result/evidence.json --output restored-mission.json
alpha-agent --home another-operator successor-work run restored-mission.json --output fresh-result
```

The machine interface is the same typed JSON CLI, protected by the existing private operator directory.
There is no new HTTP listener, unauthenticated localhost API, account service or browser-to-host bridge.
For a desktop browser-only start, use the saved HTML. Native Computer Use is a separate explicit setup;
see [Computer Use](SUCCESSOR_COMPUTER_USE.md).

`review` records the local operator's acceptance or rejection of delivered work. It never fabricates an
independent verifier, institutional admission, production authority or settlement.

## Evidence, Jobs and lifecycle integration

The same domain source is bundled into the installed Node worker and the standalone browser page.
`workbench_sources.json` commits every transitive source, including the provenance-checked AGI Jobs compiler.
The browser/native pack contains inputs, source identity, artifacts and their hashes, all observations,
limits, draft Jobs compilation and elapsed wall time. Provider and settlement spend are zero for fixed local
adapters. Host compute cost and actual human effort remain unmeasured, never silently zero.

The pinned AGI Jobs compiler groups its 21 obligations into seven typed lifecycle work packages.
These plans have zero funding and require actual reviewer/acceptance commissioning before live dispatch.
No token transfer, chain approval, market connection or work settlement happens in this workbench.

Native runs register an `Institution`, `MissionConstitution` and `CandidateReleaseManifest` using the
existing `SuccessorStore`, strict protocol and local-role custody. These records nominate the frozen
maintained work method; they do not install it as a serving release. WORLD/POLICY claims, proof, admission
and authority retain the existing lifecycle's separate gates. The existing `successor-demo` and Jobs/
Ascension acceptance suites exercise full bounded delegation, revocation, negative settlement and succession.

Native exports add `lifecycle.json` and an Ed25519 `signed-receipt.json`. Verify attribution with a source
key retained independently of the downloaded package:

```bash
alpha-agent successor-work verify-receipt result/signed-receipt.json --source-key TRUSTED_PUBLIC_KEY_HEX
```

The adjacent `source-key.txt` identifies the producing key; importing that file is not independent trust.
A signature establishes local attribution and integrity, not factual correctness or current authorization.
Retain the existing journal checkpoint separately when freshness and rollback detection are required.

## Recovery, ownership and migration

Pause with `successor-work control RUN_ID --state paused`; use `stopped` or `retired` to end the run.
Interrupted pure work may restart only with the same task, run ID, `--resume`, and a new output directory.
All attempts share the three-attempt ceiling. Stopped and retired runs cannot resume. The existing global
operator pause is also checked during the worker. Concurrent execution uses signed revisions and leases.

Each artifact directory is new; existing files are never overwritten. Public exports exclude private keys
and grants. Restoring evidence produces a task and historical, unauthenticated observations with empty
active proof and authority. Rerun and review locally. Copying a name or a release number transfers no trust.

Saved HTML works without browser storage or a service worker in modern desktop browsers. Save a new copy
after edits; retain full evidence separately. Browser execution is cooperative and isolated from host files;
the native fixed worker additionally has a process deadline. Mobile browsers can use the hosted page;
mobile file-preview applications are not promised to execute downloaded HTML.

No migration of existing state is needed. New records use `@successor-work:` and `work-` institution
identities in the existing append-only journal. Optional local role keys occupy `workbench-principals`.
Use the existing installation, backup, update and uninstall procedures; no historical wallet is required.

## Extension SDK

`examples/successor-workbench/engine.mjs` exports `createWorkbench(adapters)`. An operator-installed
adapter supplies a versioned manifest, an input validator and a bounded asynchronous `execute` method.
All six output fields are checked by the shared transport, source commitments and draft Jobs compiler.
The additional `word-inventory` example executes without modifying the core registry:

```bash
node examples/successor-workbench/extension.mjs
```

Source adapters are trusted software installed through normal code review. Never load an adapter from a
mission/evidence JSON file, a model reply or an untrusted URL. Changing an adapter or supplier requires a
new source commitment and fresh evaluation. The SDK is for local public work; institutional effectful
tools use the existing `ActionGateway` and separately authorized resource reservations.

## Reproducible checks

```bash
python scripts/generate_successor_workbench.py
python -m pytest tests/runtime/test_successor_workbench.py tests/runtime/test_successor_computer.py --confcutdir=tests/runtime -q
node --test examples/successor-workbench/test.mjs
python -m scripts.validate_successor_workbench --output evidence/workbench-browser --axe-script tests/browser/node_modules/axe-core/axe.min.js
```

The Computer Use container test requires `SUCCESSOR_COMPUTER_IMAGE`; its absence is a reported skip,
not a pass. The release job requires this test with a real immutable image. Live providers, independent
evaluation, actual customer acceptance and mainnet commissioning have separate evidence requirements.
See the [implementation and acceptance record](SUCCESSOR_IMPLEMENTATION_2026-10-13.md).
