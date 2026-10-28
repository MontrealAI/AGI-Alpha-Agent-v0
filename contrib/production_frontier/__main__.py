# SPDX-License-Identifier: Apache-2.0
"""Read an exact local brief and return a non-authorizing construction witness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from alpha_factory_v1.core.runtime.successor.protocol import load_record

from .engine import ConstructionPolicy, ProductionBrief, ablate, construct
from .verify import verify


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--ablate", action="store_true")
    args = parser.parse_args()
    if args.brief.stat().st_size > 160_000:
        parser.error("brief exceeds 160000 bytes")
    brief = load_record(ProductionBrief, args.brief.read_bytes())
    if args.policy and args.policy.stat().st_size > 16_000:
        parser.error("policy exceeds 16000 bytes")
    policy = load_record(ConstructionPolicy, args.policy.read_bytes()) if args.policy else ConstructionPolicy()
    report = ablate(brief, policy) if args.ablate else construct(brief, policy)
    original = report["original"] if args.ablate else report
    if original["best"] and not verify(brief, policy, original):
        raise ValueError("independent witness replay failed")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
