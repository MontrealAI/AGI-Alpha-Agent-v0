# SPDX-License-Identifier: Apache-2.0
import sys
from pathlib import Path


def main() -> None:
    """Entry-point for Meta-Agentic AGI v3 demo."""
    repo_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo_root))
    from alpha_factory_v1.demos.meta_agentic_agi_v3.meta_agentic_agi_demo_v3 import main as demo_main

    demo_main()


if __name__ == "__main__":
    main()
