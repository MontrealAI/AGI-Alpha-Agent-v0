# SPDX-License-Identifier: Apache-2.0
"""Workflow helper that emits structured Repo-Healer artifacts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .failure_bundle_builder import build_bundle_from_github_event


def main() -> int:
    """Build a failure bundle and candidate payload from GitHub event JSON."""
    parser = argparse.ArgumentParser(description="Build repo-healer bundle from workflow_run event")
    parser.add_argument("--event-path", default=os.getenv("GITHUB_EVENT_PATH", ""))
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN", ""))
    parser.add_argument("--bundle-out", default="repo_healer_bundle.json")
    parser.add_argument("--candidates-out", default="repo_healer_candidates.json")
    parser.add_argument("--run-attempt-threshold", type=int, default=2)
    args = parser.parse_args()

    bundle = build_bundle_from_github_event(
        event_path=Path(args.event_path),
        repository=args.repository,
        token=args.token or None,
        run_attempt_threshold=args.run_attempt_threshold,
    )
    Path(args.bundle_out).write_text(json.dumps(bundle.to_dict(), indent=2), encoding="utf-8")
    Path(args.candidates_out).write_text("[]\n", encoding="utf-8")
    print(json.dumps(bundle.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
