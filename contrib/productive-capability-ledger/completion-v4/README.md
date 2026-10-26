# Source assurance: full-envelope repair and operating record

The useful result is a source-change report: which of 1–128 explicitly named
public source files match a declared SHA-256 inventory, which differ, and the
complete proposed follow-up list. A customer can inspect the two inventories,
full difference/action CSVs, portable workspace and readable report. It does not
approve the behavior of source code or execute inspected code. The existing
[offering contract](../automation-v1/README.md), [automated economics](../automation-v1/AUTOMATED_ECONOMICS.md)
and [token boundaries](../TOKEN_BOUNDARIES.md) remain authoritative.

## What this repair delivers

Code Review finding 4372481330 on the combined #4899 source identified a real
failure: a permitted 128-attempt plan can finish with 258 retained artifacts,
while the independent verifier refused more than 256. The [before-fix failure](before-fixed-256-limit.txt)
and [original verifier](pre-repair-verifier.txt) are preserved. The current runner
and checker derive their inventory ceiling from 22 fixed files plus at most four
bounded metadata files per approved attempt (absolute 128 attempts). Metadata is
limited to 32768 bytes and payloads to 8000000 bytes; unknown artifacts refuse.
Writer acquisition retains its recovery guard until the durable reservation is
saved, preventing unreserved automatic crash-recovery cycles.

**210 local tests pass**:178 Node and 32 page/source/release-boundary Python tests.
The full-envelope regression actually checkpoints, records 116 STOP-refused
invocations, completes on reservation 118 with 258 files, passes 3,018 independent
Python checks and reconnects on 119. This is one regression fixture, not 118 jobs.
Ruff, Black and strict mypy pass on the changed verifier. These checks are local
component evidence, not full software qualification.

The [protocol](PROTOCOL.json) then freezes a current-code operating replication of
[the previously published five-path request](../completion-v3/previous-published-source.json).
It executes against public source 443246db and finds exactly the same three
intended source-version differences. The [independent result](independent-acceptance.json)
passes 353 checks. This is one operating replication of a prior declared request;
it adds no held-out diversity or extra customer demand. Its checkpoint, completion
and reconnect are one job. The [downloadable package](delivery-package.zip)
contains the actual outputs, scope, observations and acceptance record. The
[hash inventory](DELIVERY_SHA256.json) checks every package member. Previous
[v1](../completion-v1/README.md), [v2](../completion-v2/README.md) and
[v3](../completion-v3/README.md) snapshots are unchanged.

## Use and limits

Permitted inputs are ordinary, already present public Git blobs and one explicit
committed inventory. Acquisition of the public checkout is separate from offline
execution. Git 2.51.1 is tested. The exact approved plan records source, runner,
comparison dependencies, expiry, per-invocation time, total reserved time and
attempt allowance. Run the existing CLI to prepare a plan, inspect its finite
scope and approve that exact digest. Its [operating instructions](../automation-v1/README.md)
cover execution, STOP/pause, durable CANCEL, checkpoint recovery and output
verification. Missing blobs, changed methods, exceeded budgets, expiry, corrupt
history or interrupted recovery guards refuse with retained evidence. Partial,
refused or cancelled work is never an accepted deliverable. No automatic renewal
or permission expansion occurs.

The free [English/French local browser example](https://montrealai.github.io/AGI-Alpha-Agent-v0/try/)
remains available. It is distinct from this local Node source route and from the
configured authenticated planning executor. The existing installed profile's
closed methods support planning, construction and planning journeys; no
source-assurance transport adapter or approved Git profile has been added. The
exact approved operator home/profile is unavailable in this session. Real
operator authentication, browser-closure persistence, worker/network recovery
and a clean approved-profile install therefore remain NOT RUN for this increment.
Hosted fixtures must retain their own exact route and source labels.

## Acceptance and remaining dependencies

| Requirement | Verified state and next owner |
| --- | --- |
| Useful deliverable and finite local scope | Implemented; actual source outputs and independent checks retained here. Root/#4907 owner line. |
| Current-main integration | Existing #4899 includes #4907 through normal merge 4a491219; current inventory repair continues on #4899. Existing companion, five held source pins, 22 catalog records and historical editions preserved. Root is sole ref publisher through #4850. |
| Final Code Review and hosted checks | Required on the final published repair; pending at this immutable snapshot. Root requests the normal review and preserves adverse results. |
| Security | Historical exact4a tree has 57 findings/exit1; all 57 [source/rule/context notes](SECURITY_4A_CASES.json) remain UNAPPROVED with zero admissions. New finding is an observed-URL list append in a browser fixture; this assessment grants no waiver. Existing Security decision owner must determine permitted engineering dispositions. Original operator identity is not exposed in retained records. Final repaired source requires its own scan. |
| Authenticated installed execution | NOT RUN; exact existing approved operator installation/session required from its runtime owner. A source route additionally needs an implemented adapter and explicit profile adoption, beyond the current closed planning profile. |
| Persistent operation | Local checkpoint/lock/expiry/budget/STOP/CANCEL controls tested. Approved installed browser closure, worker restart and interrupted connected delivery remain NOT RUN here. |
| Successive capability cycle | Prior prospective source request and current replication retained. Human-authored repair; strongest practical conventional specialist remains incumbent. No autonomous discovery, profitable admission or acceleration established. |
| Automated economics | Shared alpha-automated-costs/v1 and mission-linked ledger preserved. Marginal/recurring/fully-loaded currency costs remain unknown without actual prices, total attempt costs, upkeep and attention. No precise savings ratio; matched human duration is unknown. |
| Surplus and token roles | Nontransactional ledger and separate USDC/AGIALPHA documentation preserved; actual collections, reserves and available surplus are unknown. No token transaction, distribution or appreciation claim. |
| Release and live publication | Not merged to main, not released, not newly live. Latest verified public software release remains v1.43.0. Existing accepted URLs/downloads preserved. Full software qualification and normal release/publication gates are required. |
| Original Harness/Fleet restrictions | Unchanged, original decision controls/operators retained. No held action retried, credentials added, persistent access created, financial commitment or security criterion changed. |

The [machine-readable acceptance record](VALIDATION.json) distinguishes these
states. Tests and process counters do not establish full currency cost,
commercial acceptance or customer savings. Every failed/interrupted attempt
keeps its evidence and its conservative allowance. The existing conventional
specialist is retained; failed or unproven improvements do not replace it.

## Français

Le résultat utile est un dossier de contrôle des sources publiques : inventaires,
écarts complets, actions proposées, espace portable et rapport lisible. Il ne
certifie pas le comportement du code inspecté. La correction permet de conserver
tout l’historique d’un plan de 128 tentatives : 258 fichiers et 3 018 contrôles
indépendants dans le test de reprise.210 tests locaux passent. Une répétition
opérationnelle de la demande publiée vérifie les mêmes cinq sources et trois
écarts, avec 353 contrôles indépendants. Cette répétition ne représente ni une
nouvelle clientèle ni une évaluation sur des données inédites.

Les limites de durée, tentatives et échéance sont explicites; STOP met en pause,
CANCEL annule durablement, et les résultats partiels restent refusés. L’exemple
web gratuit reste local. L’exécution authentifiée dans l’installation approuvée,
la persistance après fermeture du navigateur et l’installation propre ne sont
pas exécutées ici. La sécurité, la fusion, la publication et la mise en service
restent soumises aux contrôles existants. Les coûts complets, recettes, excédents
et gains économiques restent inconnus; aucune amélioration autonome n’est
présumée.
