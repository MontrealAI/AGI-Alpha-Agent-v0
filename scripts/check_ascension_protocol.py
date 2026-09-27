# SPDX-License-Identifier: Apache-2.0
"""Check that the public local-EVM snapshot matches shipped sources and conserves every token."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def check(root: Path) -> dict[str, object]:
    report = json.loads((root / "docs/assets/ascension-protocol/receipt.json").read_text())
    assert report["schema"] == "agialpha.ascension.local-evm.v1" and report["chainId"] == "31337"
    sources = root / "contracts/ascension"
    actual = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources.glob("*.sol")}
    assert actual == report["sources"], "EVM snapshot source hashes do not match the shipped contracts"
    for path in sources.glob("*.sol"):
        assert path.read_bytes() == (root / "tests/contracts/contracts/ascension" / path.name).read_bytes()
    amounts = report["accounting"]
    assert int(amounts["funded"]) == sum(
        int(amounts[k]) for k in ("workerNet", "validatorsNet", "burned", "refunded", "remainingTreasury")
    )
    assert report["nativeDelivery"]["verifiedJournal"]["valid"] is True
    assert all(step["status"] == 1 for step in report["steps"])
    events = [event for step in report["steps"] for event in step["events"]]
    assert any(e["event"] == "SeedSealed" and e["args"]["capsuleHash"] == report["capsuleHash"] for e in events)
    assert any(e["event"] == "Bloomed" and e["args"]["planRoot"] == report["plan"]["planRoot"] for e in events)
    assert any(e["event"] == "Delivered" and e["args"]["resultHash"] == report["resultHash"] for e in events)
    assert sum(int(e["args"]["burned"]) for e in events if e["event"] == "Payout") == int(amounts["burned"])
    assert len({s["transactionHash"] for s in report["steps"]}) == len(report["steps"])
    return {"contracts": len(actual), "transactions": len(report["steps"]), "sources_match": True, "accounting": True}


if __name__ == "__main__":
    print(json.dumps(check(Path(__file__).resolve().parents[1]), indent=2))
