# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("alpha_source_candidate_worker", HERE / "source_worker.py")
if spec is None or spec.loader is None:
    raise ValueError("candidate worker unavailable")
worker_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker_module)


def create_candidate_app(journal: Any, registry: Path, *, node: Path, git: Path, python: Path) -> Any:
    worker = worker_module.SourceAssuranceWorker(
        registry, journal.root / "source-assurance", node=node, git=git, python=python
    )
    policy = worker_module.candidate_policy(journal, worker)
    transport = worker_module.load_transport()
    app = transport.create_strategy_app(
        journal,
        worker,
        policy,
        static_files={
            "/": HERE / "strategy.html",
            "/strategy.js": HERE / "strategy.js",
            "/strategy.css": HERE / "strategy.css",
        },
    )
    app.state.source_assurance_worker = worker
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Source-assurance candidate; owner profile adoption required")
    parser.add_argument("--existing-home", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--node", required=True, type=Path)
    parser.add_argument("--git", required=True, type=Path)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--prepare-scope")
    parser.add_argument("--run-id")
    parser.add_argument("--created-at")
    parser.add_argument("--expires-at")
    parser.add_argument("--port", type=int, default=8788)
    args = parser.parse_args()
    from alpha_factory_v1.core.runtime.store import Journal

    journal = Journal(args.existing_home)
    if args.prepare_scope:
        if not all((args.run_id, args.created_at, args.expires_at)):
            parser.error("preparation requires a fresh run ID and explicit created/expiry dates")
        worker = worker_module.SourceAssuranceWorker(
            args.registry, journal.root / "source-assurance", node=args.node, git=args.git, python=args.python
        )
        worker_module.candidate_policy(journal, worker)
        print(
            json.dumps(
                worker.prepare_input(
                    args.prepare_scope, args.run_id, created_at=args.created_at, expires_at=args.expires_at
                ),
                indent=2,
            )
        )
        return
    if any((args.run_id, args.created_at, args.expires_at)) or not 1024 <= args.port <= 65535:
        parser.error("serve requires a bounded loopback port and no preparation-only arguments")
    app = create_candidate_app(journal, args.registry, node=args.node, git=args.git, python=args.python)
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
