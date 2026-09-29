# SPDX-License-Identifier: Apache-2.0
"""Portable evidence exports and exact replay verification; no untrusted code execution."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from .paper import Config, csv_text, run

WEB = Path(__file__).with_name("web")


def strict_json(text: str) -> Any:
    """Reject ambiguous duplicate keys and non-standard NaN/Infinity constants."""

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON number: {value}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def render(bootstrap: dict[str, Any]) -> str:
    """One offline HTML file, with embedded assets and script-safe data."""
    data = json.dumps(bootstrap, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
    script = "const BOOTSTRAP = " + data + ";\n" + (WEB / "app.js").read_text(encoding="utf-8")
    style = (WEB / "style.css").read_text(encoding="utf-8")

    def digest(value: str) -> str:
        return base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()

    policy = (
        "default-src 'none'; "
        f"script-src 'sha256-{digest(script)}'; style-src 'sha256-{digest(style)}'; "
        "connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'"
    )
    return (
        (WEB / "index.html")
        .read_text(encoding="utf-8")
        .replace("__CSP__", policy)
        .replace("__STYLE__", style)
        .replace("__SCRIPT__", script)
    )


def verify(report: Any) -> dict[str, Any]:
    """Recompute all measurements from embedded prices and reject any altered field."""
    try:
        if not isinstance(report, dict) or report.get("schema") != "finance-alpha-paper-v1":
            raise ValueError("Unsupported report schema")
        config = Config(**report["config"])
        data = report["data"]
        if data["kind"] == "synthetic":
            actual = run(config=config, case=data["case"])
        elif data["kind"] == "user_supplied_unverified":
            actual = run(data["csv"], config)
        else:
            raise ValueError("Unsupported data provenance")

        def numeric_json(value: Any) -> Any:
            # JSON has one number type; browser downloads legitimately write 1.0 as 1.
            # Keep booleans distinct and require exact binary numeric values, not a tolerance.
            if isinstance(value, dict):
                return {key: numeric_json(item) for key, item in value.items()}
            if isinstance(value, list):
                return [numeric_json(item) for item in value]
            if type(value) is float and value.is_integer():
                return int(value)
            return value

        if json.dumps(numeric_json(report), sort_keys=True, allow_nan=False) != json.dumps(
            numeric_json(actual), sort_keys=True, allow_nan=False
        ):
            raise ValueError("Report does not match exact replay with this engine revision")
    except (KeyError, TypeError, RecursionError, OverflowError) as exc:
        raise ValueError("Malformed report") from exc
    return {
        "verified": True,
        "input_sha256": data["sha256"],
        "scope": "Exact replay, not data authenticity or future performance",
    }


def export(report: dict[str, Any], destination: Path) -> None:
    """Reserve a new directory exclusively and mark incomplete exports visibly."""
    # Serialize before reserving the output; no writes occur for invalid reports.
    verify(report)
    result = report["result"]
    files = {
        "report.json": json.dumps(report, indent=2, allow_nan=False) + "\n",
        "prices.csv": report["data"]["csv"],
        "equity.csv": csv_text(result["equity"], list(result["equity"][0])),
        "trades.csv": csv_text(
            result["trades"],
            [
                "date",
                "signal_date",
                "symbol",
                "side",
                "quantity",
                "reference_open",
                "fill_price",
                "fee",
                "slippage_cost",
                "cash_after",
                "units_after",
            ],
        ),
        "report.html": render({"mode": "report", "report": report}),
    }
    files["manifest.json"] = (
        json.dumps(
            {
                "schema": "finance-alpha-export-v1",
                "sha256": {name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items()},
            },
            indent=2,
        )
        + "\n"
    )
    destination.mkdir(parents=True, exist_ok=False)
    marker = destination / "INCOMPLETE"
    marker.write_text("Export interrupted unless this marker is removed. Choose a new output directory to retry.\n")
    for name, content in files.items():
        with (destination / name).open("x", encoding="utf-8", newline="") as output:
            output.write(content)
    marker.unlink()
