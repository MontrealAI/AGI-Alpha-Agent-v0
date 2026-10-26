# Dependency refresh: the component evidence is ready

**Decision: preserve the current native lock; accept this component evidence for the next application qualification.**

The proposed Starlette 1.7.0 → 1.10.0 and Pydantic 2.13.5 → 2.14.1 refresh,
with pydantic-core 2.46.5 → 2.50.1, preserved the declared request-boundary
and mission-input behavior. FastAPI stayed at 0.141.1. Both before and after
environments passed all 61 source-grounded cases and independent verification.
The original FastAPI import bridge and actual 15-second timeout were exercised.

## What this enables

A maintainer can reuse the exact component lock, observations and independent
verification in the broader upgrade review, without reconstructing these specific
checks. The component patch is reviewable and replayable; it is not a qualified
replacement for the complete native application lock.

## Remaining work

Qualify the complete application dependency closure and supported platforms.
Run the authorized authentication, persistence and mission-execution checks.
Use the existing owner review and release acceptance process before adoption.
No application, credentials, Journal, settlement or operator action was created.

## Cost and demand

This was an internal project assessment, not a paid order. Actual collections are
zero. Complete delivery money, price, customer time and operator time remain
unknown. Setup, failed attempts, correction, execution, verification and package
assembly records are preserved. Runtime process quantities are not a bill or wage.

## Résultat utile

**Décision : conserver le verrou natif actuel et accepter ces preuves
de compatibilité des composants pour la qualification suivante.** Le changement
proposé conserve les comportements déclarés de la frontière des requêtes et de
la validation des entrées. Les 61 cas ont réussi avant et après le changement,
avec une vérification indépendante. Le chemin d'importation FastAPI d'origine
et le délai réel de 15 secondes ont été conservés.

Ce dossier permet au responsable de réutiliser les preuves exactes dans la revue
de mise à jour. La qualification complète de l'application, les contrôles
d'authentification et de persistance, ainsi que l'autorisation de publication
restent à effectuer. Le coût monétaire complet et le prix sont inconnus;
aucun paiement client n'a été reçu.

See decision.json for source links, exact versions, required actions and evidence
hashes. The full companion preserves environments, wheels, helper source and
primitive cost records; this folder is the readable decision packet.
