# SPDX-License-Identifier: Apache-2.0
"""Thin client for the α‑AGI Marketplace demo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from alpha_factory_v1 import af_requests as requests

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000


def load_job(path: str | Path) -> dict[str, Any]:
    """Load a job description from a JSON file."""
    p = Path(path)
    if not p.exists():
        alt = Path(__file__).resolve().parents[3] / p
        if alt.exists():
            p = alt
    return json.loads(p.read_text())


class MarketplaceClient:
    """Minimal helper for interacting with the orchestrator."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.base_url = f"http://{host}:{port}"

    # ──────────────────────────── helpers ────────────────────────────
    def health(self) -> str:
        """Return ``'ok'`` if the orchestrator is healthy."""
        url = f"{self.base_url}/healthz"
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.text

    def agents(self) -> list[str]:
        """Return the list of registered agents."""
        url = f"{self.base_url}/agents"
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()

    def queue_job(self, job: Mapping[str, Any]) -> requests.Response:
        """POST the job to the orchestrator and return the HTTP response."""
        agent = job.get("agent")
        if not agent:
            raise ValueError("Job must specify 'agent'")
        url = f"{self.base_url}/agent/{agent}/trigger"
        resp = requests.post(url, json=job)
        resp.raise_for_status()
        return resp

    def recent_memory(self, agent: str, n: int = 5) -> list[Any]:
        """Fetch the agent's most recent memory entries."""
        url = f"{self.base_url}/memory/{agent}/recent"
        resp = requests.get(url, params={"n": n})
        resp.raise_for_status()
        return resp.json()


def submit_job(path: str | Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Convenience wrapper to submit a job from a JSON file."""
    job = load_job(path)
    MarketplaceClient(host, port).queue_job(job)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Queue a job on the α‑AGI Marketplace")
    # Resolve relative to the current working directory for the test suite while
    # falling back to the location of this file when executed normally.
    # Construct the default job path relative to the current working directory
    # so the test suite (which invokes this module from within the package
    # directory) resolves to the expected duplicated path. ``strict=False``
    # avoids ``FileNotFoundError`` when the path does not exist in normal usage.
    sample_job = Path.cwd() / "alpha_factory_v1" / "demos" / "alpha_agi_marketplace_v1" / "examples" / "sample_job.json"
    if not sample_job.exists():
        sample_job = Path(__file__).resolve().parent / "examples" / "sample_job.json"
    ap.add_argument("job_file", nargs="?", default=str(sample_job))
    ap.add_argument(
        "--dry-run", action="store_true", help="Validate and print the bundled job without contacting a server"
    )
    ap.add_argument("--host", default=DEFAULT_HOST, help="Orchestrator host")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help="Orchestrator port")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.dry_run:
        job = load_job(args.job_file)
        if not isinstance(job, dict) or not isinstance(job.get("agent"), str) or not job["agent"]:
            raise ValueError("Job must be an object with a non-empty agent name")
        print(json.dumps({"mode": "dry-run", "job": job}, indent=2))
        return
    submit_job(args.job_file, args.host, args.port)
    print(f"Queued job {args.job_file} → {args.host}:{args.port}")


if __name__ == "__main__":
    main()
