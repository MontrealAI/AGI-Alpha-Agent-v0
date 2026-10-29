# Retained experience on fresh work

This native experiment tests whether checked historical LP solutions can construct
equally useful certificates on new inputs at lower lifecycle cost than a complete
set of competent conventional controls. It extends the recovered invention runtime
without modifying its historical experiments, checker, production defaults or
settlement. Its parent is the combined integration candidate PR #5021.

## Run and inspect

Use the project's existing Python 3.11–3.13 development environment and
`compounding-discovery` extra (SciPy 1.17). No model endpoint, wallet, server or
external spending is required. This is trusted installed numerical code; it does
not execute task-supplied Python or shell.

```sh
alpha-agent experience run contrib/compounding_discovery/base-target.json \
  --cases-per-regime 16 --repeats 3 --output /tmp/NEW-experience
alpha-agent experience check /tmp/NEW-experience --seal-sha256 PRINTED_SHA256
alpha-agent experience replay /tmp/NEW-experience --seal-sha256 PRINTED_SHA256 \
  --output /tmp/NEW-reproduction
```

An existing output directory is refused. Interrupted and unsuccessful runs remain
on disk with incurred resource records. Replay requires the original exact source,
dependency profile, base and policies. It reuses the original cases and fallback
selection, and refuses a different reconstructed memory. It is reproduction of
exposed work, never another fresh confirmation. A new `run` uses a new seed.

The seal binds the raw outputs and all policies. Preserve its printed SHA256 or
the immutable Git commit as the trusted comparison value; refreshing a file's own
hash is not authentication. A separate read-only verifier checks source snapshots,
lineage, exact task identities, every output and the full planned denominator.
Its OS filter actually denies writes and new sockets. The verifier never imports
the candidate solver. Authorship, host and libraries are shared; this is procedural
separation, not external certification or hostile-code isolation.

## What is learned

Nine development tasks are executed with all six HiGHS method/presolve choices.
The selected fallback uses development measurements only. The treatment compiles
verified source solutions into reusable active-constraint inverses and dual
bounds; verified negative outcomes supply reusable Farkas witnesses. Every asset
retains its actual source and applicability conditions. The independent verifier
checks that each inverse corresponds to its historical named constraint set.

For a new right-hand side, an inverse constructs a **new numerical schedule**.
The current inequalities and dual gap are checked before reuse. A retained ray
constructs a **new infeasibility certificate**, with its contradiction recomputed
from the current model. Changed coefficients invalidate a primal basis unless its
complete signature matches. Unsupported transfers fall back to the selected full
solver; all unsuccessful attempts and discarded partial constructions cost time.

This is established parametric linear optimization implemented as retained
experience. It is not new optimization theory, broad autonomous invention,
cross-domain generalization or proof of a commercially useful service.

## Strong controls and fresh cases

The ten arms are six complete HiGHS configurations (`highs`, dual simplex and
interior point, each with presolve on/off), matrix-template caching, an ordinary
primal/dual result cache, a conventional native HiGHS warm start, and the treatment.
Controls that use history receive the same development tasks. The ordinary cache
does not pay for the treatment's inverse construction. The warm control restores
its frozen training basis before every case, preventing evaluation-to-evaluation
learning. Its adapter uses SciPy 1.17's bundled HiGHS API; an unsupported version
refuses rather than quietly dropping that control.

The source, protocol and cost assumptions are frozen first. After learning, the
memory, fallback and setup accounting are frozen, then a new random seed is
sampled. Four regimes produce new RHS, tightened windows, energy stress and
changed charge coefficients. All use the same public raw fleet instance and fixed
route family. Task-content identity excludes names/prose and normalizes decimal
updates. Renaming old cases cannot make them fresh. Evaluation never promotes
new memory, and its failures cannot be fed back while keeping these cases fresh.

Every arm faces the unchanged independent Decimal feasibility checker. Feasible
outputs additionally require a reconstructed dual bound with absolute gap at most
`1e-5`; feasibility alone cannot qualify a worse objective as equally useful.
Feasible schedules and correct infeasibility diagnoses are counted separately.
Conflicting accepted outcomes remain UNKNOWN. Repeated timings are not independent
tasks or multiple productive deliveries. Task/arm order is randomized per repeat.

The conservative comparison uses the fastest **whole-panel lifecycle control**
among every declared alternative, including whichever fixed method wins after
observation. That ex-post comparison gives the controls an advantage; it never
selects or tunes the treatment. There is no universal strongest-workflow claim.

## Costs and decision rules

The useful-outcome gate allows no rejected output or lost acceptance across the
planned comparison. The measured CPU gate requires at least 10% less lifecycle
CPU than the strongest observed control. Deployment uses each task's median timing;
training, portfolio selection, memory construction, preparation and an additional
separate verification pass remain charged. Rejected reuse and fallback are inside
the measured execution envelope. Delivery serialization/flush has its own exact
task/arm/repeat resource record. Common verifier startup/training checks are charged
in full to each history-using counterfactual, conservatively favoring fixed methods.
Fixed pre-existing methods need no history or new strategy selection.

Whole-campaign CPU, child-verifier CPU and wall time are also reported. These actual
experimental resources are distinct from a counterfactual one-pass operational
deployment. Do not add timing repetitions or mutually exclusive arm totals as if
they were one business's cost. Model/implementation authoring, human attention,
energy, support, deployment and opportunity costs are not inferred from CPU time.

The inherited illustrative rates are SIM USD 0.10/CPU-hour and USD 0.03/decimal-GB-month.
Retained bytes are a representation-size proxy: JSON history/memory, array payload
for templates and an explicit eight-byte-per-basis-status estimate for native
HiGHS. This is not a complete installed-memory or hosting measurement. No rate is
claimed to be an invoice or current provider quote. `cost-policy.json` defaults
shared development and every arm's additional fixed/per-task cost to **null**.
Nulls keep complete-cost superiority UNKNOWN; zero is never silently substituted.

An operator may supply `--cost-policy FILE`, following the emitted schema. Every
arm must have explicit fixed and per-task costs, plus shared development, rate and
retention assumptions. Include all remaining development, human, energy, hosting,
maintenance and opportunity expenses, with their basis stated. Fully supplied
estimates can support only a conditional **modeled-panel** result. The code also
requires at least 10% lower complete modeled cost than the cheapest control; a CPU
win cannot conceal an expensive learned artifact. Actual profitability, customer
demand and earned-funded successor construction remain separate requirements.

This is an exploratory, prospectively frozen engineering experiment. It does not
spend or reset any previous campaign's scientific confirmation/error budget, report
a confirmatory p-value, or qualify the previous protected panels. Preserve all
earlier negative results. The first development smoke is retained separately,
including a tiny-dual serialization refusal; the producer repair never weakens
the common checker or relabels that smoke as confirmation.

## Validation

```sh
python -m pytest -o addopts='' contrib/retained_experience/test_experience.py -q
mypy --strict --follow-imports=silent alpha_factory_v1/core/runtime/retained_experience
```

Focused tests exercise actual LPs, fresh certificate construction, conventional
warm starts, coefficient shifts, negative transfer, false optimality evidence,
semantic freshness, OS verifier restrictions, accounting unknowns and tampering.
Scoped passes do not replace installed-wheel, full repository, hosted release or
field qualification.
