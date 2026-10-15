# SPDX-License-Identifier: Apache-2.0
"""Stateless bounded work entry point for an explicitly authorized Fleet adapter.

Fleet owns process isolation, durable grants, actor/source/boot binding and STOP.
This process creates no identity or credentials, opens no network connection,
and cannot approve work or authorize marketplace settlement.
"""
from __future__ import annotations

import base64
import sys
import time
from typing import Any

from . import work
from .work_spec import MAX_BYTES, read_spec
from .models import Allocation, Forecast, Research, Schedule
from .store import canonical, digest


def execute(raw: bytes) -> dict[str, Any]:
    """Run only bounded deterministic, supplied-input mission kinds."""
    spec, spec_hash = read_spec(raw)
    if spec.executor != "fleet-linux-v1":
        raise ValueError("The work specification must explicitly select Fleet")
    mission = spec.mission
    started = time.monotonic()

    def checkpoint() -> None:
        if time.monotonic() - started > 60:
            raise TimeoutError("Fleet work exceeded its sixty-second computation bound")

    if isinstance(mission.work, Allocation):
        result = work.allocation(mission, checkpoint, 10000)
    elif isinstance(mission.work, Schedule):
        result = work.schedule(mission, checkpoint, 10000)
    elif isinstance(mission.work, Forecast):
        result = work.forecast(mission)
    elif isinstance(mission.work, Research):
        result = work.research(mission)
    else:
        raise ValueError("Fleet adapter does not permit code execution or model/network work")
    checkpoint()
    verification = work.verify_result(mission, result)
    output = {
        "schema": "agialpha.fleet-work-result.v1",
        "spec_hash": spec_hash,
        "mission_hash": digest(mission.model_dump()),
        "canonical_mission": canonical(mission.model_dump()).decode(),
        "canonical_result": canonical(result).decode(),
        "spec_base64": base64.b64encode(raw).decode(),
        "result": result,
        "result_hash": digest(result),
        "verification": verification,
        "authority": "computed-unreviewed; no wallet, approval or settlement authority",
    }
    if len(canonical(output)) > MAX_BYTES:
        raise ValueError("Fleet work output exceeds its bound")
    return output


def main() -> None:
    """Read exactly one bounded work file through stdin; output one JSON result."""
    raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    result = execute(raw)
    sys.stdout.buffer.write(canonical(result) + b"\n")


if __name__ == "__main__":
    main()
