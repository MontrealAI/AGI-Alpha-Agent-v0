# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    packet = json.loads((ROOT / "output/release-packet.json").read_text())
    manifest = json.loads((ROOT / "inputs/source-manifest.json").read_text())
    assertions: list[str] = []
    for name, identity in manifest["inputs"].items():
        data = (ROOT / name).read_bytes()
        assert len(data) == identity["bytes"]
        assert hashlib.sha256(data).hexdigest() == identity["sha256"]
        assertions.append("identity:" + name)
    con = sqlite3.connect(":memory:")
    with zipfile.ZipFile(ROOT / "inputs/rem-20261026.zip") as archive:
        for name in ("routes", "trips", "stops", "stop_times", "calendar", "calendar_dates"):
            stream = csv.DictReader(io.StringIO(archive.read(name + ".txt").decode("utf-8-sig")))
            fields = stream.fieldnames
            assert fields is not None and all(f.replace("_", "").isalnum() for f in fields)
            con.execute("CREATE TABLE " + name + " (" + ",".join('"' + f + '" TEXT' for f in fields) + ")")
            con.executemany(
                "INSERT INTO " + name + " VALUES (" + ",".join("?" for _ in fields) + ")",
                [tuple(row[f] for f in fields) for row in stream],
            )
    for child, field, parent, parent_field in [
        ("trips", "route_id", "routes", "route_id"),
        ("stop_times", "trip_id", "trips", "trip_id"),
        ("stop_times", "stop_id", "stops", "stop_id"),
    ]:
        query = (
            f"SELECT COUNT(*) FROM {child} c LEFT JOIN {parent} p ON c.{field}=p.{parent_field} "
            f"WHERE p.{parent_field} IS NULL"
        )
        assert con.execute(query).fetchone()[0] == 0
        assertions.append("foreign_key:" + child + "." + field)
    for table, field in [("routes", "route_id"), ("trips", "trip_id"), ("stops", "stop_id")]:
        assert con.execute(f"SELECT COUNT(*)-COUNT(DISTINCT {field}) FROM {table}").fetchone()[0] == 0
        assertions.append("unique:" + table + "." + field)
    sql = """WITH active(service_id) AS (
      SELECT service_id FROM calendar WHERE :stamp BETWEEN start_date AND end_date
       AND CASE CAST(strftime('%w',:date) AS INTEGER)
         WHEN 0 THEN sunday WHEN 1 THEN monday WHEN 2 THEN tuesday WHEN 3 THEN wednesday
         WHEN 4 THEN thursday WHEN 5 THEN friday WHEN 6 THEN saturday END = '1'
      UNION SELECT service_id FROM calendar_dates WHERE date=:stamp AND exception_type='1'
      EXCEPT SELECT service_id FROM calendar_dates WHERE date=:stamp AND exception_type='2'
    )
    SELECT r.route_id, COUNT(t.trip_id) FROM routes r
    LEFT JOIN trips t ON t.route_id=r.route_id AND t.service_id IN (SELECT service_id FROM active)
    GROUP BY r.route_id ORDER BY r.route_id"""
    for row in packet["route_daily_service"]:
        date = row["service_date"]
        result = dict(con.execute(sql, {"date": date, "stamp": date.replace("-", "")}).fetchall())
        assert result[row["route_id"]] == row["scheduled_trips"]
        assertions.append("route_date:" + date + ":" + row["route_id"])
        time_sql = (
            sql[: sql.index("    SELECT r.route_id")]
            + """
        SELECT MIN(CAST(substr(s.departure_time,1,length(s.departure_time)-6) AS INTEGER)*3600
                   +CAST(substr(s.departure_time,-5,2) AS INTEGER)*60
                   +CAST(substr(s.departure_time,-2) AS INTEGER)),
               MAX(CAST(substr(s.departure_time,1,length(s.departure_time)-6) AS INTEGER)*3600
                   +CAST(substr(s.departure_time,-5,2) AS INTEGER)*60
                   +CAST(substr(s.departure_time,-2) AS INTEGER))
          FROM trips t JOIN stop_times s ON t.trip_id=s.trip_id
         WHERE t.route_id=:route AND t.service_id IN (SELECT service_id FROM active)
           AND NOT EXISTS (SELECT 1 FROM stop_times q WHERE q.trip_id=s.trip_id
                           AND CAST(q.stop_sequence AS INTEGER)<CAST(s.stop_sequence AS INTEGER))"""
        )
        minimum, maximum = con.execute(
            time_sql, {"date": date, "stamp": date.replace("-", ""), "route": row["route_id"]}
        ).fetchone()
        for field, value in [("first_origin_departure", minimum), ("last_origin_departure", maximum)]:
            expected = (
                ""
                if value is None
                else con.execute(
                    "SELECT printf('%02d:%02d:%02d',? / 3600,? / 60 % 60,? % 60)", (value, value, value)
                ).fetchone()[0]
            )
            assert row[field] == expected
            assertions.append("origin_time:" + date + ":" + row["route_id"] + ":" + field)
    for item in packet["daily_service"]:
        day_result = con.execute(sql, {"date": item["date"], "stamp": item["date"].replace("-", "")}).fetchall()
        assert sum(count for _, count in day_result) == item["scheduled_trips"]
        assertions.append("daily_total:" + item["date"])
    additional_dates = []
    for (stamp,) in con.execute("SELECT DISTINCT date FROM calendar_dates ORDER BY date"):
        date = dt.datetime.strptime(stamp, "%Y%m%d").date().isoformat()
        exception_result = con.execute(sql, {"date": date, "stamp": stamp}).fetchall()
        additional_dates.append({"date": date, "route_trip_counts": dict(exception_result)})
    core = json.loads((ROOT / "output/canonical/report.json").read_text())
    assert sum(n["totalNotices"] for n in core["notices"] if n["severity"] == "ERROR") == 0
    assert not json.loads((ROOT / "output/canonical/system_errors.json").read_text())["notices"]
    for canonical, table in [("Trips", "trips"), ("Routes", "routes"), ("Stops", "stops")]:
        assert core["summary"]["counts"][canonical] == con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
        assertions.append("canonical_count:" + canonical)
    assert packet["disposition"] == "SCOPED-STRUCTURAL-PASS"
    assertions.append("disposition:canonical_success_and_full_requested_date_coverage")
    for path, expected in [
        ("inputs/rem-20261026.zip", packet["input_sha256"]),
        ("protocol.json", packet["protocol_sha256"]),
    ]:
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        assertions.append("packet_identity:" + path)
    result = {
        "status": "PASS",
        "method": "separately implemented SQLite calendar/exception queries; no packet-builder import",
        "checks": len(assertions),
        "assertions": assertions,
        "additional_exception_date_results": additional_dates,
        "independence": "separate implementation in same session; not external customer or publisher acceptance",
        "packet_sha256": hashlib.sha256((ROOT / "output/release-packet.json").read_bytes()).hexdigest(),
    }
    (ROOT / "output/independent-check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "checks": len(assertions), "exception_dates": len(additional_dates)}))


if __name__ == "__main__":
    main()
