# SPDX-License-Identifier: Apache-2.0
"""Separate finite semantic checker for an update-only supplier feed."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from decimal import Decimal, InvalidOperation
from typing import Any

from .catalog_product import _parse as validate_native_syntax
from .catalog_identity import assert_upstream_identity


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read(text: str) -> tuple[list[str], list[dict[str, str]]]:
    # Shared bounded syntax gate only; discard its rows. Expected semantics,
    # review output and complete native contract are reconstructed separately.
    validate_native_syntax(text)
    reader = csv.reader(io.StringIO(text.removeprefix("\ufeff"), newline=""), strict=True)
    fields = next(reader)
    if len(fields) > 32 or not fields or len(set(fields)) != len(fields) or any(not field.strip() for field in fields):
        raise ValueError("Invalid header")
    if any(len(field) > 4_096 for field in fields):
        raise ValueError("Header exceeds cell bound")
    rows: list[dict[str, str]] = []
    for values in reader:
        if len(rows) >= 1_500 or any(len(value) > 4_096 for value in values):
            raise ValueError("Input exceeds row or cell bound")
        if len(values) != len(fields):
            raise ValueError("Invalid row width")
        rows.append(dict(zip(fields, values, strict=True)))
    return fields, rows


def conventional_delta(before: str, delta: str, request: dict[str, Any], *, normalize_decimals: bool = True) -> str:
    """Compute the same requested result without using producer transformation or reconciliation logic."""
    keys, writes, decimals = request["keys"], request["write_fields"], request["decimal_fields"]
    aliases = request["aliases"]
    if set(request) != {"keys", "write_fields", "decimal_fields", "aliases", "mode", "membership", "row_order"}:
        raise ValueError("Unknown or missing request field")
    if (
        request["mode"] != "update_existing_only"
        or request["membership"] != "preserve"
        or request["row_order"] != "preserve"
    ):
        raise ValueError("Unsupported update semantics")
    for values in (keys, writes, decimals):
        if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
            raise ValueError("Invalid field list")
        if len(values) != len(set(values)):
            raise ValueError("Repeated field")
    if not isinstance(aliases, dict) or not all(
        isinstance(k, str) and isinstance(v, str) and k and v for k, v in aliases.items()
    ):
        raise ValueError("Invalid aliases")
    columns, original = _read(before)
    incoming_columns, incoming = _read(delta)
    mapped = [aliases.get(field, field) for field in incoming_columns]
    if len(mapped) != len(set(mapped)) or not set(keys).issubset(mapped):
        raise ValueError("Ambiguous or missing key columns")
    if not set(mapped).issubset(set(keys) | set(writes)) or not set(mapped).issubset(columns):
        raise ValueError("Undeclared feed field")
    if not set(aliases).issubset(incoming_columns):
        raise ValueError("Unused alias")
    if not keys or len(keys) != len(set(keys)) or not set(keys).issubset(columns):
        raise ValueError("Invalid keys")
    if not writes or len(writes) != len(set(writes)) or set(keys) & set(writes):
        raise ValueError("Invalid writable fields")
    if not set(writes).issubset(columns) or not set(decimals).issubset(writes):
        raise ValueError("Unknown or protected decimal field")
    if not set(mapped) - set(keys):
        raise ValueError("No update columns")
    for row in original:
        for field in decimals:
            if not Decimal(row[field]).is_finite():
                raise ValueError("Nonfinite source decimal")
    indexed: dict[tuple[str, ...], dict[str, str]] = {}
    for row in original:
        key = tuple(row[field] for field in keys)
        if any(not value for value in key) or key in indexed:
            raise ValueError("Missing or duplicate source key")
        indexed[key] = row.copy()
    seen = set()
    for row in incoming:
        values = {aliases.get(field, field): value for field, value in row.items()}
        key = tuple(values[field] for field in keys)
        if key not in indexed or key in seen or any(not value for value in key):
            raise ValueError("Unknown or duplicate update key")
        seen.add(key)
        for field in mapped:
            if field in keys:
                continue
            new = values[field]
            if field in decimals:
                a, b = Decimal(indexed[key][field]), Decimal(new)
                if not a.is_finite() or not b.is_finite():
                    raise ValueError("Nonfinite decimal")
                if normalize_decimals and a == b:
                    continue
            indexed[key][field] = new
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(indexed.values())
    return stream.getvalue()


def verify_delta(before: str, delta: str, envelope: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Return a scoped verdict; a hash match alone cannot establish the intended update."""
    failures = []
    try:
        assert_upstream_identity()
        if not isinstance(envelope, dict) or not isinstance(request, dict):
            raise ValueError("Envelope and request must be objects")
        native = envelope["native_package"]
        if not isinstance(native, dict):
            raise ValueError("Native package must be an object")
        changes_value = native.get("changes")
        if not isinstance(changes_value, list) or not all(isinstance(item, dict) for item in changes_value):
            raise ValueError("Native changes must be a list of objects")
        expected = conventional_delta(before, delta, request)
        columns, old_rows = _read(before)
        _, new_rows = _read(expected)
        keys = request["keys"]
        old_index = {tuple(row[key] for key in keys): row for row in old_rows}
        new_index = {tuple(row[key] for key in keys): row for row in new_rows}
        changes = []
        for key in sorted(old_index):
            old, new = old_index[key], new_index[key]
            if old != new:
                changes.append(
                    {
                        "key": list(key),
                        "kind": "update",
                        "before": [old[field] for field in columns],
                        "after": [new[field] for field in columns],
                        "fields": [field for field in columns if old[field] != new[field]],
                    }
                )
        preview = io.StringIO(newline="")
        writer = csv.writer(preview, lineterminator="\n")
        for row in [columns, *[[row[field] for field in columns] for row in new_rows]]:
            writer.writerow(
                ["'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value for value in row]
            )
        after_image = conventional_delta(before, delta, request, normalize_decimals=False)
        expected_native = {
            "schema": "catalog-change-set/v1",
            "generation": 3,
            "keys": keys,
            "options": {
                "decimal_columns": request["decimal_fields"],
                "aliases": {},
                "update_fields": request["write_fields"],
            },
            "before_sha256": _hash(before),
            "after_sha256": _hash(after_image),
            "after_csv": after_image,
            "output_sha256": _hash(expected),
            "output_csv": expected,
            "rollback_csv": before,
            "safe_preview_csv": preview.getvalue(),
            "changes": changes,
            "trace": {
                "before_rows": len(old_rows),
                "after_rows": len(new_rows),
                "changed_keys": len(changes),
                "authority": "none; in-memory transformation only",
                "formula_policy": "Exact machine CSV preserves text; safe_preview_csv prefixes formula-like cells.",
                "parser_provenance": "Port of bounds and quote grammar in examples/successor-alpha/engine.mjs.",
            },
        }
        native_unsigned = {key: value for key, value in native.items() if key != "proof_digest"}
        native_digest = _hash(
            json.dumps(native_unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        )
        unsigned = {key: value for key, value in envelope.items() if key != "digest"}
        expected_digest = _hash(
            json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        )
        obligations = {
            "envelope_identity": envelope.get("digest") == expected_digest,
            "schema": envelope.get("schema") == "catalog-delta-delivery/v1",
            "request_binding": envelope.get("request") == request,
            "source_binding": envelope.get("before_sha256") == _hash(before),
            "delta_binding": envelope.get("delta_sha256") == _hash(delta),
            "native_source_binding": native.get("before_sha256") == _hash(before),
            "intended_result": native.get("output_csv") == expected,
            "output_binding": native.get("output_sha256") == _hash(expected),
            "native_contract": native_unsigned == expected_native and type(native.get("generation")) is int,
            "native_integrity": native.get("proof_digest") == native_digest,
            "source_identity": envelope.get("source_git_blob") == "9f22a4448fa7bbd949b54c4c0d9b61936f49d549",
            "review_preview": native.get("safe_preview_csv") == preview.getvalue(),
            "change_summary": native.get("changes") == changes,
            "exact_rollback": native.get("rollback_csv") == before,
            "no_inserts_or_deletes": all(change.get("kind") == "update" for change in native["changes"]),
        }
        failures = [name for name, passed in obligations.items() if not passed]
    except (KeyError, TypeError, ValueError, InvalidOperation, csv.Error, StopIteration) as error:
        failures.append(f"invalid_input_or_artifact: {type(error).__name__}: {error}")
    return {
        "verdict": "PASS_IN_SCOPE" if not failures else "REJECTED",
        "failures": failures,
        "scope": "Bounded update-only CSV semantics and exact rollback; not business or security certification",
        "independence": "Shared bounded syntax parser; separate semantic derivation; same author/session/runtime; not external certification",
    }
