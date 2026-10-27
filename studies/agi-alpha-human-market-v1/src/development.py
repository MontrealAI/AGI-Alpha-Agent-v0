# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = [
    [" 0001 ", "R&D", "2026-10-20", "120.00", ""],
    ["0001", "Research", "2026-10-20", "120.0", ""],
    ["0002", "Engineering", "2026-10-21", "-3.5", ""],
    ["0003", "Research", "2026-02-30", "bad", ""],
    ["0004", "Research", "2026-10-22", "NA", ""],
    ["0005", "Testing", "2026-10-23", "5", ""],
    ["0005", "Testing", "2026-10-23", "8", ""],
]
base_rules = {"delimiter": ",", "amount_locale": "dot", "date_format": "iso", "key_policy": "hold",
              "missing_markers": ["", "NA", "N/A", "NULL"], "category_map": {"R&D": "Research"}}
for index, kind in enumerate(["simple", "locale", "versioned"]):
    folder = ROOT / "development" / kind
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / "input.csv").exists():
        raise SystemExit("Development inputs already exist")
    current = [row.copy() for row in rows]
    rules = dict(base_rules)
    if kind == "locale":
        rules.update(delimiter=";", amount_locale="comma", date_format="dmy")
        current = [[a, b, c[8:10] + "/" + c[5:7] + "/" + c[:4], d.replace(".", ","), e]
                   for a, b, c, d, e in current]
        current.append(["0006", "Fiscal; analysis", "25/10/2026", "1.200,25", ""])
    if kind == "versioned":
        rules.update(key_policy="latest")
        current = [row[:4] + ["2026-10-24"] for row in current]
        current[6][-1] = "2026-10-25"
        current.append(["0007", "Multi\nline", "2026-10-23", "12", "2026-10-23"])
    with (folder / "input.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter=rules["delimiter"])
        writer.writerow(["record_id", "category", "date", "amount", "updated_at"])
        writer.writerows(current)
    source_hash = hashlib.sha256((folder / "input.csv").read_bytes()).hexdigest()
    job = {"schema": "csv-clean-job/v1", "id": "dev-" + kind, "data_class": "synthetic",
           "source": {"file": "input.csv", "sha256": source_hash}, "rules": rules}
    (folder / "job.json").write_text(json.dumps(job, indent=2) + "\n")
print("Created exactly three preconfirmation development jobs")
