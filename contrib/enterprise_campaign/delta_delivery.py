# SPDX-License-Identifier: Apache-2.0
"""Adapt an explicit sparse feed to the existing reversible catalogue engine."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from . import catalog_product as native
from .delta_acceptance import verify_delta
from .catalog_identity import UPSTREAM_GIT_BLOB, assert_upstream_identity


def _digest(value: object) -> str:
    return native.digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False))


def make_request(
    keys: list[str],
    write_fields: list[str],
    decimal_fields: list[str] | None = None,
    aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Require explicit keys and field authority; never infer identifiers from data."""
    lists = {
        "keys": keys,
        "write_fields": write_fields,
        "decimal_fields": [] if decimal_fields is None else decimal_fields,
    }
    for name, values in lists.items():
        if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
            raise ValueError(f"{name} must be a list of nonempty strings")
        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate {name}")
    if not keys or not write_fields or set(keys) & set(write_fields):
        raise ValueError("Declare keys and distinct nonempty writable fields")
    if not set(lists["decimal_fields"]).issubset(write_fields):
        raise ValueError("Decimal fields must be writable fields")
    aliases = {} if aliases is None else aliases
    if not isinstance(aliases, dict) or not all(
        isinstance(k, str) and isinstance(v, str) and k and v for k, v in aliases.items()
    ):
        raise ValueError("Aliases must be explicit nonempty string pairs")
    return {
        **{key: value[:] for key, value in lists.items()},
        "aliases": aliases.copy(),
        "mode": "update_existing_only",
        "membership": "preserve",
        "row_order": "preserve",
    }


def build_delta(before: str, delta: str, request: dict[str, Any]) -> dict[str, Any]:
    """Construct a source-bound full snapshot from the sparse authorized update."""
    assert_upstream_identity()
    clean = make_request(request["keys"], request["write_fields"], request["decimal_fields"], request["aliases"])
    if clean != request:
        raise ValueError("Unknown request field or unsupported update semantics")
    headers, rows = native._parse(before)
    feed_headers, feed_rows = native._parse(delta)
    aliases = clean["aliases"]
    if not set(aliases).issubset(feed_headers):
        raise ValueError("Every alias must identify a supplied column")
    canonical_headers = [aliases.get(field, field) for field in feed_headers]
    if len(canonical_headers) != len(set(canonical_headers)):
        raise ValueError("Alias collision")
    keys, writes = clean["keys"], clean["write_fields"]
    if not set(keys + writes).issubset(headers):
        raise ValueError("Keys and writable fields must exist in the source")
    if not set(keys).issubset(canonical_headers):
        raise ValueError("Feed is missing a declared key")
    if not set(canonical_headers).issubset(set(keys + writes)):
        raise ValueError("Feed contains a protected or undeclared column")
    if not set(canonical_headers) - set(keys):
        raise ValueError("Feed must contain an authorized update column")
    source_index = native._index(headers, rows, keys)
    feed_index = native._index(canonical_headers, feed_rows, keys)
    if not set(feed_index).issubset(source_index):
        raise ValueError("New keys refuse: this contract permits updates, not insertions")
    positions = {field: headers.index(field) for field in canonical_headers}
    for key, row in feed_index.items():
        for field, value in zip(canonical_headers, row, strict=True):
            if field not in keys:
                source_index[key][positions[field]] = value
    full_after = native._emit(headers, rows)
    package = native.reconcile(
        before, full_after, keys, 3, decimal_columns=clean["decimal_fields"], update_fields=writes
    )
    envelope = {
        "schema": "catalog-delta-delivery/v1",
        "request": clean,
        "before_sha256": native.digest(before),
        "delta_sha256": native.digest(delta),
        "native_package": package,
        "mechanism": "Sparse transactional update semantics adapted to a full-snapshot compiler",
        "source_git_blob": UPSTREAM_GIT_BLOB,
    }
    envelope["digest"] = _digest(envelope)
    return envelope


def main() -> int:
    """Write a new review directory; never modify an input or a remote catalogue."""
    parser = argparse.ArgumentParser(description="Prepare and check an update-only supplier delivery; no paid services")
    parser.add_argument("--before", required=True)
    parser.add_argument("--delta", required=True)
    parser.add_argument("--keys", nargs="+", required=True)
    parser.add_argument("--write-fields", nargs="+", required=True)
    parser.add_argument("--decimal-fields", nargs="*", default=[])
    parser.add_argument("--aliases", default="{}")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    started = time.perf_counter_ns()
    output = Path(args.output)
    try:
        if output.exists():
            raise ValueError("Output must be a new directory; previous evidence is never overwritten")
        before, delta = native._read(args.before), native._read(args.delta)
        request = make_request(args.keys, args.write_fields, args.decimal_fields, json.loads(args.aliases))
        envelope = build_delta(before, delta, request)
        acceptance = verify_delta(before, delta, envelope, request)
        if acceptance["verdict"] != "PASS_IN_SCOPE":
            raise ValueError(f"Independent semantic check rejected: {acceptance['failures']}")
        package = envelope["native_package"]
        applied = native.apply_patch(before, package, authorized=True)
        reverted = native.rollback(applied, package, authorized=True)
        if reverted != before:
            raise ValueError("Exact rollback failed")
        output.mkdir(parents=True, exist_ok=False)
        artifacts = {
            "updated.csv": applied,
            "rollback.csv": reverted,
            "safe-preview.csv": package["safe_preview_csv"],
            "source.csv": before,
            "delta.csv": delta,
        }
        for name, text in artifacts.items():
            (output / name).write_text(text, encoding="utf-8", newline="")
        usage = {
            "elapsed_ns": time.perf_counter_ns() - started,
            "model_calls": 0,
            "network_actions": 0,
            "changed_rows": len(package["changes"]),
            "catalogue_rows": package["trace"]["before_rows"],
            "real_customer_revenue": 0,
            "complete_monetary_cost": None,
            "commercial_success": "UNESTABLISHED",
        }
        for name, value in {
            "package.json": envelope,
            "native-package.json": package,
            "request.json": request,
            "acceptance.json": acceptance,
            "usage.json": usage,
        }.items():
            (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        report = (
            "# Supplier delta delivery\n\n**PASS_IN_SCOPE — local review package only.**\n\n"
            f"Updated {usage['changed_rows']} of {usage['catalogue_rows']} existing rows. "
            "Untouched rows and protected fields remain; exact original rollback checked.\n\n"
            "`safe-preview.csv` is for spreadsheet review; `updated.csv` preserves machine text, "
            "including formula-like content, and should not be opened as a trusted spreadsheet.\n\n"
            "No source overwritten, remote update, payment, model API call or customer acceptance. "
            "Actual complete cost and profitability remain unknown.\n"
        )
        (output / "REPORT.md").write_text(report)
        print(json.dumps({"verdict": acceptance["verdict"], "output": str(output), **usage}, indent=2))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"REFUSED: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
