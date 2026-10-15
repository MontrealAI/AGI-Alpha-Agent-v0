# SPDX-License-Identifier: Apache-2.0
"""Compute an exact bounded plan; never execute selected tasks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .planner import solve


def main() -> None:
    """Read supplied assumptions and emit a reproducible JSON plan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).parent / "fixtures" / "supplier-plan.json")
    args = parser.parse_args()
    try:
        with args.input.open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError("Input exceeds 64 KiB")

        def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate JSON key")
                result[key] = value
            return result

        result = solve(json.loads(raw, object_pairs_hook=unique))
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
