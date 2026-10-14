# SPDX-License-Identifier: Apache-2.0
"""Ensure missing evidence and changed outcomes cannot pass the replay verifier."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from verify_and_replay import verify_results

p = argparse.ArgumentParser()
p.add_argument("--replay", type=Path, required=True)
args = p.parse_args()
verify_results(args.replay)
for case in ["missing", "changed-pass", "removed-review", "fake-human", "empty-vectors"]:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "copy"
        shutil.copytree(args.replay, root)
        target = root / "03_Evidence/acceptance/B_after.json"
        if case == "missing":
            target.unlink()
        elif case == "changed-pass":
            data = json.loads(target.read_text())
            data["tests"][0]["passed"] = False
            target.write_text(json.dumps(data))
        elif case == "removed-review":
            target = root / "03_Evidence/OWNER_EFFORT.json"
            data = json.loads(target.read_text())
            data["runs"][0]["reviewChecks"] = 0
            target.write_text(json.dumps(data))
        elif case == "empty-vectors":
            target = root / "03_Evidence/acceptance/sha256_vectors.json"
            data = json.loads(target.read_text())
            data["tests"] = []
            target.write_text(json.dumps(data))
        else:
            target = root / "pilot/status.json"
            data = json.loads(target.read_text())
            data["participantsObserved"] = 12
            target.write_text(json.dumps(data))
        try:
            if case == "fake-human":
                from verify_and_replay import verify_sources

                verify_sources(root)
            else:
                verify_results(root)
        except (ValueError, FileNotFoundError):
            pass
        else:
            raise RuntimeError("Negative control incorrectly accepted: " + case)
print("Five verifier negative controls were refused as intended.")
