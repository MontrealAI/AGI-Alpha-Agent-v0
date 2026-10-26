# GTFS production prototype: discovery record

Started after portfolio selection on 2026-10-26. Local command budget: each production/acquisition subprocess <=58 seconds; 30-minute total authoring/analysis target. No paid activity or outreach. This is an exploratory complete delivery, not the API primary confirmation.

## Selection and failed candidates

- Family selected before production outcomes: GTFS release qualification with a consumer-actionable feed/calendar decision and strongest available canonical validator. Need is recurring feed updates and meaningful quality interpretation, not invented fares or demand.
- TransLink excluded as execution input: official page explicitly permits additional conditions/fees for commercial use; retained only as recurrence evidence.
- STLévis rejected during license review: official page advertises CC BY 4.0 but also says commercial/quasi-commercial use needs prior written permission. No feed downloaded. This inconsistency is preserved; no permission sought or assumed.
- Données Québec pages for STM and STSV returned a JavaScript anti-bot challenge through web retrieval. No challenge bypass attempted. Official data URLs are considered separately only as ordinary public downloads; blocked data would cause a pivot.
- STM publisher developer pages redirected to an inaccessible beta domain in web retrieval. Preserved as source-acquisition failure.
- First validator acquisition command failed before network access: `/usr/bin/time` is absent. Switched to Python `resource.getrusage`/monotonic subprocess measurement; the failed shell command is not hidden or counted as a successful download.

## Candidate input decision

REM is compact and relevant to Montreal. Transitland's public catalogue and maintained atlas identify the publisher endpoint `https://gtfs.gpmmom.ca/gtfs/gtfs.zip` and CC BY 4.0. Download the publisher archive and inspect any included license text before redistribution. If the archive has conflicting terms, do not publish it as permissive.

Sources: https://www.transit.land/data/feeds/f-reseau~express~metropolitain ; https://github.com/transitland/transitland-atlas/blob/master/feeds/gtfs.gpmmom.ca.dmfr.json ; https://www.stlevis.ca/stlevis/donnees-ouvertes .

Pinned canonical incumbent: MobilityData GTFS validator 8.0.1 CLI, published asset SHA256 `19293ddd9b6f954f216d4f12054bd8a3232921751c4484339e339764a91000e2`, source https://github.com/MobilityData/gtfs-validator/releases/tag/v8.0.1 . This is an existing public tool, not an AGI ALPHA invention.

## Completed production

REM publisher archive contains the full CC BY 4.0 license. The first inspection assumed UTF-8 for all files and failed on a CP1252 typographic byte in the license; the exact license bytes were preserved and reviewed as CP1252. All GTFS CSV tables themselves decode as UTF-8.

One exploratory delivery completed, not 21 jobs: the 21 cells are 3 routes by 7 dates. Canonical engine reported zero errors, 1,565 warnings and one informational unknown license file. No warning was removed. Source-derived service totals: 443 per weekday, 323 Saturday, 315 Sunday. The packet is scoped structural pass; actual rider timetable accuracy, target-application acceptance and paid demand are unassessed.

Independent SQLite reconciliation initially covered 44 checks (0.315781s elapsed); a necessary extension also checked every first/last origin departure and finished with 86 checks (16.631317s elapsed). Both genuine receipts are retained and their costs included. This is same-session separate implementation, not external independent assessment. No rerun was used to improve timing.

Tooling checks: ruff, black and mypy are absent in the inherited global environment; none is claimed as passed. Root is arranging repository-qualified lint tooling before freezing the publication source.


## Post-delivery source qualification (2026-10-26)

Original executed sources were archived before strict typing corrections. An initial strict mypy check found three local annotation/name-reuse errors; the final check passed for all three scripts. Ruff passed. Explicit Black 25.1.0 per-file API confirmed no further formatting changes. Two CLI format commands stalled in tool completion; their total elapsed/CPU is unavailable and must not be priced as zero. See evidence/qualification*.json and evidence/formatting.json. This packaging step does not add a customer delivery or a confirmation run.
