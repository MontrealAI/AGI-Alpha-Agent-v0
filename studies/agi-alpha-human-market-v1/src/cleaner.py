# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import re
import unicodedata
from pathlib import Path
from typing import Any

FIELDS = ["record_id", "category", "date", "amount", "updated_at"]
MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 50000


def norm(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip())


def date_value(value: str, style: str) -> str:
    pattern = r"[0-9]{4}-[0-9]{2}-[0-9]{2}" if style == "iso" else r"[0-9]{2}/[0-9]{2}/[0-9]{4}"
    if not re.fullmatch(pattern, value):
        raise ValueError("date format")
    a, b, c = (int(x) for x in re.split("[-/]", value))
    day = dt.date(a, b, c) if style == "iso" else dt.date(c, b, a)
    if not 1900 <= day.year <= 2100:
        raise ValueError("date year")
    return day.isoformat()


def amount_value(value: str, locale: str) -> str:
    if locale == "dot":
        if not re.fullmatch(r"-?[0-9]{1,10}(?:\.[0-9]{1,2})?", value):
            raise ValueError("amount format")
        decimal = value
    else:
        if not re.fullmatch(r"-?(?:[0-9]{1,10}|[0-9]{1,3}(?:\.[0-9]{3}){1,3})(?:,[0-9]{1,2})?", value):
            raise ValueError("amount format")
        decimal = value.replace(".", "").replace(",", ".")
        if len(decimal.lstrip("-").split(".")[0]) > 10:
            raise ValueError("amount digits")
    sign = -1 if decimal.startswith("-") else 1
    whole, _, fraction = decimal.lstrip("-").partition(".")
    cents = sign * (int(whole) * 100 + int(fraction.ljust(2, "0") or "0"))
    if abs(cents) > 999999999999:
        raise ValueError("amount range")
    return ("-" if cents < 0 else "") + str(abs(cents) // 100) + "." + str(abs(cents) % 100).zfill(2)


def validate_job(job: dict[str, Any], version: int) -> dict[str, Any]:
    if set(job) != {"schema", "id", "data_class", "source", "rules"}:
        raise ValueError("JOB_FIELDS")
    if job["schema"] != "csv-clean-job/v1" or job["data_class"] not in {"synthetic", "public"}:
        raise ValueError("INPUT_POLICY")
    if not isinstance(job["id"], str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", job["id"]):
        raise ValueError("JOB_ID")
    source = job["source"]
    if set(source) != {"file", "sha256"} or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,120}", source["file"]):
        raise ValueError("SOURCE_PATH")
    if source["file"] in {".", ".."} or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
        raise ValueError("SOURCE_HASH")
    rules = job["rules"]
    if set(rules) != {"delimiter", "amount_locale", "date_format", "key_policy", "missing_markers", "category_map"}:
        raise ValueError("RULE_FIELDS")
    if rules["delimiter"] not in {",", ";"} or rules["amount_locale"] not in {"dot", "comma"}:
        raise ValueError("RULE_VALUE")
    if rules["date_format"] not in {"iso", "dmy"} or rules["key_policy"] not in {"hold", "latest"}:
        raise ValueError("RULE_VALUE")
    if not isinstance(rules["missing_markers"], list) or len(rules["missing_markers"]) > 20:
        raise ValueError("MISSING_MARKERS")
    if any(not isinstance(v, str) or len(v) > 256 for v in rules["missing_markers"]):
        raise ValueError("MISSING_MARKERS")
    if "" not in {norm(v) for v in rules["missing_markers"]}:
        raise ValueError("EMPTY_MISSING_MARKER_REQUIRED")
    mapping = rules["category_map"]
    if not isinstance(mapping, dict) or len(mapping) > 200:
        raise ValueError("CATEGORY_MAP")
    if any(not isinstance(k, str) or not isinstance(v, str) or max(len(k), len(v)) > 256 for k, v in mapping.items()):
        raise ValueError("CATEGORY_MAP")
    if len({norm(k) for k in mapping}) != len(mapping):
        raise ValueError("AMBIGUOUS_CATEGORY_MAP")
    if version not in {0, 1, 2}:
        raise ValueError("VERSION")
    if version < 1 and (rules["amount_locale"] != "dot" or rules["date_format"] != "iso"):
        raise ValueError("UNSUPPORTED_LOCALE_JOB")
    if version < 2 and rules["key_policy"] != "hold":
        raise ValueError("UNSUPPORTED_KEY_POLICY")
    return rules


def clean(job: dict[str, Any], raw: bytes, version: int) -> dict[str, Any]:
    rules = validate_job(job, version)
    if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != job["source"]["sha256"]:
        raise ValueError("SOURCE_SIZE_OR_IDENTITY")
    text = raw.decode("utf-8-sig", errors="strict")
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=rules["delimiter"], strict=True)
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ValueError("EMPTY_INPUT") from exc
    if header != FIELDS:
        raise ValueError("HEADINGS")
    missing = {norm(x) for x in rules["missing_markers"]}
    mapping = {norm(k): norm(v) for k, v in rules["category_map"].items()}
    valid: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    count = 0
    for count, values in enumerate(reader, 1):
        if count > MAX_ROWS:
            raise ValueError("ROW_LIMIT")
        if len(values) != len(FIELDS) or any(len(x) > 256 for x in values):
            raise ValueError("ROW_SHAPE_OR_CELL_LIMIT")
        row = dict(zip(FIELDS, (norm(x) for x in values), strict=True))
        row["category"] = mapping.get(row["category"], row["category"])
        reasons = []
        for field in FIELDS[:4]:
            if row[field] in missing:
                reasons.append("MISSING_" + field.upper())
        for field, converter in [("date", lambda v: date_value(v, rules["date_format"])),
                                 ("amount", lambda v: amount_value(v, rules["amount_locale"]))]:
            if row[field] not in missing:
                try:
                    row[field] = converter(row[field])
                except ValueError:
                    reasons.append("INVALID_" + field.upper())
        if row["updated_at"] in missing:
            row["updated_at"] = ""
            if rules["key_policy"] == "latest":
                reasons.append("MISSING_UPDATED_AT")
        else:
            try:
                row["updated_at"] = date_value(row["updated_at"], "iso")
            except ValueError:
                reasons.append("INVALID_UPDATED_AT")
        if reasons:
            quarantine.append({"source_row": count, "reasons": sorted(set(reasons))})
        else:
            valid.append({**row, "source_row": count})
    if count == 0:
        raise ValueError("EMPTY_INPUT")
    seen: dict[tuple[str, ...], int] = {}
    groups: dict[str, list[dict[str, Any]]] = {}
    duplicates: list[dict[str, int]] = []
    for row in valid:
        key = tuple(row[f] for f in FIELDS)
        if key in seen:
            duplicates.append({"source_row": row["source_row"], "kept_source_row": seen[key]})
        else:
            seen[key] = row["source_row"]
            groups.setdefault(row["record_id"], []).append(row)
    kept: list[dict[str, Any]] = []
    superseded: list[dict[str, int]] = []
    for rows in groups.values():
        if len(rows) == 1:
            kept.extend(rows)
        elif rules["key_policy"] == "hold":
            quarantine.extend({"source_row": row["source_row"], "reasons": ["CONFLICTING_KEY"]} for row in rows)
        else:
            newest = max(row["updated_at"] for row in rows)
            latest = [row for row in rows if row["updated_at"] == newest]
            if len(latest) != 1:
                quarantine.extend({"source_row": row["source_row"], "reasons": ["CONFLICTING_LATEST"]} for row in rows)
            else:
                winner = latest[0]
                kept.append(winner)
                superseded.extend({"source_row": row["source_row"], "kept_source_row": winner["source_row"]}
                                  for row in rows if row is not winner)
    result: dict[str, Any] = {"clean": sorted(kept, key=lambda x: x["record_id"]),
                              "quarantine": sorted(quarantine, key=lambda x: x["source_row"]),
                              "duplicates": duplicates, "superseded": sorted(superseded, key=lambda x: x["source_row"])}
    statuses = []
    for field, status in [("clean", "CLEAN"), ("quarantine", "QUARANTINE"),
                          ("duplicates", "DUPLICATE_EXACT"), ("superseded", "SUPERSEDED")]:
        statuses.extend({"source_row": row["source_row"], "status": status} for row in result[field])
    result["disposition"] = sorted(statuses, key=lambda x: x["source_row"])
    if [x["source_row"] for x in result["disposition"]] != list(range(1, count + 1)):
        raise ValueError("RECORD_RECONCILIATION")
    return result


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "|".join(row[k]) if isinstance(row[k], list) else row[k] for k in fields})
