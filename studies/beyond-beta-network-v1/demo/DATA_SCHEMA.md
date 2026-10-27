# Paid work / retained Alpha — offline publication adapter

The demonstration binds executed frozen results. It is not a second simulator. All monetary values are USD dollars; canonical ledgers use cents. Missing results must never be replaced with invented outcomes.

## Main result view

Top level: `status: "bound_to_frozen_results"`, bilingual `headline`, `freeze_note`, `sources`, `scenarios`, `sensitivities`.

Each scenario: `id` (`conservative`, `central`, `favorable`), `worlds`, `human_price` (base reference), `seed`, `selected_policy`, `pricing` (executed development price-grid rows), and `policies`.

Each policy/arm record: `id`, bilingual `label`, `arm` (`beta`, `local`, `network`), `baseline_version`, matched useful-delivery-cohort `human_price` and `offer_price`, bilingual `offer_note`, `complete_cost`, `available_cash`, `adoption`, `acceptance`, `throughput`, `profit:{p05,p50,p95}`, `loss_probability`, `insolvency`, `useful`, `new_scope_useful`, `paired_gain`, `human_review_hours:0`, `queue_p95`, `capacity_refusals`, bilingual `quota_note`, `headline`, `learning_note`, `ledger_note`.

`adoption` means AI choice/contacted prospects before scope and capacity filtering. `acceptance` means useful accepted/attempted deliveries. `new_scope_useful` means work newly serviceable within the same-state deadline/capacity comparison, not new physical authority or recovery of unspecified intent. `paired_gain` must name its comparator in the explanatory note; Beta-to-network and local-to-network gains are distinct quantities.

`pricing:[{fraction,useful,profit,insolvency,selected}]` contains development-grid evidence. Fresh confirmation is not reused to select a policy. Human rates and hours, contingent payment terms, demand and buyer value are identified separately.

## The Alpha/network chain

Each policy includes:

`alpha:{candidates,admitted,false_admissions,retired,recipient_gain,network_available,baseline_note:{en,fr}}`.

`origin_job:{id,agent,title:{en,fr},paid_outcome:{en,fr},beta_work:{en,fr},restriction:{en,fr},candidate:{en,fr},already_paid:{en,fr},additional_retention:{en,fr},optional_research:{en,fr},evidence:{en,fr},admission:{en,fr}}` is one identified recorded demanding job/candidate example. It can be rejected. Its narrative identifies the recorded scenario/policy/seed, what the customer funded, the Beta work, development already charged in A, actual remaining B and optional C, and modeled net-Alpha assessment. A fallback explains that no candidate was earned in that trajectory; it may not manufacture a successful example. Optional C can explicitly say no separate project was chosen. A and B are not charged twice.

`accounting:{a_paid_work,b_retention,c_optional_research,common_business,total_resource_cost,net_collections,a_recharged:0,note:{en,fr}}` provides the complete enterprise expense partition, preferably mean USD per independent world over the full horizon, with that statistic and treatment of failed jobs/obligations named in `note`. `total_resource_cost = a_paid_work + b_retention + c_optional_research + common_business` within displayed rounding. `a_recharged` must be zero. All A costs remain in consolidated profit; only remaining B/C costs enter prospective retention assessment. Refund principal is contra-revenue, not a duplicate resource expense. This panel's mean expense must not be subtracted from median profit or presented as a representative path.

`recipients:[{id,baseline:{en,fr},availability:{en,fr},adoption:{en,fr},fresh_useful,incremental_gain,adaptation_cost}]` distinguishes whole-network discoverability from optional actual use and net recipient benefit. No additional agents or compute are introduced to make the sharing arm win. Costs and gain units/statistics must be named in `network_note:{en,fr}`.

`beta_phases:[{week,label:{en,fr},baseline:{en,fr},admitted_eligible,retired,incremental_gain,note:{en,fr}}]` contains recorded phase snapshots or executed paired baseline comparisons. The phase selector only changes the displayed recorded evidence; it does not rerun a frontier simulation. `note` distinguishes a trajectory snapshot from a causal paired comparison.

`lifecycle_note:{en,fr}` explains admission rules, direct-label eligible authenticated agent attestations, version/scope/dependency/freshness checks and revocation/supersession. Actual implemented tests are named separately from simulated economic validation. Existing club roles and settlement remain unchanged.

## Investment, cash and independent invention

`capabilities:[{title,description,status,available,complete_cost,falsifier}]`, bilingual text fields, reports simulated assets and **complete additional B/C** cost, including paid assessment and the explicitly named lifecycle horizon. `description` identifies the paid-work source and any separately optional research. A already paid is retained in the job/consolidated ledger and is not recharged here. No fixed investment count or positive outcome is required.

`events:[{week,title,description,amount}]` and `cash_timeline:[{week,cash,available,investment_spend}]` describe one identified recorded world; include paid-job acceptance/collection, B retention, optional C, hold/defer/abandon as applicable. `investment_spend` is cumulative B/C capability spending with exact included categories named in `ledger_note`. `ledger_note` identifies the trajectory. It is not called the median path unless selected by a specified median criterion. Available cash and collection timing precede B/C commitments; future receipts are not present cash.

`campaigns:{count,useful_probability,cost_per_useful}` refers to fresh independent invention campaigns, never descendant jobs. `learning_note` states the experiment, amortization, capacity and zero-effect-control limits; more job volume does not establish self-acceleration.

## Sensitivity, evidence and analytic control

`sensitivities:[{title:{en,fr},note:{en,fr},rows:[{scenario,label:{en,fr},profit,insolvency}]}]` contains executed stress outputs, including moving Beta and Alpha erosion where available. If a panel is only for central, the other scenario views explicitly say so.

`sources:[{title:{en,fr},url,note:{en,fr}}]` links official prices, published human bill rates, source research, the governing manuscript and frozen protocol/results.

The isolated analytic contingent-price ceiling is `[s q V − B − (1 − s q) D] / s`. Completion belief `s`, conditional correctness `q`, useful value `V`, burden `B` and extra failure harm `D` are assumptions; `D` excludes lost `V`. Other alternatives can imply a lower ceiling. At `s=0` no payable outcome exists. This control never changes frozen results.

The artifact is one offline HTML file with inline data, CSS and JS. Final QA covers EN/FR, scenario/arm/phase/sensitivity controls, responsive layout and no network dependency.

## Separate development illustration

The top-level `development_witness` object contains a selected, recorded capacity-development world, not confirmation. It has an `identity`, bilingual `note`, six bilingual `stages`, and a bilingual `result`. It is unchanged by the primary scenario controls, explicitly discloses post-selection and negative complete economic return, and is never pooled into primary or capacity holdout statistics.

## Final rendering qualification

The sensitivity selector always displays the executed central-policy stress family, independently of the primary scenario control. Its note identifies this boundary. The isolated analytic buyer calculation does not alter frozen result data. `qa/verification.json` binds the tested HTML and JSON hashes and checks all scenario/policy/Beta-phase controls, A/B/C display, the separate negative development illustration, English/French labels, responsive overflow and offline operation. These are publication checks, not empirical capability validation.
