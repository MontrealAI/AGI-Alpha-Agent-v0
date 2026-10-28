# Bounded adaptive discovery means

This additive AGI ALPHA contribution constructs an observation-conditioned investigation policy over finite,
set-valued predictions. A user supplies hypotheses, available experiments, explicit allowed flags and per-path
resource limits. The instrument returns a checked decision tree, a proved finite infeasibility result, or an
honest incomplete result when computation/output limits stop the search. It never executes imported probes.

The algorithm is established finite minimax dynamic programming. It is not a new scientific method, evidence
of general intelligence, a customer offering, or an autonomous commercial enterprise. Costs are abstract
experiment units, not USD, runtime, AI-versus-human effort or measured research expenses. Actual observation
sets and permission flags still require independent domain and authorization validation.

## Implemented contribution

The current native `flywheel_probe.py` asks for a greedy next singleton-observation read. The preceding
Possibility Engine study at PR #5008 already constructs robust noisy **static** experiment portfolios. This
add-on constructs **contingent policies**: later probes depend on actual supplied observations. Set-valued
outcomes model bounded ambiguity without inventing probabilities. A static portfolio can be unaffordable
while every contingent path fits the budget. That finite action-set result does not establish superiority
over competent conventional adaptive diagnosis; the independent conventional implementation is primary.

The solver minimizes worst-case cumulative cost subject to the hard depth cap. Reported depth is checked,
but is **not claimed globally minimal among cost-optimal policies**. Local depth/ID tie breaking is only a
deterministic implementation choice. Repeating an experiment on one path is forbidden. All potential
outcomes must have a branch. The terminal hypothesis must be uniquely consistent with every observation.

Hard limits: 2–8 hypotheses, 1–12 experiments, 1–8 symbols per prediction set, 250,000 input bytes,
at most 100,000 search states, 20 CPU seconds, 5,000 expanded policy nodes and 250,000 policy bytes.
A resource stop yields `incomplete`, never `infeasible`. The latter is conditional on the supplied finite
hypotheses, observation sets and permitted actions, not a scientific exhaustion certificate.

## Installation and inexpensive first use

Start from the exact contribution revision recorded by the containing source/evidence package. The inherited
native base is `12770c22b4a9f90f2013bbfb64242f912ba5071e`. Preserve the repository's normal setup and qualification
requirements. In a complete networked checkout, the prescribed setup is `FULL_INSTALL=1 ./codex/setup.sh`.
This session's complete setup failed because no offline wheelhouse was available; its sparse checkout also
lacked `alpha_factory_v1.scripts.preflight`. These failures are retained in `evidence/`.

The following **limited editable research installation** was actually used. It reuses installed dependencies
and does not claim a clean, locked or release-qualified environment:

```sh
python3 -m venv --system-site-packages .venv-discovery
.venv-discovery/bin/python -m pip install --no-deps --no-build-isolation -e . -e contrib/discovery_means_v1
.venv-discovery/bin/python -m discovery_means.cli contrib/discovery_means_v1/examples/adaptive.json --output /tmp/policy.json
.venv-discovery/bin/python -m discovery_means.cli contrib/discovery_means_v1/examples/adaptive.json --transcript contrib/discovery_means_v1/examples/transcript.json --output /tmp/continued.json
.venv-discovery/bin/python -m discovery_means.native_bridge contrib/discovery_means_v1/examples/adaptive.json > /tmp/native-contracts.json
```

The example permits `screen` (1 unit), then `left` or `right` (2 units). The fixed pair `left`+`right` costs
4 units; the contingent policy costs at most 3. The supplied observations `screen=R2`, `right=c` identify
`H2`. This is executed software with authored observations; no physical sensor reading is asserted.
The development run took milliseconds; the full declared input range can reach its 20-CPU-second cap.

The experiment JSON fields are `hypotheses`, `experiments`, `max_cost`, `max_experiments`, and optional
`max_states` (default 100,000). Each experiment has exactly `id`, positive integer `cost`, boolean `allowed`,
and `outcomes`, mapping every hypothesis to a nonempty list of inert symbolic strings. Duplicate names,
unknown fields, booleans in integer fields, floats, missing predictions and malformed names are refused.

## Actual native custody journey

```sh
.venv-discovery/bin/python -m discovery_means.native_run contrib/discovery_means_v1/examples/adaptive.json --private-directory /tmp/adaptive-private-fresh --output /tmp/native-journey.json
```

The private directory must be new. This command executes the local instrument, creates one explicitly
research-only instance of the **existing** native Journal, CostLedger, ProtectedLibrary and checkpoint,
and submits opportunity, witness, bundle and observation through the existing signed `Discovery.apply`
path. It then reads back the record and verifies that replay of the same command is refused. Generated
private state, credentials and role keys are not publication artifacts. Refusing RPC readers ensure that
any chain attempt fails. The recorded run made zero RPC calls.

The result is correctly `paused-uncertain`: all three cost buckets remain incomplete. Native custody of
locally executed evidence is established. The general model/tool executor was not used, no real identity
was qualified, no commercial admission was granted, and no revenue or funding was inferred. The earlier
`native_bridge` demonstrates only installed native schemas and predecessor compatibility; its bundle is
a draft. These are distinct integration scopes, both recorded honestly.

Actual environment: Python 3.12; editable native distribution 1.47.0 and add-on 0.1.0. Installed Pydantic
2.14.1 and cryptography 45.0.7 were observed; the latter does not satisfy the native project's >=50.0.1
requirement. Full dependency, package, platform, security and release qualification therefore remain blocked.

## Checks and evidence

```sh
.venv-discovery/bin/python -m unittest discover -s contrib/discovery_means_v1 -p test_instrument.py -v
python -m ruff check contrib/discovery_means_v1
python -m mypy --strict --follow-imports=silent contrib/discovery_means_v1/instrument.py contrib/discovery_means_v1/native_bridge.py contrib/discovery_means_v1/native_run.py contrib/discovery_means_v1/cli.py
```

Twelve focused development tests passed, including ambiguous noisy outcomes, altered commitments, disallowed
probes, budget/depth/search limits, missing branches, unexpected observations, and exponential output
expansion. Independent confirmation is owned by the separate evaluator and lives in the campaign evidence;
it is not counted as development. `verify()` checks every branch without calling `solve()`. It verifies
feasibility and worst-case accounting, not optimality/infeasibility; the independent confirmation oracle
checks those stronger finite claims.

Source freeze and prior-art corrections are in `evidence/source-freeze.json` and
`evidence/development-corrections.json`. The native journey receipts preserve actual operation scope and
unknown costs. These scoped checks do not replace inherited R01–R37 regression applicability or the normal
repository release owner, exact-source CI, package and publication gates.
