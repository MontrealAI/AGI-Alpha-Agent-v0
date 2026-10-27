# Joint roster and funded opening instrument: technical record

## Result and scope

The executable constructs a complete **synthetic commitment and schedule package**: permitted worker shifts, employer quotas, each child's full care interval, named physical opening and backup offers, qualified staff reservations, a reconciled cost ledger, and eligible payer allocations within every ceiling. It does not deliver childcare or establish actual consent, availability, qualification, licensing, enforceability, demand, or profit.

The origin has a CAD 405 complete combined package. Fixed rosters require CAD 705 and exceed the same aggregate ceiling of CAD 450. Flexible rosters without a commitment to open the declared facilities cannot provide care in this instance. An ordinary exact coordinator given the complete combined formulation selects the identical package. Conventional enumeration and maximum flow are implementation components; no algorithmic or execution superiority is claimed. See [origin input](origin_case.json), [V2 result](origin_result_v2.json), and the [input schema](input_schema.json).

The first prospectively frozen varied run produced **0 offers in 24 randomized cases**. That result remains material and unchanged. A later, separately frozen adaptive boundary study locates a feasible region; it does not replace the original failures or estimate market eligibility. V2 corrects eight verifier omissions found by an independent audit. All original evidence is retained. Fresh independent V2 confirmation passed 12 new cases and rejected 20 new tamper attempts; these finite tests do not prove correctness for every possible supported input.

## The smallest inspectable complete origin

There are two employers, four parent workers with one child each, and four counterpart workers. Each employer requires two workers on the 06:00–10:00 shift and two on the 10:00–14:00 shift. All eight workers explicitly permit both shifts. Changing from the current shift costs CAD 5 per worker. In the input, each employer's W1 and W2 are parents; W3 and W4 are counterparts.

| Worker, at each employer | Current shift | Selected shift | Change compensation |
|---|---|---|---:|
| W1, parent | 06:00–10:00 | 06:00–10:00 | CAD 0 |
| W2, parent | 10:00–14:00 | 06:00–10:00 | CAD 5 |
| W3 | 06:00–10:00 | 10:00–14:00 | CAD 5 |
| W4 | 10:00–14:00 | 10:00–14:00 | CAD 0 |

All four children need care from 05:30 to 10:30 because the input declares 30 minutes of travel before and after work. Each parent accepts either named site. Site A supplies the primary opening and site B the reserved backup. Each offer declares capacity four and one named qualified caregiver for its five-hour opening. These capacities and qualification tags are assumptions supplied by the input, **not inferred legal ratios**.

| Required world | Complete care assignment | Active opening | Reserved backup |
|---|---|---|---|
| Normal | All four children at A, 05:30–10:30 | A early | B early |
| Primary provider absent | All four children at B, 05:30–10:30 | B early | B commitment activates |
| Backup provider absent | All four children at A, 05:30–10:30 | A early | Unused in this world |

The finite contract permits one mutually exclusive full-day world to be realized. Each outage is announced at 05:00, before care begins. The arrangement makes no mid-session transfer promise. Primary charges are explicitly nonrefundable if the primary provider is absent; the budget therefore includes primary charges even in that world.

| Obligation | CAD | Meaning |
|---|---:|---|
| Primary care | 170 | 150 fixed opening plus 5 per child |
| Backup standby | 20 | Reservation of the named backup block |
| Backup activation reserve | 170 | Full maximum activation cost of one declared world |
| Worker changes | 20 | Four permitted changes at 5 each |
| Coordination | 25 | Revenue for the verified package |
| **Maximum funded package** | **405** | Every finite obligation funded |

The CAD 150 opening quote is itemized into 100 for qualified staff, 20 for the facility, and 30 for provider administration and insurance allocation. These are synthetic illustrative prices, not supplier quotes. All quantities are represented as integer CAD cents. The CAD 380 outside the coordination fee consists of pass-through obligations. In the normal world the realized obligation is CAD 235 and the CAD 170 unused activation reserve is refundable; the reserve is not revenue.

