# Paid work. Retained Alpha. Expanding possibility.

Bilingual offline research demonstration, retaining the Beyond Beta distinction.

## Delivery and data contract

`demo/build_demo.py` embeds `results/demo_data.json` into `demo/template.html`, producing
the self-contained `demo/index.html`. The input object accepts `summary`, `samples`,
`sensitivity`, `mechanism` and `graph`. Each sample is a retained simulator result with
`scenario`, `arm`, `seed`, `weekly`, `events`, `costs`, `skills` and final monetary fields.
The revised economic edition additionally accepts numeric USD
`cost_books: {job, retention, investment, common}`. These totals are displayed directly
and reconciled against the run's `expenses`; absent books remain explicitly pending.
The source-job table reads supplied `source_job_paid_cost` and
`prospective_incremental_retention` fields from `retention_records`, `source_jobs`,
`events` or `skills`. No cost split is reconstructed or invented from older runs.
Despite its legacy field name, `source_job_paid_cost` is explicitly labeled **direct
accrued source-job cost**, not customer price or collected cash. The prospective B
column is the approved upfront retention budget; continuing lifecycle costs remain
in the assessment and expense books. `paid_job_cost_recharged` is displayed separately.
If no simulation data file exists, the builder reads the actual local mechanism and
graph evidence and displays an explicit economic-results-pending state. Development
economic histories are not silently substituted.

All source data are embedded. There are no external libraries, network requests,
fonts, model calls, wallet requests, credentials, or transactions. The content-security
policy disallows connections. Downloading evidence creates a local JSON download only.
Embedded JSON escapes opening angle brackets and Unicode line separators; dynamic
labels and evidence content are escaped or inserted as text.

## Three views

1. **Economic experiment.** Scenario, counterfactual and seed selectors expose saved
   trajectories. A week slider and step buttons inspect actual weekly cash, available
   cash, commitments, accepted useful outcomes and active admitted capabilities. An SVG
   chart and full accessible table show the same records. Decisions appear only when
   recorded in that week. Costs, final totals and final lineage records remain distinct
   from the selected-week state. Receivables do not become cash; investment reserves
   remain a separate policy decision.
   Three cost books make the primary mechanism explicit: **A** includes complete paid-job
   delivery and its learning; **B** includes only additional retention and reuse costs;
   **C** records optional separate invention. Common costs are allocated separately.
   Source-job costs remain in historical enterprise profit and are not charged a second
   time to the prospective retention decision. Retention does not require a separate
   invention investment. The interface warns if supplied books fail to reconcile.
2. **Mechanism laboratory.** A browser-executed exhaustive solver supports one to three
   suppliers with independent integer-uniform costs, bounded public budget and complete
   bundle value. It optimizes within the same declared posted-price family and explicitly
   permits no offer. Full finite unilateral deviations, individual rationality and budget
   checks run locally. The original Python confirmation and its preserved negative
   controls are displayed separately; changing inputs never changes retained evidence.
   Abstract mathematical units are not labeled dollars or realized business value.
3. **Shared lifecycle.** Step controls replay the actual local graph fixture, including
   candidate, evidence, mandatory Alpha assessment, signed attestations, validation,
   admission, canonical promotion, authorized reuse and revocation. The negative novel
   candidate is rejected on complete net value. The Beta v1-to-v2 transition closes
   selection until fresh assessment, validation and admission; historical positive
   evidence cannot silently regain authority. Every fixture member sees the same admitted-skill
   availability. Operational execution permission is separate. The recipient-b refusal,
   recipient-a historical reuse receipt, and revoked held-reuse refusal are explicitly
   distinguished. Selecting an identity does not authenticate a wallet. Nested names
   have no directory authority. The fixture's public cryptographic keys imply no
   production confidentiality, and Merkle inclusion establishes no usefulness.

## Presentation and accessibility

The interface uses deep purple, restrained star motifs, gold accents, clear typography
and responsive panels. EN/FR toggles translate major labels, explanations, controls,
statuses, event descriptions and data headings. Raw evidence remains verbatim. Keyboard
navigation supports tabs, form inputs, range controls and lifecycle step buttons. Chart
title/description and a full data table provide alternatives to visual inspection.
Reduced-motion preferences are respected. Missing data produce explicit empty states.

The primary outcome is demanding executable coordination work: a scoped allocation or
procurement protocol, typed domain, adversarial deviation checks and runnable evidence.
The seven-stage journey is Identify → Out-Learn → Out-Think → Out-Design → Out-Strategise
→ Out-Execute → Out-Evolve. French explanations translate each stage. The journey is
labeled a protocol to test, not evidence of demonstrated superiority.

## Interpretation

