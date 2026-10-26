# SPDX-License-Identifier: Apache-2.0
"""Embed a reviewed evidence object in an offline bilingual research companion."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    """Render the existing template without network, external assets or secrets."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("index.html"))
    args = parser.parse_args()
    data = json.loads(args.data.read_text())
    if not isinstance(data, dict):
        raise ValueError("Evidence must be a JSON object")
    encoded = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    template = Path(__file__).with_name("index.template.html").read_text()
    if template.count("__FROZEN_EVIDENCE_JSON__") != 1:
        raise ValueError("Expected exactly one embedded evidence marker")
    args.output.write_text(template.replace("__FROZEN_EVIDENCE_JSON__", encoded))
    print(args.output)


if __name__ == "__main__":
    main()
