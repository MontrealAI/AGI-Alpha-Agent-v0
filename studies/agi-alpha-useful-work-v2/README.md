# AGI ALPHA — The Decision That Carries Its Evidence

## The useful outcome

**A maintainer receives an evidence-backed component decision and an exact proposed component-lock patch.** For the first completed native-profile assessment, the proposed Starlette and Pydantic refresh preserved the declared request-boundary and mission-input behavior. The next action is to carry this evidence into full upgrade qualification and retain the current native application lock until the remaining gates are met.

Start with the [English/French demonstration](publication/AGIALPHA_Useful_Work_Demo.html), the [completed decision packet](results/development/first-delivery-corrected/READ-ME.md), its [decision JSON](results/development/first-delivery-corrected/decision.json), and its [exact component-lock patch](results/development/first-delivery-corrected/proposed-component-lock.patch). The self-contained demonstration includes downloadable copies of the original completed packets. Open the downloaded HTML locally to use it.

The intended user is the maintainer of AGI ALPHA's native Python agent. A substantive source, dependency or requirement change can trigger a new assessment. An identical valid whole request is a no-op. The need is observed inside this project; the six historical confirmation transitions are representative maintenance missions. Customer acceptance, orders, recurrence of purchases and payment have **not** been observed.

The accepted deliverable binds original consumer definitions, exact dependency versions and wheels, the finite behavioral contract, before/after observations, independent verification, execution receipts, the decision, a proposed component-lock patch and reproducible commands. A complete verified regression is also a useful hold decision. Missing or stale evidence cannot qualify as a complete decision.

## What was established

| Question | Observed answer |
|---|---|
| What did the first assessment cover? | Original RequestBoundary and enumerated Mission/Review/Control input behavior through the original FastAPI import bridge; 61 required cases in each exact environment. |
| What changed in that assessment? | Starlette 1.7.0 to 1.10.0; Pydantic 2.13.5 to 2.14.1; required pydantic-core 2.46.5 to 2.50.1. FastAPI remained 0.141.1. |
| Did the work produce a reusable capability? | Yes: an evidence-bound automated producer, run through the existing local SUCCESSOR Ω Workbench, with source/environment custody and independent verification. |
| Did it help fresh work? | All six frozen historical missions produced complete scoped-preservation packets in each of three arms. The researcher-assisted workflow required six explicit finalizations; both reusable builders required zero. |
| Was it better than a capable conventional builder? | No practical method superiority was established. The independent ordinary unittest/package builder also completed all six. |
| Did the investment repay? | Not established. Complete monetary cost, active human effort, maintenance, justified utilization and customer price remain unknown. Actual study customer collections are zero. |

Six missions generated **18 arm evaluations**, not 18 customer jobs. Each profile's 61 assertions are coverage checks, not additional missions or independent defect families. No real dependency regression was found in the six confirmation transitions. Synthetic negative controls are labeled separately.

### Primary comparison

| Measure | A: researcher-assisted | B: retained producer | C: conventional builder |
|---|---:|---:|---:|
| Accepted scoped packets | 6/6 | 6/6 | 6/6 |
| Explicit per-mission researcher finalizations | 6 | 0 | 0 |
| Median complete service span, seconds | 36.220 | 16.554 | 16.628 |
| Median mechanical delivery, seconds | 16.310 | 16.506 | 16.576 |
| Median measured local CPU, seconds | 1.786 | 2.043 | 2.085 |
| Complete monetary delivery cost | Unknown | Unknown | Unknown |

A's service span includes response and scheduling intervals. It is **not active human labor** and is not priced as a saving. The actual original 15-second body timeout supplies a mechanical floor. One run per arm and mission on a shared host does not establish a generalized reliability rate or a timing advantage over C. A was constructed during this study with researcher assistance and legitimate reusable tools; it is not an observed no-AI human service benchmark.

## Paper, evidence and costs

- [Publication-ready paper PDF](publication/AGIALPHA_The_Decision_That_Carries_Its_Evidence.pdf) and [LaTeX source](publication/paper.tex).
- [Capability asset card](publication/capability-asset-card.md): implementation, support, evidence, rights, costs, fallback and retirement.
- [Frozen primary protocol](protocol/primary-protocol.json), [83-file source freeze](protocol/source-freeze.json), [selection record](discovery/confirmation-metadata-v1.json), and [execution-driver seal](protocol/execution-driver-seal.json).
- [Complete campaign](results/confirmation/campaign.json), [primary economic tables](analysis/economic-publication-tables-01.json), and [independent source/custody audit](results/review-controls/postcampaign-custody-v3/review.json).
- [Economic snapshot 02](results/economic-analysis-02/summary.json) and its [canonical economic output](results/economic-analysis-02/canonical-economics/economics.json). These retain unknown monetary inputs and an economic HOLD.
- [Creator–critic–verifier corrections](discovery/retained-candidate-review.md), [final manuscript correction review](publication/independent-manuscript-corrections-review-02.json), and [bilingual product review](publication/primary-product-review.md).
- [Exact-source ecosystem and rights review](discovery/ecosystem-and-rights.md), [companion rights](publication/companion-rights.md), and [prior manuscripts](history/prior-papers/PROVENANCE.json).

The same finite capability account includes discovery, unsuccessful attempts, both builders, common verification, import-closure corrections, acquisition, integration, scrutiny, delivery and publication. Snapshot 02 closes at 2026-10-26T15:42:59.393708Z. Final archive verification, publication and delivery are recorded in a separate delivery-cost supplement extending that same account. A sealed archive cannot include the subsequent cost of its own final delivery; this is an explicit accounting boundary, not an assertion that those activities are free. Primary outcomes remain immutable.

