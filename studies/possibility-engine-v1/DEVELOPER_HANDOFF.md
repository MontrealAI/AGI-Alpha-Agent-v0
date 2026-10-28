# Developer handoff — Possibility Engine v1

## Decision and boundaries

Retain the useful computational instrument and its evidence. Stop the tested USD4,500 paid-pack launch under the
modeled assumptions. A future application needs an independently supplied beneficiary question, lawful port access,
measured delivery effort and willingness to pay. A physical claim additionally requires calibrated component/timing
bounds and an independently operated fixture. The supported model family and acceptance test stay intact when
searching for that application.

The present implementation handles two through eight labeled sixteen-vertex graphs satisfying `A²=4I+2J`, with
uniform edge rate/leakage and bounded gain/error. It has no trained specialist, arbitrary-graph support or physical
qualification. Conventional construction ties; copying the same ordinary artifact library reproduces the successor
results exactly. Those observations do not establish exclusive or retained-capability advantage.

## Source map

| Path | Responsibility |
| --- | --- |
| `src/engine.py` | Input validation, robust envelopes, minimum-cost portfolio, RC export; local JSON CLI |
| `src/make_examples.py` | Development cases; writes development outputs, so use only in an isolated copy |
| `protocol/ACCEPTANCE.md` | Frozen technical, successor and commercial criteria |
| `verification/independent_math.py` | Direct integer graph construction and analytical conventional comparator |
| `verification/check_protocol.py` | Independent output, coverage and bounded exhaustive-cost check |
| `verification/circuit_runner.py` | Restricted RC parser, Kirchhoff ODE, optional ngspice comparison |
| `verification/run_confirmation.py` | Frozen-seed technical CLI campaign and ordinary-library comparison |
| `economics/model.py` | Strategic alternatives, complete lifecycle and integer-cents ledger |
| `economics/assumptions.json`, `selected_policy.json` | Explicit estimated inputs and frozen attempted policy |
| `verification/check_accounts.py` | Independent event-by-event accounting and contract closure |
| `verification/check_summaries.py`, `check_reference_accounts.py` | Additive aggregate/reference audits |
| `reproduce.py` | Additive safe replay wrapper; does not modify the 22 frozen sources or issued seeds |

## Reproduction environment

Observed: Python3.12.14; NumPy2.3.5; SciPy1.17.0; Linux x86-64 with glibc2.39.
Only this study environment was exercised. The parent repository's Python3.11–3.13 policy is not evidence of this
study passing every interpreter/platform combination. `requirements-study.txt` pins the two direct numerical
dependencies. No dependency installation occurs automatically.

Native circuit validation used ngspice42 from Ubuntu package `42+ds-3build1`. The official-index checksum match,
dependency checksums and explicit signature-verification limitation are preserved in
`verification/ngspice-package-verification.json` and `verification/ngspice-dependency-verification.json`.
The extracted native executable is environment-specific and is not bundled as a portable runtime.
Supplying no `--ngspice` runs ODE validation only; inspect `simulator.status` instead of calling that a native pass.

## Quick verification and full replay

Run the quick command from the study directory:

```sh
python3 -B reproduce.py --output /tmp/possibility-engine-quick-review
```

It creates a new isolated workspace, checks the exact freeze and seed identities before and after execution,
reruns the development joint and successor CLI deliveries, independently verifies feasibility/optimality and
predictions, compares semantic results, and runs the fourteen existing unit/control tests. Complete JSON equality
is also reported; a different equally optimal portfolio can remain semantically equivalent if it passes the
independent check. Logs and `reproduction_receipt.json` remain in the output directory.

For complete replay, first extract `AGI_ALPHA_FLYWHEEL_COMPANION_v1.zip` into a new directory and enter
its `possibility-engine-v1/` folder. The compact source checkout omits bulky raw journals and netlists;
`stage-full` copies its containing tree and does not retrieve the archive automatically. From the complete
extracted tree, first stage a new copy. The wrapper moves only copied result directories into
`original_results/`; it never removes original study records.

```sh
python3 -B reproduce.py --mode stage-full --output /tmp/possibility-engine-full-review
sh /tmp/possibility-engine-full-review/REPLAY_COMMANDS.sh
```

The generated script uses these exact interfaces inside its isolated workspace:

```sh
python3 -B verification/run_confirmation.py FREEZE.json evidence/confirmation/seeds.json --output evidence/confirmation/technical
python3 -B economics/model.py confirm --seed-file evidence/confirmation/seeds.json --output economics/confirmation
python3 -B economics/persist_confirmation_references.py
python3 -B verification/check_accounts.py economics/confirmation --config economics/assumptions.json --output verification/replayed_accounting.json
python3 -B verification/check_summaries.py .
python3 -B verification/check_reference_accounts.py .
```

It then invokes the wrapper's `stage-circuits` mode to copy immediate netlists from `binary_*` and `successor_*`
case directories, excluding ordinary-library duplicates. Finally it calls:

```sh
python3 -B verification/circuit_runner.py /absolute/path/to/circuit-inputs /absolute/path/to/new-circuit-results
```

For native comparison, stage with `--ngspice /absolute/path/to/ngspice` and, when required,
`--library-dir /absolute/path/to/its/libraries`. Those flags are forwarded to the circuit command. Keep its output
directory new. The generated script uses the actual invoking Python executable and safely quoted absolute paths.

Do not invoke `issue_seeds.py` for reproduction: the retained bank is the original post-freeze evidence.
New scientific confirmation requires a new explicitly scoped source/protocol version and genuinely fresh seeds.
Do not run `model.py develop`, `make_examples.py` or output-overwriting analysis scripts in the original study.

## Verification status

The completed campaign has 42/42 fresh technical cases/controls, 336/336 independent ODE and native circuit passes,
12/12 ordinary-library ties, and complete independent reconciliation of 1,536 trajectories, 385,682 journal events,
1,828 contracts and 228 aggregate statistics. All final deposits, receivables and obligations close. Forced lifecycle
controls are excluded from demand estimates. Simulation sampling precision does not establish confidence in the
estimated demand, cost or behavioral inputs.

The frozen scientific source passed the scoped Ruff E/F check. The recorded strict-mypy run remained **failed**
because two SciPy imports lack stubs; it is not a full typing pass. The full repository setup, test suite, coverage,
complete pre-commit/security/integrity hooks, representative platform campaign, hosted integration, package/Pages
publication, native installation and live served-byte acceptance were not performed for this study.
See `evidence/qualification/prior_checks.json` for the exact qualification boundary.

## Integration and ownership

This is an additive research study under `studies/possibility-engine-v1/`. The recorded ownership snapshot in
`evidence/research/ownership_snapshot.json` identifies the existing integration/publisher lane under issue4850,
including the #5007 dev-UI observability repair and the separate resilient-compute commercial campaign. At that
snapshot, the production publication lane remained held; source checks in this study do not qualify that lane.
Recheck live owner/main refs and follow the repository's normal review, merge and publication gates before any
integration. Preserve the other studies, protected source pins, negative findings and sole publisher ownership.

No publication, deployment, release tag, customer message, purchase, fund transfer or credential change is performed
by the reproduction commands. The LinkedIn text remains a draft for approval.
