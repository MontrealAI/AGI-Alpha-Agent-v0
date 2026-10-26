# SPDX-License-Identifier: Apache-2.0
"""A separately declared exploratory transfer using the unchanged frozen driver."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from production_campaign import campaign, verify_freeze

ROOT = Path(__file__).resolve().parents[1]
PARENT = "f422f5c88283852dda8157d766fe5c70c0e0b9197297c8136924ea5b580bdd34"


def main() -> None:
    freeze = ROOT / "protocol/secondary-transfer-freeze.json"
    identity = (ROOT / "protocol/secondary-transfer-freeze.sha256").read_text().split()[0]
    raw = freeze.read_bytes()
    if hashlib.sha256(raw).hexdigest() != identity:
        raise ValueError("SECONDARY_FREEZE_IDENTITY")

    def guard() -> dict[str, object]:
        verify_freeze(ROOT, freeze, identity)
        parent_check = verify_freeze(ROOT, ROOT / "protocol/production-freeze.json", PARENT)
        return {"accepted": True, "parentCheck": parent_check}

    guard()
    protocol = json.loads((ROOT / "protocol/secondary-transfer.json").read_text())
    result = campaign(ROOT, protocol, "transfer", ROOT / "outputs/secondary-transfer", guard)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
