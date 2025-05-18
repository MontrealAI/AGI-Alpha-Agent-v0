"""Helper module for the Alpha‑AGI Marketplace demo."""

from __future__ import annotations

from pathlib import Path

from .marketplace import MarketplaceClient, load_job, submit_job, parse_args
from .alpha_scan import scan_equity_alpha

# Directory containing the demo resources
DEMO_PATH = Path(__file__).resolve().parent

# Sample job JSON used by quick-start examples
SAMPLE_JOB = DEMO_PATH / "examples" / "sample_job.json"

# Bash helper script for posting jobs to the orchestrator
POST_JOB_SCRIPT = DEMO_PATH / "scripts" / "post_job.sh"

__all__ = [
    "DEMO_PATH",
    "SAMPLE_JOB",
    "POST_JOB_SCRIPT",
    "MarketplaceClient",
    "load_job",
    "submit_job",
    "parse_args",
    "scan_equity_alpha",
]
