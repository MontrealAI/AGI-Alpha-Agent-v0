# Resilient Placement Decision Pack

Obtain a named, checkable placement of two replicas per service across declared failure domains, or an exact infeasibility finding. The package includes a CSV plan, capacity totals, independent finite verification, an English/French report, original inputs, execution evidence and file hashes.

This is a working local research delivery on the existing #4985 execution/accounting stack. It is not an activated customer service. The model is scripted, tools execute locally, inventories are research-authored, research acceptance is independent of customer acceptance, actual collections are USD0, and complete actual cost/profit remain unknown.

## Begin with the supported brief

From the repository root, in the existing qualified development environment:

```sh
python -m contrib.resilient_placement_delivery check contrib/resilient_placement_delivery/examples/bilingual-publishing.json
python -m contrib.resilient_placement_delivery deliver contrib/resilient_placement_delivery/examples/bilingual-publishing.json --output ../my-placement-delivery-01
python -m contrib.resilient_placement_delivery verify-pack ../my-placement-delivery-01/pack
python -m contrib.resilient_placement_delivery economics --output ../my-placement-economics-01.json
```

Choose a new output directory for each distinct brief. Open `pack/index.html` locally. Its links download the exact CSV, input, decision, execution and manifest. `examples/regional-analysis.json` supplies a distinct second mission under the same operating configuration. Replace only inputs you are authorized to use. Do not place secrets, provider credentials or private customer data in a public example or review packet.

The schema requires unique named hosts, their capacities/failure domains, named service demands, and one nonnegative objective cost for each host/service pair. These are declared planning units, not the offering price or observed provider spending. Exact integers prevent silent rounding. The exhaustive acceptance budget is `C(hosts,2)^services <= 100000`; larger jobs are refused before execution. There is no approximate-success fallback.

## What is implemented

The wrapper uses the existing `MissionExecutor`, `PlacementEnvironment`, `PlacementWorkflow`, `Journal`, `DurableCheckpoint`, `ProtectedLibrary`, finite acceptance adapter and `CostLedger`. It creates no alternative solver, registry, customer ledger, token settlement or publisher. The brief commitment binds names and units to the numeric execution; packaging independently rechecks the result and saved tool observation. Canonical export verification detects a changed report/CSV even when its local manifest is rehashed. A manifest establishes byte consistency, not the authority of a separately imported journal.

Two records are deliberately distinct. The primary execution retains unknown actual costs in its original ledger and refuses native acceptance/earning. It still yields independently checked research artifacts. A separate, prominently labeled synthetic conformance journal executes deposit → unknown-cost refusal → fictional cost reconciliation → native research acceptance → synthetic earning → refund due → refund. Fictional money never becomes actual revenue or cash. This exercises the complete accounting controls without pretending to have metered a business.

Output directories contain private runtime identity keys and API tokens created by the existing Journal. Keep `actual/journal`, `synthetic-conformance/journal` and checkpoint databases private. Publish only the enumerated safe export files and `pack/`; do not upload or archive the entire output tree. Ephemeral role/encryption keys are not exported. Public-role metadata is not live ENS authentication. All identity-reader calls in this harness refuse.

## Price and complete economics

[OFFER.json](OFFER.json) freezes the beneficiary, deliverable, scope, correction terms, turnaround and price hypotheses. USD150/250/400 are hypotheses, with USD250 as the cautious reference, not an observed willingness to pay. The equivalent human-service estimate is three hours at USD100/hour plus 20% overhead: USD360, with USD180–720 uncertainty. Both pathways reuse existing software; no bespoke solver development is priced into that comparison.

The existing arrangement engine accounts for successful/failed attempts, model/tool/compute/storage/network allowances, packaging, checking, correction, automated support, acquisition, infrastructure, maintenance, processing, payment default, refunds, reserves and prefunding. The automated tier imposes no fictional human reviewer. A delivery's learning is not charged again in retention. B/C investment is zero because optional retention is not admitted. Actual research development remains unknown and outside modeled operating profit; complete project return remains unknown.

The baseline has positive modeled per-order contribution but negative modeled operating profit at low volume. Zero demand, acceptance, price, workload, acquisition, failure and liquidity sensitivities remain visible. The separate higher-volume profitable-but-underfunded scenario is conditional on unobserved buyers and performance. It is not the default evidence of real profitability, and all arrangements HOLD. See the exported economics JSON for exact assumptions, rational amounts and break-even thresholds.

## Operating limits, cancellation and recovery

No live provider call, deployment, customer outreach or payment occurs. No schedule or recurrent trigger is enabled because no permission-cleared recurring buyer workload has been established. [model-profiles.json](model-profiles.json) records current official model identifiers/capabilities and public rate references; it grants no account access or spending authority. Live use remains with the existing provisioned Responses transport, exact profile and signed permit, served-model qualification, quota, billing and scoped operator approvals.

The existing executor enforces signed request/profile/environment/configuration bindings, action/turn/time budgets, persistent stop control and no uncertain replay. Duplicate execution is refused before another tool action. Exact accounting retries are idempotent; a second operation cannot reuse earning evidence. An incomplete search issues no accepted pack, no earning, and returns the synthetic unearned deposit. A failed output retains its evidence; rerunning the CLI does not overwrite it.

To stop an active research runtime, use the existing `Journal.control(True)` through its authorized operator and preserve the checkpoint. Restart from the same state only after the existing journal/checkpoint checks; do not make a fresh permit to hide an uncertain attempt. The wrapper intentionally does not export signing/encryption keys for portable service recovery. Its private state is local research custody, not a production disaster-recovery qualification. A pack interrupted during publication retains `INCOMPLETE`; reject it, preserve it, and produce a separately identified correction after reconciliation.

Rollback is additive: cease invoking this contrib command and retain its immutable evidence. Existing routes, runtime source, papers, workers, versions, contracts and settlement roles are unchanged. Parent merge, full resulting-main qualification, release identity, installed platform/browser checks and canonical deployment remain with the active integration/publication owners. A local pass or source-review PR is not a released installation.

## Conventional alternatives and attribution

Fault-domain scheduling and capacity-constrained assignment are established techniques. Kubernetes [topology spread constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/) and [OR-Tools task-size assignment](https://developers.google.com/optimization/assignment/assignment_cp) are competent alternatives. This pack does not claim a new optimizer, superior scheduling, or a Kubernetes controller. Its small exact independent oracle verifies this finite formulation, not real infrastructure resilience. An ordinary library using the same solver can reproduce the answer. The proposed value is preparation, checked delivery and accountable records; demand and advantage remain unmeasured.

## Evidence handoff to the writer

The review evidence includes both distinct briefs, complete safe execution exports, research acceptance/refusals, exact manifest and source identities, synthetic accounting transitions, conditional economics, tests and a precise release disposition. These are engineering evidence for the existing paper author, not a new efficacy sample from a paying customer. Credit for any accompanying paper: Vincent Boucher — President of MONTREAL.AI. Independent same-session model review is distinct from external peer review, maintainer approval and live authenticated agent authority.