The demonstration distinguishes actual local implementation and finite tests from
simulated financial histories and fixture authority. It claims no live ENS enforcement,
customer sales, frontier-model job execution, confidential production encryption,
deployed contracts or zero-knowledge proofs. A copied capability is not counted as new
intelligence, and greater record counts do not by themselves establish a commercial loop.

The saved Python witness retains its original frozen identities and an explicit
post-confirmation replay-wrapper repair. The demonstration reads that evidence without
editing or rerunning it. The browser solver is an independent interactive illustration,
not an additional preregistered scientific confirmation.

## Beyond Beta interpretation

Beta is defined as expert frontier intelligence plus ordinary tools, prior experience
and reconstruction ability. Alpha is additional net mission advantage against that
versioned baseline and the recipient's already-held capabilities. No distinction is
inferred merely from the presence or absence of a file. The actual procurement witness
is labeled a retained candidate whose complete net advantage is unestablished: reduced
construction work and increased revalidation work are both shown. Trusted-attestation
savings remain a modeled condition. The graph's positive and negative dollar figures
are prominently labeled selected simulation-fixture inputs, not empirical Alpha.

The economic view includes saved sensitivity records concerning Beta improvement,
copying, obsolescence or useful lifetime. If these records have not been embedded it
states that explicitly, rather than inventing a decay curve.

## Verification actually performed

The reproducible verifier is `demo/verify_demo.mjs`. After rebuilding the HTML, run
`node demo/verify_demo.mjs` from the study root, or pass a generated HTML path as its
first argument. It uses Node built-ins only, embeds its nine recorded Python-oracle
cases, reads no temporary fixtures, writes no files, and reports the verified HTML's
SHA-256 identity. Its output explicitly distinguishes static interaction checks from
browser rendering.

The complete embedded JavaScript parsed and executed under Node 24.22.1 with a minimal
deterministic DOM stub. The original thirteen interaction checks passed in both a witness-only
pending edition and a separate temporary edition containing one actual saved development
run. The latter tested weekly cash, chart, slider, and data-table agreement; it was not
substituted into the delivered economic-confirmation dataset. Nine browser-solver input
cases independently matched the Python exact solver, including no-offer, zero-budget
and maximum supported finite domains. Other checks covered EN/FR labels, tab state,
all-member discovery, separate execution refusal, nested-name refusal, Beta invalidation,
fresh readmission, revocation, fixture-status labeling, bounds and offline resources.

The paid-work revision adds two checks for the journey and three-book accounting display,
and for source-job costs being read only from supplied records. All **fifteen** checks pass
in the revised pending-results edition and in a separate temporary v2 development
edition. The latter embeds one actual 30-week modeled run at seed 19, with two retention
records and zero separate invention investment, and verifies the A/B/C totals and source
cost display against its saved records. This is interface QA, not confirmation, and
does not use the fresh v2 study seed ranges. Confirmation data will be checked by the
same verifier after rebuilding.

These are code/interaction checks, **not browser rendering tests**. The installed
Playwright package lacked its Chromium executable. Automatic approval review rejected
downloading the missing browser, citing unapproved external resources and the user's
execution-bypass restriction. No retry or indirect bypass was attempted. Visual layout,
actual browser download behavior and cross-browser rendering remain unverified.

## Preserved prior confirmation presentation · 2026-10-27 UTC

The prior `demo/index.html`, now preserved under `evidence/editorial-priority-v1`, was rebuilt from the completed `results/demo_data.json`,
not from the development QA run. It contains all twelve prespecified illustrative
histories (three scenarios × four counterfactual arms; seed 770001), every saved week,
event and lineage record, the main aggregate results, and all 171 sensitivity arm
records covering 57 predeclared conditions. The sensitivity selector defaults to
`beta-fast`; users can inspect every condition. These sensitivities deliberately permit
retention and are distinguished from the policy selected in the main experiment.

The first screen states the primary negative result: Beta delivery is profitable only
under the stated modeled commercial assumptions, while incremental enterprise Alpha
from sharing is unestablished. It reads the favorable paired profit difference directly
from the summary: −$8,766, with a 95% Monte Carlo interval of [−$118,842, $101,310],
over 64 fresh worlds. This is simulation sampling uncertainty, not empirical market
confidence. Central and conservative selected delivery-only policies; favorable selected
retention without separate invention. No selected primary policy chose separate R&D.
Zero retention or zero C is a legitimate decision. Capability and invocation counts
are not presented as evidence of growth.

Both languages identify each displayed policy, whether retention and C are permitted,
and any additional restriction imposed by its counterfactual arm. Empty lineage records
do not falsely imply a failed retention assessment. The source-cost column describes
direct accrued mission cost, not collections. Its paired B column is the approved
upfront campaign budget, not the full B book: portfolio appraisal and subsequent
maintenance, distribution and reuse remain separately charged. All four cost books
reconcile to each run's accrued expenses.

