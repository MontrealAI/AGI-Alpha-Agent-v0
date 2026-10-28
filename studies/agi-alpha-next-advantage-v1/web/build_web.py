# SPDX-License-Identifier: Apache-2.0
import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def validate(data: dict[str, Any], strict: bool = False) -> None:
    economics = data.get("economics", {})
    rows = economics.get("summary", [])
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row.get("scenario", "")), str(row.get("policy", "")))
        if key in seen:
            raise ValueError(f"Duplicate scenario/policy record: {key}")
        seen.add(key)
        for name, value in row.items():
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"Nonfinite value in {key}: {name}")
    if strict:
        required = ("meta", "summary", "numerical", "economics", "lineage", "sources", "findings")
        for name in required:
            if not data.get(name):
                raise ValueError(f"Final edition requires {name}")
        if not rows or not data["numerical"].get("rows"):
            raise ValueError("Final edition requires executed numerical and economic records")
        scenarios = {item["id"] for item in economics.get("scenarios", [])}
        policies = {item["id"] for item in economics.get("policies", [])}
        for scenario, policy in seen:
            if scenario not in scenarios or policy not in policies:
                raise ValueError(f"Record lacks scenario or policy metadata: {(scenario, policy)}")


def build(data_path: Path, output_path: Path, strict: bool = False) -> dict[str, Any]:
    if not data_path.exists() and not strict:
        raw = b'{"meta":{},"summary":{},"numerical":{},"economics":{},"lineage":[],"sources":[],"findings":[]}'
    else:
        raw = data_path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Report data must be a JSON object")
    validate(data, strict)
    data.setdefault("meta", {})["report_data_sha256"] = hashlib.sha256(raw).hexdigest()
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    for char, escaped in (
        ("<", "\\u003c"),
        (">", "\\u003e"),
        ("&", "\\u0026"),
        ("\u2028", "\\u2028"),
        ("\u2029", "\\u2029"),
    ):
        encoded = encoded.replace(char, escaped)
    template = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    if template.count("__REPORT_DATA__") != 1:
        raise ValueError("Template must contain exactly one data slot")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template.replace("__REPORT_DATA__", encoded), encoding="utf-8")
    return {
        "output": str(output_path),
        "bytes": output_path.stat().st_size,
        "data_sha256": hashlib.sha256(raw).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the self-contained bilingual study companion")
    parser.add_argument("--data", type=Path, default=Path(__file__).parents[1] / "evidence" / "report_data.json")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("index.html"))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.data, args.output, args.strict), ensure_ascii=False))


if __name__ == "__main__":
    main()
