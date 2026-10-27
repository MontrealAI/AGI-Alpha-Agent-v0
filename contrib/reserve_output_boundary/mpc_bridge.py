# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-root", required=True, type=Path)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--journal", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("reserve_parent_study", args.research_root / "src/study.py")
    if spec is None or spec.loader is None:
        raise ValueError("missing pinned parent execution module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.execute(args.inputs, args.port, args.output, args.journal)
    (args.output / "answer.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "executed", "wall_seconds": result["wall_seconds"]}))


if __name__ == "__main__":
    main()
