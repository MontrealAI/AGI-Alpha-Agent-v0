# SPDX-License-Identifier: Apache-2.0
"""Clean workspace artifacts to reclaim disk space."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

DEFAULT_TARGETS = (
    Path("tests/contracts/node_modules"),
    Path("alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/node_modules"),
    Path("alpha_factory_v1/core/interface/web_client/node_modules"),
)

EXTRA_TARGETS = (
    Path(".pytest_cache"),
    Path(".hypothesis"),
    Path(".mypy_cache"),
    Path(".ruff_cache"),
    Path(".coverage"),
    Path("artifacts"),
    Path("ledger"),
    Path("vector_mem.db"),
    Path("improver_log.json"),
    Path("selector_ablation.csv"),
    Path("alpha_factory_v1/demos/meta_agentic_agi_v2/meta_agentic_agi_demo_v2.sqlite"),
)


def _delete_path(path: Path, dry_run: bool) -> bool:
    if not path.exists():
        return False
    if dry_run:
        return True
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return True


def _collect_targets(include_all: bool) -> tuple[Path, ...]:
    if include_all:
        return DEFAULT_TARGETS + EXTRA_TARGETS
    return DEFAULT_TARGETS


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove large local caches and node_modules to free disk space.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Also remove test/coverage caches and artifacts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be removed without deleting anything.",
    )
    args = parser.parse_args()

    removed_any = False
    for target in _collect_targets(args.all):
        if _delete_path(target, args.dry_run):
            removed_any = True
            suffix = "(dry-run)" if args.dry_run else ""
            print(f"Removed {target}{suffix}")

    if not removed_any:
        print("No cleanup targets found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
