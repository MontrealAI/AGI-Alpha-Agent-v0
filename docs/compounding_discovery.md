# Compounding discovery mission

This additive offline workflow executes three switches through the existing
reviewed mission runtime. It leaves settlement, signing, source pins, provisioning
and release ownership with their existing components. It does not call a paid
model, deploy, contact a buyer or change the production symbolic claim solver.

`A` replays completed productive source experience, extracts its typed capacity
principle, searches by structural signature, validates an explicit variable/unit
mapping and constructs the target model. It never converts currency to energy.
`S` generates and tests a restricted portfolio of executable per-vehicle LP
programs (HiGHS method and presolve combinations), then retains a checked strategy
with applicability limits. It is not unrestricted program synthesis.
`C` corrupts a certificate and searches two seeded moderate operator perturbations
for independently certified feasibility boundaries. It cannot replace the common
final Decimal checker. A criticism that has no checked witness remains unproved.

The target contract is the existing deterministic fixed-route eADARP model.
Public raw data and published route orders are known; fresh operator updates are
simulated. Certificates are useful model artifacts, not field dispatch approval,
empirical battery evidence or evidence of buyer demand.

## Commands

From the repository root in Python 3.11–3.13 with the project and
`compounding-discovery` optional dependencies installed:

```sh
python -m alpha_factory_v1.core.runtime.cli discovery run contrib/compounding_discovery/example-request.json --output NEW_DELIVERY
python -m alpha_factory_v1.core.runtime.cli discovery check NEW_DELIVERY
python -m alpha_factory_v1.core.runtime.cli discovery learn NEW_DELIVERY --output NEW_MEMORY.json
python -m alpha_factory_v1.core.runtime.cli discovery resume contrib/compounding_discovery/example-request.json --output NEW_DELIVERY
```

`run` exclusively creates a new directory. `resume` returns the exact checked
completed result and refuses changed requests, memory or sources. An incomplete
attempt retains resource checkpoints and its failure; it is not silently retried
with a reset budget. Inspect the incurred costs and allocate a separately identified
new request. The experiment runner can resume its immutable completed observations.

For the normal signed lifecycle, submit `example-mission.json` with the ordinary
`run` command. It stops in `review`. Existing exact-revision review and signed
export remain required. Discovery output does not approve or fund itself.

The independent shared-charger extension uses a separate contract that replaces
unlimited station concurrency with one port per declared physical station. It
constructs a conventional joint MILP for at most eight charging visits:

```sh
python -m alpha_factory_v1.core.runtime.cli shared-charger solve contrib/compounding_discovery/example-shared.json --output NEW_SHARED
python -m alpha_factory_v1.core.runtime.cli shared-charger check NEW_SHARED
```

A failed joint search is `UNRESOLVED`; solver status alone is no infeasibility
certificate. The extension is initial seed-funded research. It is not an
already earned-funded successor or a novel scheduling algorithm.

## Experiments and evidence

The evaluator and complete protocol are in `contrib/compounding_discovery/`.
All eight arms have identical task information, solver options, source records,
authority and resource ceilings. The none arm is a complete conventional LP
solver. The separate pinned frontier-authored reference is a real independent
implementation; its certificate serialization is translated before the same
checker and its original output is retained. No fresh live-model benchmark is
claimed. All strategy trials, failures, critics, checks and chronological promotion
costs are counted. Source hashes are frozen before confirmation seeds.

```sh
python contrib/compounding_discovery/experiment.py --base contrib/compounding_discovery/base-target.json --capture contrib/compounding_discovery/capture.json --mapping contrib/compounding_discovery/mapping.json --reference-program contrib/compounding_discovery/generalist_reference.py --output NEW_STUDY
python contrib/compounding_discovery/experiment.py --resume --output NEW_STUDY
python contrib/compounding_discovery/experiment.py --reproduce-from NEW_STUDY --output NEW_REPRODUCTION
python contrib/compounding_discovery/experiment.py --final-from NEW_STUDY --output NEW_FINAL
python contrib/compounding_discovery/audit.py --campaign NEW_STUDY > NEW_AUDIT.json
```

Reproduction reuses frozen inputs/seeds and independently creates new results;
CPU timings can differ. Source-relative freezes require invocation from the
repository root. `.json.gz` observations are lossless and include every task,
program, certificate, memory identity and resource event. Memory histories retain
principles, full checked counterexamples and chronological parent bindings.
They cannot store hidden labels or future task outputs. Unsigned local hashes
are integrity checks; the ordinary signed journal supplies operator identity.

Measured CPU is priced at a declared simulated USD0.10/hour. Retention uses a
declared USD0.03/decimal-GB-month assumption. AI development quantities are
explicit token estimates at inherited reference rates, not actual invoices or
fresh provider quotes. Actual external spending is zero. Full historical
programme payback and actual demand remain unknown. Separate technical gains,
conditional modeled commerce, profit, unrestricted earned funds and funding
provenance; never credit seed equity or refundable custody as earned capital.

Focused validation:

```sh
python -m pytest contrib/compounding_discovery/test_engine.py contrib/compounding_discovery/test_shared_charger.py contrib/structural_transfer/test_runtime.py -q
```

The preserved118-test suite additionally needs the `claim-probe` optional SymPy
dependency. Neither suite substitutes for the complete repository, platform,
security, hosted release, held-source or native-runtime qualification campaigns.
