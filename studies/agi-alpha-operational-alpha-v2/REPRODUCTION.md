# Reproducing the supporting studies

This guide covers the four-task Operational Alpha pilot, its development mission, the separately frozen C5
composition control, the actual-byte capability transport fixture, and the two conditional enterprise simulations.
The later scientific-model reuse qualification extension under `opportunity/` is outside this completed supporting
review. This guide does not select or evaluate that extension. It does not build the paper or certify a deployment.

## One command

From this study directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python reproduce.py
```

The command verifies frozen inputs and sources, re-evaluates all saved deliverables, repeats the native fixture,
reconstructs both economic summaries from their archived history rows, and repeats the small prospective admission
prescreen experiment. It executes the existing `economics/verify_value_results.py` in a temporary copy because that
verifier writes a result file. It leaves the original evidence unchanged. The final JSON printed to standard output
contains a Boolean `passed` field; failure also returns a nonzero exit status.

A fresh report can be saved without overwriting an existing one:

```sh
PYTHONDONTWRITEBYTECODE=1 python reproduce.py --report validation/my_supporting_replay.json
```

To additionally re-execute all **4,608 original and 9,216 value-controller selected economic histories**:

```sh
PYTHONDONTWRITEBYTECODE=1 python reproduce.py --full-economics --report validation/my_full_supporting_replay.json
```

This option compares every regenerated outcome row exactly with the saved row. It uses the frozen selected policies
and fresh-world seed lists. It does not repeat the earlier policy search, regenerate hosted-agent reasoning, or
independently validate the simulator's economic assumptions. The archived compressed event streams are checked
against their recorded SHA-256 commitments; this reproducer does not independently re-audit each ledger event.

The default and full commands were exercised outside the repository in a temporary standalone package. The full
selected-history replay completed successfully with a source closure containing only the supporting study folders
and the 34 files described below. The final review records actual timings and versions. Timings are environment
observations, not portable performance promises.

## What is actually reproduced

| Evidence | Replay operation | Meaning and boundary |
|---|---|---|
| Development repair | Run the frozen evaluator against the archived submission | One 10/10 development outcome; not paid work or protected confirmation |
| Primary U, E and E+ | Re-evaluate twelve submissions and compare their inventory hashes | Four paired task families, one batch per arm; each output passes ten categories |
| C5 U, E and E+ | Re-evaluate three submissions, including unchanged common components | One supplied composition task, fourteen categories; not fourteen opportunities |
| Runner records | Check closure, budgets, log sequences, inventories and exposure order | Recorded successful operations; not comprehensive infrastructure telemetry or hostile-process isolation |
| Capability capsule | Compare source, recovered and ordinary-library bytes | Actual transport of the same 4,649-byte workflow capsule; byte equality is not recipient benefit |
| Native/lifecycle fixture | Fresh local encryption, signature, authorization and accounting controls | 31/31 controls with declared synthetic identities; no live ENS authentication or production admission |
| Original enterprise model | Reconstruct summary and all principal final accounting identities | 4,608 policy histories over 768 profile/seed worlds; all money simulated |
| Value-controller supplement | Run existing verifier, reconstruct summary, verify original bindings | 9,216 controller/policy histories over 768 different profile/seed worlds |
| Prospective prescreen | Re-execute 256 rule histories and compare confirmation and summary | 128 artificial candidate worlds; no recovered historical profit |

Every primary and C5 artifact was accepted under its frozen evaluator. The accepted-output differences E−U and
E+−E are zero in these experiments. This is a small descriptive result, not an equivalence theorem. Neither the
number of protected categories nor the number of simulated histories increases the number of observed task families.

The native fixture's actual-source bindings and cryptographic operations are executable. Its ENS members, positive
monetary admission examples and payment amounts are fixtures. The actual candidate remains outside the unchanged
native production scope, lacks complete monetary evidence and has four primary clusters against the existing
six-cluster gate. The actual recorded collections are zero; complete actual costs and profit are unknown.

## Runtime dependencies

The benchmark replay, economic code, archive checks and report writer use the Python standard library. The native
fixture additionally needs **Node.js**, **Pydantic 2** and **cryptography**. It uses Node's built-in modules; there is
no npm dependency install for this fixture. It needs no model API key, wallet key, browser session, paid account or
network connection. Python 3.11–3.13 is the repository-supported range.

The reviewed environment was:

| Component | Observed version |
|---|---|
| Python | 3.12.14 |
| Node.js | 24.22.1 |
| pydantic | 2.11.7 |
| pydantic-core | 2.33.2 |
| cryptography | 50.0.2 |
| cffi | 2.1.1 |
| pycparser | 2.22 |
| annotated-types | 0.7.0 |
| typing_extensions | 4.14.1 |
| typing-inspection | 0.4.1 |

These are observed versions, not a claim of a fully locked operating-system or binary-wheel environment. The
repository's general contributor guide names Node 22.17.1 for the web client; this supporting native replay was
executed on the Node version above. No browser assets or web-client CI are exercised here.

If dependencies are missing, install the reviewed direct Python versions in your chosen virtual environment:

```sh
python -m pip install pydantic==2.11.7 cryptography==50.0.2
```

Package installation may require internet access. The reproducer itself does not install anything. To check saved
outputs and standard-library economics without fresh native execution, use the explicit limited mode:

```sh
PYTHONDONTWRITEBYTECODE=1 python reproduce.py --skip-native
```

That mode still requires and verifies the pinned prior source files and archived native results. Its report states
that fresh native replay was skipped; it cannot be cited as a fresh 31-control pass.

## Standalone archive and exact source closure

Preserve these two sibling paths:

- `studies/agi-alpha-operational-alpha-v2/`
- `studies/agi-alpha-capability-opportunity-v1/integration/`

For the supporting command, the new study needs `reproduce.py` and its `benchmark/`, `benchmark_composition/`,
`protocol/`, `workflows/`, `results/`, `integration/` and `economics/` folders. Preserve the correction histories and
all archived failed test output. `REPRODUCTION.md` and `validation/` supply provenance and review, although earlier
review reports are not inputs to acceptance. No external `research_runs/` workspace is required: the submissions
and runner records are archived under `results/trials/`.

Only **34 exact prior-edition files** are needed for the native replay:

- `bridge.py`
- `replay.mjs`
- `run_integration.py`
- `crypto_controls.mjs`
- `source_manifest.json`
- All **29 files** named by `source_manifest.json`, at their unchanged `local_path` values below `integration/`.

The machine-readable complete list, byte sizes and hashes are in
`validation/final_supporting_review.sources.json`. The 29-file list includes the vendored native runtime, research
lifecycle, authority fixture, provenance and licenses. Do not substitute current repository implementations for
these pinned files. The wrapper checks five adapter/manifest hashes, then every vendored source's hash and size.
An altered source fails before output or native execution.

The exact prior adapter pins originate in `integration/run_native_integration.py` and the archived native protocol.
The source manifest records the unchanged research lifecycle source commit
`2727262caa52766a78916f2ed81f5afaf668edce` and native source commit
`80b345828f34fd8a6e592977dd17ef37141305f4`. The additive study's recorded parent is
`231834269599d85e49cfe1ca9917a1a874522d44`. The standalone command verifies local bytes against these archived
commitments; it does not require Git or fetch network content to re-establish the historical commit ancestry.

The standalone packaging review also changed a frozen C1 source in its temporary copy and confirmed rejection
before saved-output execution. All copied source and result bytes remained unchanged after the successful replay.
Ephemeral signature keys, local journal identifiers and elapsed times need not be identical across native runs;
control outcomes and transported bytes must match.

## Frozen simulations and optional search reconstruction

The original confirmation binds the frozen simulator, cost/market protocol, admission helper, pilot input and selected
policies. The value-controller supplement separately binds those original files and results, its own wrapper and
protocol. The existing value verifier checks 2,304 held histories against exact expert operation, 768 graph/library
pairs and 2,304 unchanged control histories. Both summary functions are rerun and compared by exact JSON equality.

`--full-economics` replays selected policies only. To reconstruct development selection and event-emitting
confirmation as well, use **new output directories**. Never point these commands at the archived results:

```sh
python economics/run_economics.py freeze --pilot economics/results/pilot_input.json --out /tmp/alpha_original_rebuild
python economics/run_economics.py confirm --out /tmp/alpha_original_rebuild
python economics/value_controller.py freeze --out /tmp/alpha_value_rebuild
python economics/value_controller.py confirm --out /tmp/alpha_value_rebuild
```

The value-controller wrapper intentionally retains its bindings to the preserved original source/data in
`economics/results/`; it does not silently replace them with a new original run. Existing freeze/confirmation paths
are refused by the studied programs. A new run is a reconstruction of the already specified experiment, not a new
prospective freeze.

The original and value-controller confirmations use different fresh seed sets. Compare policies within each matched
world set. For example, the value-controller result compares HOLD with the original policy on the *same new worlds*;
subtracting an original-edition headline mean from a value-edition headline mean would confound the world change.
The preserved original policy results are not rewritten by the supplement.

## Replaying model behavior requires a new trial

Running saved code is different from asking frontier models to solve unfamiliar tasks again. The original hosted
contexts had no independently verified public API snapshot, itemized token bills or complete research cost ledger.
Their original wall times, thoughts and model usage cannot be recovered by re-running Python. The exact participant
message bytes were not committed before the original primary trial; the documented role instructions and later
archive preserve that limitation.

A new model trial needs a separately versioned model/access manifest, fresh protected task instances, frozen role
instructions, matched budgets and complete metering. Do not present results on these now-public tasks as protected
fresh confirmation. Do not pool development, C5, assertion categories or economic simulations with the four primary
task-family units.

## Validation scope

The completion review records source-pin checks, all sixteen saved outcomes, the 31 native controls, all 13,824
selected economic history reruns, prescreen replay, an isolated packaging check and a changed-source negative
control. `ruff check` and targeted `mypy --strict --follow-imports skip` passed for `reproduce.py`; Ruff formatted
the file. An attempted Black invocation failed because the installed environment lacked
`pathspec.patterns.gitignore`; no Black pass is claimed. Initial reproducer-only diagnostics and their corrections
are retained alongside the final review.

This is internal research review and scoped reproducibility validation. It is not external replication, the full
repository test suite, hosted CI, production security review, publication verification or authority to deploy.
