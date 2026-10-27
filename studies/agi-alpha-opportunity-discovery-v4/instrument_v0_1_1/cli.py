# SPDX-License-Identifier: Apache-2.0
"""Execute a local source-bound evidence audit without modifying source artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from instrument_v0_1_1.audit import audit
from instrument_v0_1_1.qif_reader import EvidenceError


def main() -> int:
    """Write an audit or a structured request/integrity error."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text())
        report = audit(request, args.request.resolve().parent)
    except (EvidenceError, OSError, ValueError) as error:
        report = {
            "schema_version": "0.1",
            "error": f"{type(error).__name__}: {error}",
            "physical_reuse_admitted": False,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report), file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "mission": report["mission"]["id"],
                "result": report["mission_result"],
                "output": str(args.output),
                "identity": report["identity"]["complete_identity_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
