# AGI ALPHA — one useful component-compatibility decision

**The proposed dependency refresh preserved the declared request-boundary and
mission-input behavior. Keep the current native application lock while the
remaining application and release qualifications are completed.**

Start with the [corrected decision packet](results/development/first-delivery-corrected/READ-ME.md).
Its [machine-readable decision](results/development/first-delivery-corrected/decision.json),
[exact component-lock patch](results/development/first-delivery-corrected/proposed-component-lock.patch),
and [replay command](results/development/first-delivery-corrected/reproduce.txt)
give the maintainer a bounded next action and inspectable evidence.

## The completed useful work

The actual native profile pins Starlette 1.7.0 and Pydantic 2.13.5. This internal
assessment evaluated Starlette 1.10.0 and Pydantic 2.14.1, including the required
pydantic-core change from 2.46.5 to 2.50.1. FastAPI remained 0.141.1. Both exact
ten-package environments passed all **61 enumerated cases** and the separately
authored verifier. The original FastAPI import bridge, original consumer bodies,
actual 15-second request timeout, security headers, exact forwarded bytes, and
the listed strict Mission/Review/Control input behaviors were exercised.

The maintainer can carry this component evidence and executable lock patch into
the broader upgrade assessment. Complete application closure, supported platform
qualification, authentication, persistence, mission execution, owner approval,
and required release gates remain separate. No Alpha app factory, Journal,
credentials, operator action or financial transaction was activated. This is an
internal project assessment; customer acceptance and paid demand were not observed.

| Exact artifact | Purpose |
|---|---|
| [Component contract](protocol/component-contract.json) | Input cases, expected observations, finite scope and acceptance policy |
| [Contract rationale](protocol/component-contract-rationale.md) | Source-grounded reasoning and limitations |
| [Import projections](protocol/component-projections.json) | Original FastAPI bridge and preserved provisional predecessor |
| [Consumer and native lock identities](publication/current-consumer-identities.json) | Exact source bytes, Git blobs and current source links |
| [Corrected artifact manifest](results/development/first-delivery-corrected/artifact-manifest.json) | Exact packet file identities |
| [Correction receipt](results/development/first-delivery-corrected/correction-receipt.json) | What changed, what stayed identical, and correction assembly cost |
| [Outer handoff index](publication/source-handoff-artifact-index.json) | Binds the inner manifest, assembly receipt, correction receipt and source handoff |

The consumer experiment is pinned to Alpha commit
`eb07086ac42799ff45f7b1c946a2f7c514bd3bbc`. The same consumer, repository test and
native lock Git blobs were independently verified at current main
`92064005b55d4fec0effbb2acacc8403bb551f3e`; that equality does not make the
newer main a new experimental source or prove release qualification.

## Runnable reproduction

Use **Python 3.12 on Linux x86-64**. From this study directory, with a fresh
writable output path:

```sh
python publication/replay_first_delivery.py --out /tmp/agialpha-first-delivery-replay
```

This source-only handoff contains exact package metadata and hashes. The command
fetches the declared public wheels, checks their identities, then installs from
local files with `--no-index --require-hashes`. It creates relocated plans instead
of editing the original receipts. It runs the unchanged component recorder and
the independent verifier and saves all new records. Expect at least 30 seconds
of deliberate timeout observation plus setup.

With the complete companion's development wheels present, append `--offline`.
The source-only public draft contains **no wheel binaries, PDF, private guidance
documents, deployment, or release asset**. It is not the complete offline archive.
The packet's original execution receipts retain their original absolute paths
as historical evidence; the replay helper is the runnable relocation path.

Expected replay disposition is `PRESERVED_WITHIN_COMPONENT_CONTRACT`, with
61 PASS, zero INCOMPLETE and zero BEHAVIOR_MISMATCH on each side. This repeats
the exposed development mission and creates no additional customer-job count.

## Cost and corrections

Actual customer collections are **zero**. Full marginal, recurring and loaded
monetary cost, price, customer time and residual operator time remain unknown.
Recorded execution and setup quantities are evidence, not an inferred bill or
human wage. Preparation, failed attempts, review, corrections, execution,
verification, assembly and replay have separate records; the later economic
analysis must include all attributable activities.

The [historical original packet](results/development/first-delivery/READ-ME.md)
is preserved byte-for-byte, including its original assembler. The corrected
edition changes only native-profile wording and runnable replay guidance. The
original's phrase “production lock” was imprecise: the evidence establishes a
native source profile, not a deployed production service. The decision, cases,
observations, verification and source bytes are unchanged. See the
[exact reporting diff](publication/first-delivery-correction.diff).

The earlier eight-package direct-Starlette environment remains historical
development evidence. Independent review required the original FastAPI bridge,
so the accepted component packet uses the corrected ten-package environments.
A failed logger attempt and other recorded construction corrections are retained
and charged; they do not become new missions or disappear from the cost basis.

## Integration handoff

The product owner acknowledged this single research contract and comparison in
[issue #4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6419136075).
The narrow importer can consume `alpha-component-decision/v1`, the exact evidence
list and hashes, and the acceptance/scope fields. An internally verified
component disposition must not become customer acceptance, release approval,
or operator authority during rendering.

This additive namespace is `studies/agi-alpha-useful-work-v2/`. The proposed
draft branch is `research/agi-alpha-useful-work-v2-20261026`. Runtime adoption,
source integration and publication remain with their existing owners. The
[publication gate record](publication/publish-gates.md) distinguishes this
reviewable source draft from a released service or published paper. No live
publication is claimed by this local handoff.

## Résultat utile

**Le changement proposé conserve les comportements déclarés des composants.
Conserver le verrou natif actuel pendant la qualification complète de
l'application et de la version.** Les 61 cas ont réussi avant et après le
changement, avec les sources et dépendances exactes, le chemin FastAPI d'origine
et le délai réel de 15 secondes.

Le responsable peut réutiliser ce dossier et son correctif de verrou des
composants pour la suite de la revue. L'authentification, la persistance,
l'exécution des missions, les autres plateformes et l'autorisation de publication
restent hors de cette preuve. Aucun paiement client n'a été reçu; le coût
monétaire complet reste inconnu. Cette remise contient les sources et les
preuves textuelles; l'archive complète hors ligne est un livrable distinct.