The source allocation pays CAD 40 from each parent, CAD 145 from employer A and CAD 100 from employer B. These satisfy the declared ceilings and category/beneficiary permissions. Allocation is deterministic eligible maximum flow, not a fairness optimum. The maximum admissible coordinator fee for this physical plan is CAD 70. Parent ceilings remain CAD 40 and employer ceilings CAD 145 while that boundary is calculated. A higher fee requires changed inputs, not a reinterpretation of pass-through money.

The selected package covers 4 children and 1,200 child-care minutes in every required world. It preserves every employer quota and 960 worker-minutes per employer, or 1,920 total. These exact checks are reconstructed from schedules and intervals. They are not a solver objective score or evidence of actual service delivery. The V2 origin verifier performs 423 checks and accepts the artifact.

## Input and output contract

The JSON input declares shifts; employers and exact shift quotas; workers, their current and explicitly permitted shifts and compensation; children, parent identities, accepted sites and location-specific travel; providers and their declared participation; locations, opening windows and concurrent capacity; staff, qualification tags, windows and minute limits; primary and backup offers, staffing, capacities and prices; finite worlds and their advance notice; and payer ceilings, categories and beneficiaries.

The supported model has one synthetic operating day, one realized world, integer CAD cents, at most 12 workers, 8 children, 8 offers, 6 scenarios and 4 shifts. A case supplies a search-state limit no greater than the implementation's one-million-state bound. Reaching the limit yields a distinct search-limit result and cannot be reported as an infeasibility proof. Every reported study search completed within its declared bound.

An offer contains a worker roster and serialized schedule; per-world child assignments and complete care intervals; active offers, staffing, capacities and outage data; committed backup offers and reserved staff minutes; every cost item with its derivation; payer-to-item payment edges and payer totals; exact care and employer-output summaries; a fee boundary; and a transformation witness bound to the canonical input hash. Every world and every rejected case is retained. A funding refusal can retain a complete least-cost physical plan and its funding shortfall for inspection.

The constructor enumerates permitted rosters, prunes quota violations, enumerates care assignments and declared worlds, checks physical obligations, and solves eligible payer allocation by integral maximum flow. The ordinary control enumerates the roster Cartesian product before applying the same complete formulation. Both receive the same public information and may return the same optimum. A separately coded checker reconstructs obligations, rejects unsupported domains, verifies exact interval coverage and resources, reconciles all material serialized fields, and checks the claimed fee boundary using its own residual network.

The model's staffing quotas express counts, not unstated employer skill coverage. It does not create a provider that has declined, move a parent to an unaccepted location, split a child's care between sites, infer travel times, or promise protection from an omitted outage. Changing any of those facts requires explicit revised input and a new verification.

## Original frozen varied cases: failures retained

The first [technical freeze](FROZEN_TECHNICAL_POLICY.json) precedes the generation of 18 targeted cases and 24 randomized cases, all retained in `technical/fresh/`. The [summary](fresh_suite_summary.json) records 5 offered and 37 refused, with the ordinary control tying all 42. Four cases offer a complete package where the fixed-roster control refuses.

All five offers are targeted: already-open capacity; low opening price; a three-employer/six-child case with its declared staffing raised; shared caregivers across overlapping blocks where the selected single-block solution avoids conflict; and the exact funding boundary. Targeted refusal cases cover locked choices, insufficient qualification or capacity, no accepted site, excessive backup travel, primary or backup withdrawal, correlated absence, late notice, insufficient funding, absence of a compensation payer, expensive worker changes, and a ceiling one cent below the feasible boundary.

**All 24 randomized cases refused.** Their fixed seeds are 2026102701 through 2026102724. The generator draws alternative-shift permission with probability 0.8, change compensation from CAD 0/5/10/20, and independent pre/post travel at each site from 10/20/30/45/60 minutes. It also varies accepted sites, provider withdrawal, staff qualification, offer/site capacity, opening and per-child costs, standby cost, payer ceilings, already-open capacity and correlated absence. The five-hour offer windows are held fixed; travel exceeding their margins therefore often prevents full care coverage. Exact probabilities and ranges are in [the frozen policy](fresh_case_policy.json) and the frozen generator source.

