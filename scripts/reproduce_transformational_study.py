#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run an explicit free local complete-campaign study, keeping its signed state."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import time
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.store import Journal, private_write
from alpha_factory_v1.core.runtime.successor.campaign_experiment import (
    CampaignExperiment,
    CampaignUnit,
    PolicyStudy,
)
from alpha_factory_v1.core.runtime.successor.protocol import canonical, safe_json_loads


def _is_exact_type(value: object, expected: type[object]) -> bool:
    """Compare exact types without admitting bool or other subclasses."""
    return type(value) is expected


def read_input(path: Path) -> tuple[dict[str, Any], str]:
    """Hash the same bounded regular-file bytes that are parsed and executed."""
    if path.is_symlink():
        raise ValueError("input must be a regular file, not a symbolic link")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 2_000_000:
            raise ValueError("input must be a bounded regular JSON file")
        raw = stream.read(2_000_001)
    value = safe_json_loads(raw, max_bytes=2_000_000)
    if not isinstance(value, dict):
        raise ValueError("input must be a JSON object")
    return value, hashlib.sha256(raw).hexdigest()


def batch(value: dict[str, Any]) -> list[CampaignUnit]:
    """Read only the bounded complete batch at the point where it is needed."""
    if set(value) != {"schema", "units"} or value["schema"] != "discovery-policy-campaigns/v1":
        raise ValueError("unsupported complete-campaign batch")
    if not _is_exact_type(value["units"], list) or not 1 <= len(value["units"]) <= 64:
        raise ValueError("invalid complete campaign count")
    return [CampaignUnit.model_validate(unit) for unit in value["units"]]


def main() -> None:
    """Require explicit local consent; never replace evidence or a private identity."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--confirmation", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True, help="New private journal directory")
    parser.add_argument("--output", type=Path, required=True, help="New inert public evidence JSON")
    parser.add_argument(
        "--approve-free-local-study",
        action="store_true",
        required=True,
        help="Explicitly approve only this declared bounded free local comparison",
    )
    args = parser.parse_args()
    if args.state.exists() or args.state.is_symlink() or args.output.exists() or args.output.is_symlink():
        parser.error("choose new state and output paths; existing artifacts are never replaced")
    raw_spec, spec_sha256 = read_input(args.spec)
    spec = PolicyStudy.model_validate(raw_spec)
    raw_training, training_sha256 = read_input(args.training)
    training = batch(raw_training)
    started = time.monotonic_ns()
    experiment = CampaignExperiment(Journal.initialize(args.state))
    proposed = experiment.create(spec)
    experiment.approve(spec.study_id, proposed["binding"])
    trained = experiment.train(spec.study_id, training)
    # Terminal files are opened only after the discovery policy has been frozen.
    # These public fixtures are not a claim of blind or independent custody.
    raw_confirmation, confirmation_sha256 = read_input(args.confirmation)
    confirmation = batch(raw_confirmation)
    completed = experiment.confirm(spec.study_id, confirmation, trained["freeze"]["digest"])
    experiment.journal.verify()
    report: dict[str, Any] = experiment.export(spec.study_id)
    report["reproduction"] = {
        "elapsed_nanoseconds": time.monotonic_ns() - started,
        "input_sha256": {"spec": spec_sha256, "training": training_sha256, "confirmation": confirmation_sha256},
        "state": completed["state"],
        "physical_compute_after_unrecorded_crash": "unknown; not charged as zero",
        "human_time_energy_maintenance_migration": "not measured",
        "sampling": "explicit public finite fixtures; not IID, hidden or externally adjudicated",
        "certified_ceiling_escape": False,
    }
    private_write(args.output, canonical(report) + b"\n")
    print(
        f"Retained complete-campaign evidence at {args.output}; no execution, payment or promotion authority exported."
    )


if __name__ == "__main__":
    main()
