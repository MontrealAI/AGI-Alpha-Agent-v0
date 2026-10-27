# SPDX-License-Identifier: Apache-2.0
"""Separate-process recipient; receives the same explicit snapshot grant in both arms."""
import importlib.util
import json
import sys
from pathlib import Path

bundle, input_path, output_path = map(Path, sys.argv[1:])
request = json.loads(input_path.read_text())
assert request["grant"]["scope"] == "independent-snapshot-revalidation-only"
assert request["grant"]["execute_authorized"] is True
assert request["grant"]["rights_current"] is True
spec = importlib.util.spec_from_file_location("received_continuity", bundle / "continuity.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
answers = [module.process(request["packet"], c["mission"], c["event"]) for c in request["cases"]]
with output_path.open("x", encoding="utf-8") as out:
    out.write(json.dumps(answers, indent=2, allow_nan=False) + "\n")
