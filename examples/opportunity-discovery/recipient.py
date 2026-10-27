# SPDX-License-Identifier: Apache-2.0
"""A fresh local recipient invokes the actual retained observation compiler."""

import hashlib
import json
import os
import sys
from pathlib import Path

from alpha_factory_v1.core.runtime.successor import flywheel_observations as retained
from alpha_factory_v1.core.runtime.successor.protocol import canonical

raw = sys.stdin.buffer.read(131_073)
if len(raw) > 131_072:
    raise ValueError("bounded recipient request required")
problem = retained.ObservationProblem.model_validate_json(raw)
plan = retained.compile_observations(problem)
sys.stdout.buffer.write(
    canonical(
        {
            "plan": plan.model_dump(),
            "process_id": os.getpid(),
            "retained_source_sha256": hashlib.sha256(Path(retained.__file__).read_bytes()).hexdigest(),
            "identity_basis": "unauthenticated local process fixture; not an ENS agent",
        }
    )
)
