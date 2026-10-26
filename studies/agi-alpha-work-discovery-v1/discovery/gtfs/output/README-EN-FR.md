# REM schedule-ingestion decision / Décision d'importation du réseau REM

**SCOPED-STRUCTURAL-PASS — scoped structural checks only / contrôles structurels limités.**

This packet answers whether the exact published REM archive supports a reproducible local schedule-ingestion decision
for 26 October–1 November 2026. It preserves the original archive, canonical validator receipts, all warnings and
explicit calendar expansion. It does not certify actual service, operational suitability or publisher acceptance.

Ce dossier évalue le fichier REM exact pour une décision reproductible d'importation des horaires du 26 octobre au
1er novembre 2026. Il conserve l'archive originale, les résultats du validateur officiel, les avertissements et les
calendriers développés. Il ne certifie ni le service réel ni l'acceptation par l'exploitant.

## Decision and useful action / Décision et action possible

The canonical validator reports 0 errors, 1565 warning instances and
1 informational instance. There are no runtime/system notices. Every requested local service date has
scheduled trips. An application maintainer can proceed to its own staged import, with the warnings below retained for
review. Do not remove unreferenced stop records or repeated shape coordinates without publisher/context assessment.
No deployment, public notification or provider modification was performed.

Le mainteneur peut préparer son propre import de validation, en conservant les avertissements ci-dessous. Ne pas
supprimer automatiquement les arrêts non référencés ou les coordonnées répétées. La vérification des horaires publiés
aux voyageurs et les essais dans le planificateur cible restent nécessaires.

## Exact source / Source exacte

- Publisher / Fournisseur: Réseau express métropolitain, https://rem.info/fr .
- Original feed / Flux original: https://gtfs.gpmmom.ca/gtfs/gtfs.zip .
- Captured archive / Archive capturée: `inputs/rem-20261026.zip`.
- Feed version / Version: `20260520`.
- SHA256: `9263a39e4dff0ee8d1ffb23bacb0884bad90e86cb44f80c6b0b3c7cd18d3b577`.
- License / Licence: CC BY 4.0, supplied unchanged in `__Licence.txt`; https://creativecommons.org/licenses/by/4.0/ .
- Derived summaries / Résumés dérivés: AGI ALPHA research; no publisher endorsement / aucune approbation de l'exploitant.

## Local service-date evidence / Service par date locale

Counts are scheduled trips from `trips.txt` whose service is active after calendar exceptions. There is no
`frequencies.txt` in this archive. First/last times are **origin departures across both directions**, not departures from
every station. GTFS values beyond 24:00 refer to the same service day and are preserved. The window includes the local
daylight-saving transition; no naive UTC conversion is performed.

Les nombres correspondent aux trajets planifiés après les exceptions de calendrier. Les heures sont les départs aux
origines, dans les deux directions, et non les passages à chaque gare. Les heures supérieures à 24 h restent associées
au jour de service. Aucune conversion UTC n'est effectuée.

| Service date | Route | Scheduled trips | First origin departure | Last origin departure |
|---|---|---:|---|---|
| 2026-10-26 | S1 | 220 | 05:30:00 | 24:51:31 |
| 2026-10-26 | S2 | 61 | 05:37:40 | 18:35:55 |
| 2026-10-26 | S3 | 162 | 05:30:00 | 24:36:35 |
| 2026-10-27 | S1 | 220 | 05:30:00 | 24:51:31 |
| 2026-10-27 | S2 | 61 | 05:37:40 | 18:35:55 |
| 2026-10-27 | S3 | 162 | 05:30:00 | 24:36:35 |
| 2026-10-28 | S1 | 220 | 05:30:00 | 24:51:31 |
| 2026-10-28 | S2 | 61 | 05:37:40 | 18:35:55 |
| 2026-10-28 | S3 | 162 | 05:30:00 | 24:36:35 |
| 2026-10-29 | S1 | 220 | 05:30:00 | 24:51:31 |
| 2026-10-29 | S2 | 61 | 05:37:40 | 18:35:55 |
| 2026-10-29 | S3 | 162 | 05:30:00 | 24:36:35 |
| 2026-10-30 | S1 | 220 | 05:30:00 | 24:51:31 |
| 2026-10-30 | S2 | 61 | 05:37:40 | 18:35:55 |
| 2026-10-30 | S3 | 162 | 05:30:00 | 24:36:35 |
| 2026-10-31 | S1 | 158 | 05:30:00 | 25:21:31 |
| 2026-10-31 | S2 | 7 | 05:37:40 | 25:26:29 |
| 2026-10-31 | S3 | 158 | 05:36:42 | 25:06:30 |
| 2026-11-01 | S1 | 154 | 05:30:00 | 24:51:31 |
| 2026-11-01 | S2 | 7 | 05:37:40 | 24:56:29 |
| 2026-11-01 | S3 | 154 | 05:36:42 | 24:36:30 |

## Warning triage / Avertissements à examiner

| Severity | Canonical notice | Instances |
|---|---|---:|
| WARNING | equal_shape_distance_diff_coordinates_distance_below_threshold | 18 |
| WARNING | equal_shape_distance_same_coordinates | 1529 |
| WARNING | stop_without_stop_time | 18 |
| INFO | unknown_file | 1 |

Repeated equal-distance shape points are warnings, not automatically proved operational defects. The detailed
canonical report contains source row numbers and sample coordinates. The unreferenced-stop CSV includes all unreferenced
stop records, including parent/location records that may not themselves need stop times; it must not be confused with
the canonical warning count. The additional unknown file is the bundled license, retained deliberately.

Les points de tracé répétés et les arrêts sans passage nécessitent une interprétation adaptée au système consommateur.
Le fichier supplémentaire est la licence d'origine; elle est conservée. Les exemples avec numéros de ligne restent dans
`canonical/report.json`.

## Process and cost boundary / Processus et coûts

Canonical engine: MobilityData GTFS validator 8.0.1, unchanged public tool. The measured full JVM command took
2.381854 seconds elapsed and
6.195344 CPU seconds, including JVM startup; peak RSS
273460 KiB. These are one local execution, not a human-time comparison or a cost invoice.
Acquisition, packaging and independent reconciliation receipts are stored separately. Research, authoring, inference,
human review, support and maintenance monetary costs are unknown. Actual customer collections are zero.

This is an exploratory useful technical delivery. A strong conventional tool already performs general validation;
this packet is an integration/interpretation composition. No rare capability, transfer advantage, graph advantage or
self-financing investment is established by this prototype.

## Reproduction / Reproduction

Verify all hashes in `inputs/source-manifest.json`. Run the recorded canonical command with the pinned jar and feed,
then `python src/build_packet.py` and `python src/independent_check.py` from the prototype directory. Every subprocess
is bounded to 58 seconds through `src/run_command.py`. JSON timestamps and local paths in new canonical reports may
differ; compare semantic findings and source identities, not byte equality of timestamped reports.
