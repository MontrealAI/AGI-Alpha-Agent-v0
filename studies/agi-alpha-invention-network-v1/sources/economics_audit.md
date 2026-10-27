# Economic implementation audit and handoff

Audit date: 2026-10-27. The source is ready for the study owner to freeze. This audit did **not** create a policy freeze or execute the enterprise confirmation. Small synthetic unit worlds and an eight-week development-input smoke check were used only for implementation verification.

## Corrected material issues

- Full inverse/composition missions now use nested `composition.mission_records`, including sensor design, all forward calls and inversion. They no longer silently inherit single-forward-transfer timings.
- The competent inverse baseline is `competent_generalist`, including its ordinary D-optimal design tools. A recipient using a solver skill retains those tools; the fixed-sensor ablation is not used as the ceiling of competent Beta.
- Integer nano-USD retains the USD0.002 invocation charge and the much smaller numerical-compute charges. Earlier cent rounding erased both.
- Capacity and cash admission happen before serving and before fresh numerical outcomes are consulted. Refused orders pay no serving charge. A declared numerical budget and one correction are reserved before execution.
- Candidate decisions no longer use the true future upgrade date or hidden true job correctness. A candidate may be screened after observable acceptance, including a simulated false pass. The upgrade is acted upon only when it occurs.
- The primary screen first calculates an optimistic bound using ordinary baseline timing alone: even free elimination of all numerical subproblem cost must repay assessment, packaging and any admission. A negative bound rejects without consulting v1/v2 outcomes. This avoids giving optional Gym decisions a free preview of future learning. The bound concerns measured numerical-compute savings only; unmeasured reductions in human/model effort or increases in customer value are not credited.
- Forecast routing uses development evidence. Slower fresh runtimes and lower technical acceptance remain in realised outcomes; negative transfer has separate use and incremental-cost counters.
- Setup now appears in the exported ledger. Every world and stress arm exports its full event history to `all_histories.jsonl.gz`. An independent reconstruction checks cash, A/B/C costs, collections, refunds, no negative balance, seed exclusion and serving only on attempted jobs.
- Outstanding invoices are recorded at face value. Future default is not used to remove receivables before the due date. Collection fees and full refundable receipts are reserved separately. No borrowing is assumed; unfundable new operations close while existing invoices and warranties continue to settle.
- Expansion is a separate diagnostic. It uses lagged observed capacity-rejected orders, quoted margin and existing earned surplus; it does not inspect future arrivals. More resources are not described as compounding.
- Zero accepted/useful denominators yield null cost-per-outcome/false-pass rates, rather than silently using one fictional outcome.

## Disjoint campaign costs

The founder deliverable includes a reusable numerical engine. Its required solution generation, basis construction, verification and artifact write are charged exactly once in A on the first attempted founder thermal mission. Its development run was a computational experiment; no actual customer payment is implied.

Extra human retention assessment and packaging are B. Every numerical candidate assessment is B once, including all four candidate ranks (20, 28, 36, 44), nonselected ranks, and separate retention evaluation. Only additional Gym enrichment and estimated additional development labour are C. All rank evaluation is charged when the v2 campaign is elected, including forced diagnostic campaigns.

The recorded ordinary-baseline assessment interval contains both ordinary and v1/v2 work. The implementation partitions it rather than charging the entire interval in A and then charging v1/v2 again in B. Shared reference solves are paid once. Composition assessment similarly counts shared forward solver records once instead of adding their repeated appearance in multiple mission-level ablations.

A conservative one-second component-initialization allowance is an explicit **assumption**, separate from observed timing. The historical researcher/team labour and orchestration bill were not metered: actual total research cost remains unknown, not zero.

## Tariffs and service-price evidence

`economic_protocol.json` now gives exact assumed aggregate input/output/call budgets for Astra, Sol and Terra. At the sourced standard short-context input/output rates (USD10/50, USD2/10 and USD1/5 per million), the bundles reconcile exactly to USD66, USD96 and USD138. No cache saving is assumed. Output budgets include billed reasoning tokens. These are estimated workflow budgets, not API logs or evidence of entitlement.

Human operating/reviewer scopes are itemized separately from automated workflow occupancy. The USD84/hour service reference is sourced, while 72/96/120-hour mission scopes are estimates, not matched contract quotes. Processing at 3% plus USD0.30 is assumed. Numerical equipment at USD3.52/hour is a sourced service-rate proxy, not an observed host bill. All empirical, sourced, calibrated, assumed and simulated categories are enumerated in the protocol.

Exact copies of the earlier source deliverables are in this directory: `source_memo.md`, `primary_sources.json`, and `sources.bib`. The JSON and bibliography include the primary paper/PDF URLs, technical documentation, source limitations and retrieval date.

## Verification completed

- `python scripts/check_python_deps.py`: all required packages available.
- `python -m pytest studies/agi-alpha-invention-network-v1/test_economics.py --noconftest -q`: **16 passed**.
- `python -m ruff check studies/agi-alpha-invention-network-v1/economics.py studies/agi-alpha-invention-network-v1/test_economics.py`: passed.
- Ruff format with line length 120 completed. Black could not start because the environment's pathspec package lacks `pathspec.patterns.gitignore`; no dependency was changed to bypass this.
- Source-copy byte equality verified for all three copied documents.

The tests cover tariff reconciliation and context limits; subcent money; complete composition timing; independent ledger reconstruction; setup inclusion; no serving on capacity declines; finite-cash closure; future-obsolescence isolation; realised negative transfer; optional rejection with no mandatory Gym; ordinary-only upper-bound screening; founder A versus all-rank B versus Gym C; preservation of competent sensor-design tools; nonclairvoyant receivables; refunds and processing fees; zero denominators; and detection of a missing setup transaction.

## Owner commands

Run from the repository root. Freeze only after accepting the final protocol and source:

```sh
python studies/agi-alpha-invention-network-v1/economics.py --development studies/agi-alpha-invention-network-v1/technical_dev_final/results.json --output studies/agi-alpha-invention-network-v1/economic_confirm --freeze
python studies/agi-alpha-invention-network-v1/economics.py --development studies/agi-alpha-invention-network-v1/technical_dev_final/results.json --confirmation studies/agi-alpha-invention-network-v1/technical_confirm/results.json --output studies/agi-alpha-invention-network-v1/economic_confirm
```

The second command defaults to 200 worlds in each main profile and 100 per diagnostic, all five policies, and writes 8,500 complete histories. The optional `--worlds N` changes the number of Monte Carlo worlds; it must be declared if used for the final edition. Source, protocol, development results and training hashes are checked against the freeze.

Monte Carlo uncertainty remains conditional on assumed demand, prices, quality, labour and access. Profitable simulated Beta does not establish customer sales; locally observed numerical transfer does not establish autonomous invention, specialist ASI, trained proprietary model weights, live ENS authentication or a physical product.
