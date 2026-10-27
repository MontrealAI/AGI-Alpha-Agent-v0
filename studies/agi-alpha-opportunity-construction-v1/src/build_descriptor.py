# SPDX-License-Identifier: Apache-2.0
"""Build a rights-cleared research capability descriptor after fresh confirmation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Bind actual results without conferring deployment permission."""
    paths = [
        "src/mpc_worker.py",
        "src/study.py",
        "config/technical_protocol.json",
        "evidence/technical_freeze.json",
        "results/origin_confirmation.json",
        "results/successor_confirmation.json",
        "vendor/mpyc-0.11-py3-none-any.whl",
    ]
    for name in ("origin", "successor"):
        result = json.loads((ROOT / f"results/{name}_confirmation.json").read_text())
        assert result["oracle_agreement"] == result["n"] == 120
    descriptor = {
        "schema": "agialpha.research-capability.descriptor.v1",
        "name": "Confidential declared-reserve feasibility instrument",
        "version": "1.0.0",
        "study_date": "2026-10-27",
        "qualification": "Finite synthetic software scope only; not production admission or equipment certification.",
        "scope": "Three parties, two distinct unit-capacity asset slots each, six unit demands; all single/pair or single/pair/triple scenarios; private eligibility, scenario availability and asset-specific withholding.",
        "function": "For every declared scenario there exists an injective eligible usable allocation. One aggregate output bit per independent input world.",
        "provenance": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths},
        "dependencies": "Pinned MPyC 0.11; Python and local authority dependencies in config/dependencies.json.",
        "rights": {
            "new_code": "Apache-2.0",
            "mpyc": "MIT",
            "native_components": "Original licenses preserved",
            "data": "Public synthetic research fixtures; no customer data, protected answers or secrets.",
        },
        "failure_modes": [
            "False or duplicate real asset assertions",
            "Unmodeled physical/transport constraints",
            "Active adversaries or collusion beyond one of three passive parties",
            "Unqualified remote hosts/channels",
            "Information revealed by authorized output or metadata",
            "Journal rollback or new uncontrolled query grants",
            "New capacities/quotas outside the declared function",
        ],
        "reuse": "Reuse executable structure; recheck each mission's scenario meaning; regrant authority separately.",
        "authority": [],
        "live_ens_qualification": False,
        "distribution": "Public research bytes are available for a signed local successor.agent.agi.eth fixture receipt. Real namespace ownership and operational permission need separate live verification.",
        "expected_reuse_scenarios": [3, 6, 12],
        "economic_admission": "No measured incremental E+ gain. The commercial A baseline already owns its originating product. Additional B retention remains subject to its explicit expected-value gate.",
        "same_information_control": "An ordinary library contains the identical executable and scope information.",
        "research_cost": "Actual extraction/publication and hosted-model expenditure is unknown, not zero; no claim of paid-job learning.",
        "recipient_boundary": "Using this instrument does not establish independent cryptographic expertise or confer old mission acceptance.",
    }
    path = ROOT / "config/capability_descriptor.json"
    path.write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n")
    print(path)


if __name__ == "__main__":
    main()
