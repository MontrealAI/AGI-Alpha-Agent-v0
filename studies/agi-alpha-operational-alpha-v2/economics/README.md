# Conditional enterprise experiment

This module executes accounting and finite sequential decisions. It **does not observe customers, API bills,
model tokens, willingness to pay, or complete actual research cost**. Actual collections are zero; actual complete
cost and profit remain unknown. Its output is a conditional economic scenario, not a commercial result.

## Input and interpretation

`pilot.json` has this shape (numbers below are syntax examples, not the study's results):

```json
{"arms":{"U":{"accepted":4,"attempted":4,"elapsed_seconds":500,"operations":20},"E":{"accepted":4,"attempted":4,"elapsed_seconds":500,"operations":20},"E_plus":{"accepted":4,"attempted":4,"elapsed_seconds":500,"operations":20}}}
```

The model extrapolates aggregate pilot acceptance through an explicitly assumed Beta(accepted+1,failed+1)
exchangeability model. Four constructed tasks do not calibrate real service quality. Identical sufficient
statistics receive identical latent-quality draws, preventing Monte Carlo noise from inventing superiority.
All token/compute expenses and capacity reservations are the same across configurations. Hosted elapsed and
operation counts are retained as input provenance, **never treated as API tokens or CPU cost**.

H uses the sourced USD61–80/hour Arc backend band with **assumed** one hour at USD70/hour per finite
70–110-line component repair, giving a USD70 primary reference. The declared effort range is0.5–4hours, not a
human timing observation or matched quote. The lower-price reference is one hour at USD30/hour. The earlier
4–12-hour estimate belongs only to a broader production-service hypothesis and is not used in benchmarkH.
Demand/validator/model/transfer/cost stresses are retained. Production costs include all nine explicit categories. Routine human review is zero in the
automated primary scenario; separate stresses add5or15minutes at the sourced-rate reference. These are hypotheses,
not an invented staffing requirement.

The six policies are ordinary U, established expert E, equipped E+, private retention, protected shared retention,
and an ordinary identical-content library. E's initial modeled method setup is B; E+'s additional packaging is B.
All policies share the same two modeled recipients,12daily capacity units and opportunity tapes. A single job
reserves2units for up to2attempts; a four-component pack reserves8. Unused attempt reservations remain unavailable
in that conservative model. Private retention equips recipient0; shared and library equip both. Distribution
costs, contents, permissions and outcomes are identical for graph and library. No graph premium is inserted.

## Decisions and accounting

The price/reserve grid is selected on32development worlds per policy using the declared risk-sensitive objective.
The frozen choice is reused in all new primary and stress worlds. After actual modeled observations, policies may
screen/assess a capability, decline it, select optional Gym development, prototype the four-component pack, deliver,
hold funds or stop production. All see the same offering menu and public pilot eligibility. Latent outcomes and
future demand are never passed to the choice rules. The bounded search is not a globally optimal enterprise.

The pre-assay support bound uses the full feasible monetary pair support; a posterior mean is not an upper support
bound. The unchanged local `integration/admission.py` helper is called before modeled assessment and its source
hash is frozen. Six **hypothetical future** assay clusters are generated only in the simulated environment. This
does not qualify the actual four-task unmetered pilot or authorize execution through the native protected gate.
A common assessor error can cause false admission; failed assays still cost money. The default conservative Gym
prior can rationally select no training. A training attempt, if selected, can be harmful.

A charges complete attempts, correction, automated quotes, acceptance and daily operations. B charges extra
method setup, assessment, retention, distribution, invocation and maintenance. C charges optional extra Gym and
new-offering prototypes, including failures. No expense is posted twice. Capacity displacement is a resource
constraint, not an additional cash expense. Every retry preserves the original task identity.

Collections, invoices, refunds, capital, costs, profit, reserves and obligations are separate. Contract receipts
are held through a14-day refund window regardless of hidden actual quality, so the decision code cannot peek at
future refunds. Existing liabilities settle during14extra days. Negative operating results remain losses; seed
capital is never revenue. Production stops when unencumbered cash cannot cover modeled recurring expense.

## Run, freeze, confirm

Run from the study root after the actual pilot is final and root authorizes confirmation. No real money or API
credentials are used. Freeze refuses to overwrite an earlier freeze; confirmation verifies source, admission
helper, protocol and input hashes and refuses to replace results.

```sh
python economics/run_economics.py freeze --pilot results/pilot_summary.json --out economics/results
python economics/run_economics.py confirm --out economics/results
python economics/prescreen_experiment.py freeze --out economics/prescreen_results
python economics/prescreen_experiment.py confirm --out economics/prescreen_results
python economics/test_economics.py
```

The main confirmation writes4,608histories:2,304primary (three profiles × six policies ×128worlds) and2,304stress
(six profiles × six policies ×64worlds). Complete event logs are deterministic gzip, with all source and result
hashes. Intervals describe Monte Carlo variation **conditional on assumptions**; they do not establish those
assumptions. A complete replay belongs in another directory; retain the first result.

The independent prescreen experiment freezes128fresh artificial candidate worlds, each with24candidates. It compares
the old loose0.6Kscreen and a reachable-first rule with the same1.25full-cost hurdle. It retains assay failures,
false admissions, realized negative transfer, finite cash and downstream choices. Its result is a **new prospective
synthetic experiment**, not recovered profit from the historical568unreachable assessments.

## Scope limits

No sampled ordinary human users, live customers, bank receipts, metered model calls, live ENS identities, proprietary
weight training, external replication, production authorization, or sustained compounding is established here.
A bundle that both configurations qualify for is a common offering, not a newly expanded exclusive frontier.

The source is Apache-2.0. Original studies and their corrected evidence remain unchanged.