Across randomized refusals, the search encountered an uncovered care interval in 23 cases, insufficient qualified staffing in 7, and no acceptable location in 6. These counts overlap; they describe encountered pruning reasons, not a mutually exclusive or exhaustive attribution of failure. The unprequalified synthetic mix cannot estimate actual lead eligibility. In particular, it does not support any commercial assumption that 75% of prequalified leads will be technically eligible.

## Separately frozen adaptive boundary experiment

After observing the original failures, a new question was declared and frozen: with identical qualified physical offers, how do opening full cost, employer ceilings and roster permission determine feasibility? The [boundary policy](boundary_policy.json) and [freeze](FROZEN_BOUNDARY_POLICY.json) precede those new executions. All 66 cases are retained in `technical/boundary/`; the [summary](boundary_summary.json) records 19 offers and 47 refusals, with 66 ordinary-control ties.

The 48-cell main grid varies each block's fixed opening cost F over CAD 80/150/220/290, each employer's ceiling C over CAD 80/145/210/275, and permission over locked, employer-A-only flexibility, and both-employer flexibility. Parents retain CAD 40 ceilings and the fee remains CAD 25. Columns below show each employer's ceiling; yes/no means an actual complete offered/refused artifact.

| Permission | F | C = 80 | C = 145 | C = 210 | C = 275 |
|---|---:|:---:|:---:|:---:|:---:|
| Locked | 80 | No | Yes | Yes | Yes |
| Locked | 150 | No | No | No | Yes |
| Locked | 220 | No | No | No | No |
| Locked | 290 | No | No | No | No |
| A only | 80 | No | Yes | Yes | Yes |
| A only | 150 | No | No | No | Yes |
| A only | 220 | No | No | No | No |
| A only | 290 | No | No | No | No |
| Both | 80 | Yes | Yes | Yes | Yes |
| Both | 150 | No | Yes | Yes | Yes |
| Both | 220 | No | No | Yes | Yes |
| Both | 290 | No | No | No | Yes |

For this physical family, the least complete package costs 4F + 105 when locked or only A is flexible, and 2F + 105 when both are flexible. The aggregate ceiling is 160 + 2C; exact category/beneficiary eligibility is still checked. Those equations explain this grid, not arbitrary instances. All 16 no-backup controls refuse, even at the largest ceilings.

The two remaining cases are a predeclared successor and its underfunded pair. The successor renames every participant/resource/shift, shifts time windows two hours later, changes each child's site-specific travel, raises fixed openings to CAD 170 and per-child cost to CAD 6, uses CAD 25 standby and CAD 7 worker-change compensation, and changes payer ceilings. It offers a CAD 466 package with CAD 79 maximum coordinator fee. All four children receive 1,140 total care-minutes per world and both employers retain 1,920 combined worker-minutes. Its lower-ceiling pair refuses with a CAD 16 shortfall. The ordinary control ties both. This is transferred finite construction under a prospectively specified variant, not transferred real-world acceptance or net value.

## Independent audit and versioned correction

The independent V1 audit matched its separate oracle on 48 fresh cases, with 39 offers and 9 refusals, and passed 13 semantic cases. Nevertheless, **8 of 26 tamper tests were incorrectly accepted by the V1 standalone verifier**. Erased backup-offer and reserved-staff summaries, changed serialized worker permissions/employer, and input hashes rebound to unsupported two-day/two-world/non-synthetic/USD cases exposed missing checks. A separate large-integer case exposed a fixed `10**12` capacity incorrectly used as an unbounded funding edge. See [preserved raw V1 evidence](../results/independent_audit_v1_raw.json).

V2 adds independent supported-domain validation, reconstructs the omitted summaries and additional serialized contractual details, and replaces the fixed funding edge with the exact obligation amount. The [correction record](V2_CORRECTION_RECORD.json) describes each change. V1 source, freezes, original 42 cases, boundary 66 cases and prior audit evidence remain untouched. The [V2 freeze](FROZEN_TECHNICAL_V2.json) was recorded at 2026-10-27 19:35:00 UTC and binds 235 preserved evidence files in addition to its new code and replay policy.

