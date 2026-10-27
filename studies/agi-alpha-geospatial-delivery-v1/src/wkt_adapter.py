# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from pyproj import CRS
from shapely import from_wkt
from shapely.geometry import mapping


def adapt(path: Path, binding: dict[str, Any]) -> dict[str, Any]:
    crs = CRS.from_user_input(binding["source_crs"])
    fields = binding["property_columns"]
    if not {"OBJECTID", "INDEX_PARC", "ARROND"}.issubset(fields):
        raise ValueError("The mission must bind source identity, park reference and borough separately")
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=binding["delimiter"])
        required = {binding["geometry_column"], *fields.values()}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Mission binding references absent columns")
        features = []
        for row in reader:
            geometry = from_wkt(row[binding["geometry_column"]])
            properties = {target: row[source] for target, source in fields.items()}
            properties["_input_fields"] = row
            features.append(
                {
                    "type": "Feature",
                    "properties": properties,
                    "geometry": mapping(geometry),
                }
            )
    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": crs.to_string()}},
        "features": features,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = adapt(args.input, json.loads(args.binding.read_text()))
    args.output.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
