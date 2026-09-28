# SPDX-License-Identifier: Apache-2.0
# References to "AGI" and "superintelligence" describe aspirational goals
# and do not indicate the presence of a real general intelligence.
# Use at your own risk. Nothing herein constitutes financial advice.
# MontrealAI and the maintainers accept no liability for losses incurred.
"""Zero-data launcher for the α‑AGI Insight demo.

This wrapper enforces offline execution by setting ``ALPHA_AGI_OFFLINE=true``
before delegating to :mod:`official_demo_final`. It guarantees the search loop
operates without network dependencies while retaining the production features of
the official demo.
"""
from __future__ import annotations

import os
import sys
from typing import List

if __package__ is None:  # pragma: no cover - allow direct execution
    import pathlib
    import sys

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
    __package__ = "alpha_factory_v1.demos.alpha_agi_insight_v0"

from .official_demo_final import main as _run_final


def main(argv: List[str] | None = None) -> None:
    """Run the official demo in strict offline mode."""
    previous = os.environ.get("ALPHA_AGI_OFFLINE")
    try:
        os.environ["ALPHA_AGI_OFFLINE"] = "true"
        _run_final(["--offline", *(sys.argv[1:] if argv is None else argv)])
    finally:
        if previous is None:
            os.environ.pop("ALPHA_AGI_OFFLINE", None)
        else:
            os.environ["ALPHA_AGI_OFFLINE"] = previous


if __name__ == "__main__":  # pragma: no cover
    main()