The [developer regression](v2_replay_summary.json) recomputed all 109 origin/original/boundary inputs: every four-control status and complete selected offer is unchanged, every selected V2 artifact passes, every search finishes, and the ordinary control ties 109/109. The combined totals remain 25 offered and 84 refused. This replay is not fresh validation. Separate [disclosed-defect checks](v2_known_defect_checks.json) reject the eight known mutations plus three nearby-field mutations, and preserve feasibility under uniform 1e9 monetary scaling.

The independent auditor then generated 12 new cases after the V2 source freeze and withheld them from the constructor author until execution. All 12 match the independent oracle's feasibility, optimum cost and maximum fee; six offer and six refuse. Of the six offers, three are also feasible with fixed rosters and three require the joint arrangement. All 12 ordinary controls tie. All 20 new tamper attempts are rejected: 12 certificate alterations and 8 rebound-input purpose failures. All eight old incorrect acceptances now reject; all 48 prior reference cases replay; 39 old valid witnesses still accept; 13 semantic cases replay; and large-integer funding is corrected. See [fresh V2 policy](independent_audit/FRESH_V2_POLICY.json), [raw V2 evidence](../results/independent_audit_v2_raw.json), and [validation addendum](V2_VALIDATION_ADDENDUM.json).

The independent oracle family is bounded to two employers, four workers and two children. Its new names, times, travel, prices and permissions expand the finite challenge, not the market population. These results provide bounded empirical confirmation and preserve the defect history; they are not proof against all malformed input or all possible tampering.

## Reproduction and exact versions

Run from `studies/agi-alpha-opportunity-construction-v1` with Python 3.11–3.13. The instrument and verifier use only the standard library. The observed runtime was Python 3.12.14.

```bash
python src/e1_instrument_v2.py compare --input technical/origin_case.json --output /tmp/e1-origin-reproduction.json
python src/e1_verify_v2.py --input technical/origin_case.json --result /tmp/e1-origin-reproduction.json --mode combined
```

The Python interfaces are `e1_instrument_v2.compare(case)`, `e1_instrument_v2.solve(case, mode)` and `e1_verify_v2.verify_offer(case, offer)`. The four mode identifiers are `fixed_roster_pooled_care`, `flexible_without_opening_commitment`, `combined` and `ordinary_exact_same_formulation`. Result schema remains `agi-alpha.e1-comparison.v1`; checker reports explicitly identify version `v2`.

The frozen replay runner's commands are `python src/e1_replay_v2.py known-defects` and `python src/e1_replay_v2.py replay`. They refuse to overwrite existing evidence; use a disposable copy without their existing output destinations to reproduce whole runs. No permission is implied to overwrite original artifacts. Individual cases may be reproduced with the constructor command and a new output path.

| File | SHA-256 |
|---|---|
| `src/e1_instrument_v2.py` | `4a57ec8f74c72c85c6209b4123692af5c95ac63ca15e856a3626bfdf5c3d1406` |
| `src/e1_verify_v2.py` | `aa673747ebca69ea44d5ce70c251216705d103f39c4ae85c7e120d1be226cd51` |
| `src/e1_replay_v2.py` | `7a6d76acb26cccda1e7a6ef375a91dcc9c11d652031796b0fef6a2d01ef1fa03` |
| `technical/FROZEN_TECHNICAL_V2.json` | `5a09dd91fff2108c21b43e5615fd8cb616b7a4d3427faedcc902bdeb2802da57` |

Ruff and strict mypy pass for the V2 constructor, verifier and replay runner. The earlier V1 core/checker/suite also passed those focused checks. The already frozen boundary runner retains one strict-mypy advisory about a redundant cast; it was not silently edited after results. Black could not initialize because the installed `pathspec.patterns.gitignore` dependency was absent, so Ruff formatting at 120 columns was used. Full repository integration/release tests were not run for this isolated standard-library study. Monthly extension, commercial economics, legal feasibility and publication are separate artifacts and claims.