Marginal execution money, recurring delivery money at justified utilization, fully loaded money, customer price, remaining customer effort, reserve requirement and available surplus are unresolved. The canonical accounting adapter retains unknowns. Customer benefit is separate from enterprise revenue; zero observed collections does not establish zero outstanding costs. A wage-based break-even formula is provided without inventing a human duration or a service price.

## Reproduce the actual result

Use Python 3.12 on Linux x86-64 and Node.js. The **full companion** contains exact wheel binaries, public metadata, licenses and source closure for offline replay. From its extracted `agi-alpha-useful-work-v2` directory:

```sh
python publication/verify_companion.py --root .
python publication/replay_mission.py --mission pydantic-3 --arm conventional --out reproduction/pydantic-3-conventional
```

Use `--arm retained` and a different fresh output directory for B. Valid frozen mission names are `starlette-1`, `starlette-2`, `starlette-3`, `pydantic-1`, `pydantic-2` and `pydantic-3`. The helper verifies the freeze, relocates only local paths, rebuilds exact environments from supplied wheels, runs the original behavior and independent verifier, and preserves new receipts. Output must be a new directory within the extracted study. A replay is labeled reproduction and adds **zero new missions**.

The copied-root Pydantic-3 conventional replay already completed offline, with no HTTP requests and unchanged frozen source. Its [execution receipt](publication/relocation-qa-execution.json) and [closure inclusion audit](publication/replay-closure-inclusion.json) are preserved. This verifies that example and its closure; it does not imply every platform or every replay was newly executed.

To reproduce the exposed first delivery with supplied development wheels:

```sh
python publication/replay_first_delivery.py --out /tmp/agialpha-first-delivery-replay --offline
```

The separately labeled **source/evidence edition omits wheel and Ruff binaries and is NOT_OFFLINE_COMPLETE**. It retains source, original results, metadata, requirements, negative evidence, paper and demo. Do not use it to claim offline execution readiness. The complete offline companion is a separately delivered archive with its own exact manifest and verification receipt.

## Operating and integration boundaries

The original consumer is pinned to Alpha commit `eb07086ac42799ff45f7b1c946a2f7c514bd3bbc`. Equal relevant source and native-lock Git blobs were checked at `92064005b55d4fec0effbb2acacc8403bb551f3e`. Equality of those blobs does not establish release or production qualification.

All 12 B/C local native runs retain HOLD, empty authority, disconnected settlement, historical-import inspection status and no active source proof. The pure-component probe does not create the full application, Journal, credentials, an operator profile, or any transaction. Authentication, persistence, whole mission execution, platform qualification, full lock resolution and release approval remain outside this component assessment.

The product owner retains `contrib/upgrade_decision`; the integrator retains adoption, release and publication. The [producer compatibility note](publication/producer-schema-compatibility.md) documents actual field differences under the shared `alpha-component-decision/v1` label. The first-packet importer must not be assumed to accept all fresh producer layouts or all negative outcomes without its own qualification. This study has not supplied a competing importer or runtime.

Coordination is in [issue #4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850). The research handoff is [draft PR #4932](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4932), in the additive `studies/agi-alpha-useful-work-v2/` namespace. Reviewable branch artifacts are not an adopted release, production service or live Pages publication. See the [final publication boundary](publication/final-publication-boundary.md), which preserves the earlier source-only handoff as history.

The separate commercial reviewer is reusing this frozen comparison and current product lane. The next justified small test is a real pending matching maintainer decision, with observed use/acceptance, measured active effort under competent ordinary tools, complete applicable billing, and a separately established price/demand signal. No new customer outreach, purchasing, payment or funding is authorized by this study.

## Preserved correction to the preceding companion

The original *The Next Upgrade* companion ZIP is preserved but incomplete. Its old 1,873-entry complete-verification claim is withdrawn for that original hash. A separately named corrected edition was built from the unchanged original inventory and independently extracted and checked. See the [correction](publication/v1-companion-correction/README-correction.md) and [verification](publication/v1-companion-correction/corrected-verification.json). Original source, papers and experimental findings remain unchanged; recovery cost belongs to the prior-delivery recovery account.

## Résultat et usage en français

**Le responsable reçoit une décision de compatibilité limitée aux composants, ses preuves et un correctif exact du verrou des composants.** Le premier dossier conserve les comportements déclarés avant et après la mise à jour proposée. Il permet de poursuivre la qualification complète; le verrou natif actuel reste à conserver jusqu'aux validations requises.

La démonstration est bilingue et contient sept dossiers téléchargeables: le premier exemple de développement et les six missions historiques de confirmation. Les trois méthodes ont produit six dossiers complets chacune. Les deux méthodes réutilisables ont supprimé la finalisation explicite du chercheur par mission. La méthode conventionnelle reste une solution solide; aucune supériorité économique ou algorithmique sur celle-ci n'est établie.

Les coûts monétaires complets, l'effort actif du client, le prix, la demande payante et le remboursement de l'investissement restent inconnus. Aucun paiement client n'a été observé. Les secondes de réponse du chercheur ne représentent pas des minutes de travail facturables. Les recettes, la trésorerie disponible, les économies du client et la valeur de l'entreprise restent des mesures distinctes.

La prochaine validation utile porte sur une décision réelle en attente, avec acceptation observée et mesure de l'effort et des coûts applicables. Les résultats locaux ne confèrent aucune autorisation d'exploitation, d'adoption ou de transaction.
