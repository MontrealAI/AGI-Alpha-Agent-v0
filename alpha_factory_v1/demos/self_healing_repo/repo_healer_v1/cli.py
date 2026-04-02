# SPDX-License-Identifier: Apache-2.0
"""CLI entrypoint for Repo-Healer v1."""

from __future__ import annotations

import argparse
import json
import pathlib

from .engine import EngineOptions, RepoHealerEngine, write_report
from .models import FailureBundle, FailureSignal, PatchCandidate, SupportMode, ValidatorClass


def _load_bundle(path: pathlib.Path) -> FailureBundle:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["annotations"] = [FailureSignal(**a) for a in payload.get("annotations", [])]
    payload["validator_class"] = ValidatorClass(payload.get("validator_class", ValidatorClass.NONE.value))
    payload["support_mode"] = SupportMode(payload.get("support_mode", SupportMode.AUTOPATCH_SAFE.value))
    return FailureBundle(**payload)


def _load_candidates(path: pathlib.Path) -> list[PatchCandidate]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [PatchCandidate(**item) for item in payload]


def main() -> int:
    """Run Repo-Healer v1 in bounded dry-run or apply mode."""
    parser = argparse.ArgumentParser(description="Repo-Healer v1")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--failure-bundle", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--report", default="repo_healer_report.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()

    engine = RepoHealerEngine(
        pathlib.Path(args.repo).resolve(),
        EngineOptions(dry_run=args.dry_run, report_only=args.report_only),
    )
    bundle = _load_bundle(pathlib.Path(args.failure_bundle))
    candidates = _load_candidates(pathlib.Path(args.candidates))
    report = engine.run(bundle, candidates)
    write_report(report, pathlib.Path(args.report))
    print(json.dumps(report.to_dict(), indent=2))
    if args.report_only:
        return 0
    return 0 if report.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
