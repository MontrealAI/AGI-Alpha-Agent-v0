# SPDX-License-Identifier: Apache-2.0
"""Local JSON investigation and continuation entry point."""

import argparse
import json
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.successor.protocol import safe_json_loads
from discovery_means.instrument import advance, solve, verify


def read_bounded(path: Path) -> Any:
    """Read at most the declared input allowance before parsing."""
    with path.open("rb") as stream:
        return safe_json_loads(stream.read(250_001), max_bytes=250_000)


def main() -> None:
    """Construct and check a policy, or consume a supplied observation transcript."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("problem", type=Path)
    parser.add_argument("--transcript", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    problem = read_bounded(args.problem)
    report = solve(problem)
    result = {"construction": report, "verification": verify(problem, report)}
    if args.transcript:
        result["continuation"] = advance(problem, report, read_bounded(args.transcript))
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "worst_cost": report["worst_cost"]}))


if __name__ == "__main__":
    main()
