# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import collections
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
Row = dict[str, str]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(archive: zipfile.ZipFile, name: str) -> list[Row]:
    if name not in archive.namelist():
        return []
    return list(csv.DictReader(io.StringIO(archive.read(name).decode("utf-8-sig"))))


def active_services(calendar: list[Row], exceptions: list[Row], date: dt.date) -> set[str]:
    stamp = date.strftime("%Y%m%d")
    day = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")[date.weekday()]
    active = {r["service_id"] for r in calendar if r["start_date"] <= stamp <= r["end_date"] and r[day] == "1"}
    for item in exceptions:
        if item["date"] == stamp:
            if item["exception_type"] == "1":
                active.add(item["service_id"])
            elif item["exception_type"] == "2":
                active.discard(item["service_id"])
            else:
                raise ValueError("Unsupported calendar exception type")
    return active


def seconds(value: str) -> int:
    h, m, s = [int(v) for v in value.split(":")]
    if not (h >= 0 and 0 <= m < 60 and 0 <= s < 60):
        raise ValueError("Invalid GTFS time")
    return h * 3600 + m * 60 + s


def clock(value: int) -> str:
    return f"{value // 3600:02d}:{value % 3600 // 60:02d}:{value % 60:02d}"


def main() -> None:
    feed = ROOT / "inputs/rem-20261026.zip"
    protocol = json.loads((ROOT / "protocol.json").read_text())
    if digest(feed) != protocol["input_sha256"]:
        raise ValueError("Feed identity differs from declared protocol")
    with zipfile.ZipFile(feed) as archive:
        if sum(i.file_size for i in archive.infolist()) > 10_000_000:
            raise ValueError("Feed exceeds prototype size scope")
        tables = {
            n: rows(archive, n)
            for n in (
                "agency.txt",
                "routes.txt",
                "stops.txt",
                "trips.txt",
                "stop_times.txt",
                "calendar.txt",
                "calendar_dates.txt",
                "feed_info.txt",
                "frequencies.txt",
            )
        }
        source_files = [
            {"path": i.filename, "bytes": i.file_size, "sha256": hashlib.sha256(archive.read(i.filename)).hexdigest()}
            for i in archive.infolist()
        ]
    trips = tables["trips.txt"]
    stops = tables["stops.txt"]
    routes = sorted(tables["routes.txt"], key=lambda r: r["route_id"])
    departures: dict[str, tuple[int, str]] = {}
    referenced_stops: set[str] = set()
    extended_times = 0
    for stop_time in tables["stop_times.txt"]:
        referenced_stops.add(stop_time["stop_id"])
        sequence = int(stop_time["stop_sequence"])
        trip_id = stop_time["trip_id"]
        depart = stop_time["departure_time"]
        if seconds(depart) >= 86400:
            extended_times += 1
        if trip_id not in departures or sequence < departures[trip_id][0]:
            departures[trip_id] = (sequence, depart)
    report = json.loads((ROOT / "output/canonical/report.json").read_text())
    system = json.loads((ROOT / "output/canonical/system_errors.json").read_text())
    receipt = json.loads((ROOT / "commands/canonical-rem-audit.json").read_text())
    unsupported_frequency = bool(tables["frequencies.txt"])
    start = dt.date(2026, 10, 26)
    date_rows: list[dict[str, object]] = []
    day_totals: list[dict[str, object]] = []
    for offset in range(7):
        date = start + dt.timedelta(days=offset)
        active = active_services(tables["calendar.txt"], tables["calendar_dates.txt"], date)
        selected = [t for t in trips if t["service_id"] in active]
        day_totals.append(
            {"date": date.isoformat(), "scheduled_trips": len(selected), "active_service_ids": sorted(active)}
        )
        for route in routes:
            route_trips = [t for t in selected if t["route_id"] == route["route_id"]]
            times = [seconds(departures[t["trip_id"]][1]) for t in route_trips if t["trip_id"] in departures]
            date_rows.append(
                {
                    "service_date": date.isoformat(),
                    "route_id": route["route_id"],
                    "route_name": route["route_long_name"],
                    "scheduled_trips": len(route_trips),
                    "first_origin_departure": clock(min(times)) if times else "",
                    "last_origin_departure": clock(max(times)) if times else "",
                    "active_service_ids": "|".join(sorted(active)),
                }
            )
    severity: collections.Counter[str] = collections.Counter()
    notices = []
    for item in report["notices"]:
        severity[item["severity"]] += item["totalNotices"]
        notices.append(
            {
                "code": item["code"],
                "severity": item["severity"],
                "count": item["totalNotices"],
                "evidence": "canonical/report.json",
                "sample_count": len(item.get("sampleNotices", [])),
            }
        )
    reasons = []
    if receipt["exit_status"] != 0 or receipt["timeout"]:
        reasons.append("Canonical validator did not complete successfully")
    if severity["ERROR"] or system["notices"]:
        reasons.append("Canonical errors require resolution")
    if any(d["scheduled_trips"] == 0 for d in day_totals):
        reasons.append("At least one requested date has no scheduled trip")
    if unsupported_frequency:
        reasons.append("Frequency-based service needs an additional adapter")
    disposition = "HOLD" if reasons else "SCOPED-STRUCTURAL-PASS"
    no_stop_times = [s for s in stops if s["stop_id"] not in referenced_stops]
    result = {
        "offering": "REM feed release-qualification packet",
        "disposition": disposition,
        "reasons": reasons,
        "protocol_sha256": digest(ROOT / "protocol.json"),
        "input_sha256": digest(feed),
        "feed_version": tables["feed_info.txt"][0]["feed_version"],
        "attribution": "Schedule data: Reseau express metropolitain, https://rem.info/fr, CC BY 4.0. "
        "Original archive unchanged; derived summaries by AGI ALPHA research. No publisher endorsement.",
        "window": {
            "start": start.isoformat(),
            "end": (start + dt.timedelta(days=6)).isoformat(),
            "timezone": tables["agency.txt"][0]["agency_timezone"],
            "semantics": "GTFS local service dates and elapsed service-day times; times >=24:00 preserved. "
            "No UTC conversion or real-time accuracy inference. Coverage requires some service each date, "
            "not every route on every date.",
        },
        "counts": {n: len(v) for n, v in tables.items()},
        "daily_service": day_totals,
        "route_daily_service": date_rows,
        "severity_totals": dict(severity),
        "notices": notices,
        "unreferenced_stop_records": no_stop_times,
        "stop_time_records_at_or_after_24h": extended_times,
        "input_member_manifest": source_files,
        "canonical_receipt": receipt,
        "residual_work": [
            "Check current publisher rider information and any planned changes before operational adoption.",
            "Decide whether warnings affect the consumer; no automatic deletion/correction of stops or shapes.",
            "Test the intended journey-planner import and user journeys in its actual environment.",
            "No historical-feed comparison, agency review, customer acceptance or human-only timing was performed.",
        ],
        "commercial_claim": "No sale, collection, willingness-to-pay evidence, new validator capability or full-cost advantage established.",
    }
    output = ROOT / "output"
    (output / "release-packet.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    with (output / "route-date-service.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(date_rows[0]))
        writer.writeheader()
        writer.writerows(date_rows)
    with (output / "unreferenced-stop-records.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(stops[0]))
        writer.writeheader()
        writer.writerows(no_stop_times)
    table = "\n".join(
        f"| {r['service_date']} | {r['route_id']} | {r['scheduled_trips']} | "
        f"{r['first_origin_departure']} | {r['last_origin_departure']} |"
        for r in date_rows
    )
    notice_table = "\n".join(f"| {n['severity']} | {n['code']} | {n['count']} |" for n in notices)
    text = f"""# REM schedule-ingestion decision / Décision d'importation du réseau REM

**{disposition} — scoped structural checks only / contrôles structurels limités.**

This packet answers whether the exact published REM archive supports a reproducible local schedule-ingestion decision
for 26 October–1 November 2026. It preserves the original archive, canonical validator receipts, all warnings and
explicit calendar expansion. It does not certify actual service, operational suitability or publisher acceptance.

Ce dossier évalue le fichier REM exact pour une décision reproductible d'importation des horaires du 26 octobre au
1er novembre 2026. Il conserve l'archive originale, les résultats du validateur officiel, les avertissements et les
calendriers développés. Il ne certifie ni le service réel ni l'acceptation par l'exploitant.

## Decision and useful action / Décision et action possible

The canonical validator reports {severity['ERROR']} errors, {severity['WARNING']} warning instances and
{severity['INFO']} informational instance. There are no runtime/system notices. Every requested local service date has
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
- Feed version / Version: `{result['feed_version']}`.
- SHA256: `{result['input_sha256']}`.
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
{table}

## Warning triage / Avertissements à examiner

| Severity | Canonical notice | Instances |
|---|---|---:|
{notice_table}

Repeated equal-distance shape points are warnings, not automatically proved operational defects. The detailed
canonical report contains source row numbers and sample coordinates. The unreferenced-stop CSV includes all unreferenced
stop records, including parent/location records that may not themselves need stop times; it must not be confused with
the canonical warning count. The additional unknown file is the bundled license, retained deliberately.

Les points de tracé répétés et les arrêts sans passage nécessitent une interprétation adaptée au système consommateur.
Le fichier supplémentaire est la licence d'origine; elle est conservée. Les exemples avec numéros de ligne restent dans
`canonical/report.json`.

## Process and cost boundary / Processus et coûts

Canonical engine: MobilityData GTFS validator 8.0.1, unchanged public tool. The measured full JVM command took
{receipt['elapsed_seconds']:.6f} seconds elapsed and
{receipt['user_cpu_seconds'] + receipt['system_cpu_seconds']:.6f} CPU seconds, including JVM startup; peak RSS
{receipt['max_rss_kib']} KiB. These are one local execution, not a human-time comparison or a cost invoice.
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
"""
    (output / "README-EN-FR.md").write_text(text)
    print(
        json.dumps(
            {"disposition": disposition, "daily_service": day_totals, "warnings": dict(severity)}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