The compact presentation omits 44,941 full ledger rows, 2,051 duplicated outcome rows,
and 41 detailed paired-probe arrays from the embedded copy. It preserves all original
weeks, events, lineage records and monetary totals. Sensitivity records retain the
displayed profit, useful outcomes, retention campaigns and separate investment metrics,
with their unchanged mean, lower bound, upper bound and sample count. The unabridged
source data remain unchanged in the evidence companion. The download control says
“Download demo data” and explains that its compact export is not that full companion.

The data provenance includes the raw input SHA-256, the protocol SHA-256, the freeze
time `2026-10-26T23:33:59.443862+00:00`, confirmation seeds 770001–770064 and sensitivity
seeds 780001–780016. Temporary UI fixtures do not inherit the main protocol identity.
The final graph remains the separately identified simulation fixture; its selected
positive dollar inputs are not an observed result of the mechanism witness. The
failure-memory step explicitly cannot authorize a positive capability selection.

`demo/ui_qa.json` records the final fifteen deterministic check groups. They now exercise
all twelve saved histories, all 57 sensitivity selections, the negative primary result,
English/French labels, selected-policy restrictions, cash at the beginning and end of
each run, A/B/C/common totals and the presence or absence of supplied source-cost records.
The nine independent Python-oracle examples and lifecycle/refusal checks remain. A
separate presentation-integrity receipt in that file compares the embedded projection
against the unchanged full input. No new simulation, model call, browser installation,
browser rendering claim or change to the frozen scientific implementation was made.


## Reporting amendment · profitable work first

The user's subsequent editorial instruction changes the demonstration's order and title
without changing a model, economic policy selection, seed, scientific protocol, or saved
outcome. The current title is **PROFITABLE WORK FIRST. COMPOUNDING CAPABILITY WHEN
WORTHWHILE.** Its French counterpart gives the same priority to profitable delivery and
the conditional accumulation of useful capabilities.

Before editing, the prior HTML, template, builder, verifier, QA receipt and this design
record were copied under `evidence/editorial-priority-v1`, with a preservation receipt.
The previous HTML SHA-256 is
`9979955ef2e483ce2e92faf57cc1df110fe280a11f9f2487e1ccb10f58deb4d9`.

The presentation now follows the requested decision sequence: useful customer outcome;
equivalent human-service reference; selling price; complete delivery and business costs;
profit and available surplus; job-born capability; incremental retention value; sharing
increment; and optional separate invention. Book A precedes the detailed profit view;
B follows the saved job lineage; and C follows the unchanged sharing comparison.

The leading commercial dashboard reads `results/commercial_core.json`, which is
read-only postprocessing of the original confirmation histories. It compares all three
Beta scenarios over 64 independent worlds each. Quoted prices and human references pool
completed-job quotes; they are explicitly separate from collected revenue and from useful
accepted-outcome margins. Human references follow the frozen scope/effort rule, not a
verified measurement of exclusively human effort. The selected network-family pricing
policy was applied unchanged to Beta; the demo does not claim separate optimization for
Beta.

The financial table includes A costs, common costs, total accrued expenses, unexpensed
closing obligations, profit, uncommitted closing cash, initial seed capital and the
illustrative reporting buffer. That buffer is
`max(0, min(profit, available_cash - initial_seed) - planning_floor)`;
it is not another expense, a newly selected policy, or an instruction to invest all cash.
The original scenario constraints and reserve policy remain unchanged.

A stricter retrospective calculation retains only modeled receipts attached to useful
outcomes while keeping every original expense and unexpensed closing obligation. Its
mean surplus is positive in each scenario. The conservative minimum world is negative
(−$30,128.78), which is shown beside the mean and interval; this is not described as a
guaranteed floor. Useful outcomes mean on-time, truly correct outputs within the
simulation's latent truth model, not observed client or provider validation.

The earlier sharing result is retained lower in the demonstration: favorable network
minus Beta profit remains −$8,766, with its unchanged 95% Monte Carlo interval spanning
zero. Job-born capabilities, retention events and graph entries do not prove a positive
enterprise increment. The witness's mixed construction/checking result and the graph's
simulation-fixture status also remain unchanged. Zero retention or zero C remains a
valid decision.

The compact embedded commercial register retains all scenario aggregates and metadata,
while omitting its per-world rows; the complete register remains separately available.
The builder records its SHA-256 and the editorial amendment. The same fifteen QA groups
now additionally verify the three commercial scenarios, consistency with the original
summary, the negative conservative useful-receipts world, the reporting-buffer labels,
English/French commercial priority and the required decision order. No browser rendering
claim is added.
