# SPDX-License-Identifier: Apache-2.0
"""Check that the local RSS sampler observes a known child allocation."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import resource
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sampler", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("prospective_load_measurement", args.sampler)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    before = module.tree_rss_bytes()
    child = subprocess.Popen(
        [
            "node",
            "-e",
            'const b=Buffer.alloc(32*1024*1024,1);process.stdout.write("ready\\n");'
            "setTimeout(()=>process.stdout.write(String(b.length)),750)",
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert child.stdout.readline() == "ready\n"
    samples = []
    while child.poll() is None:
        samples.append(module.tree_rss_bytes())
        time.sleep(0.02)
    output, _ = child.communicate(timeout=5)
    receipt = {
        "schema": "agialpha.rss-sampler-sanity.v1",
        "child_exit": child.returncode,
        "child_confirmed_allocation_bytes": int(output),
        "baseline_bytes": before,
        "sampled_peak_bytes": max(samples),
        "sampled_growth_bytes": max(samples) - before,
        "samples": len(samples),
        "max_single_completed_child_rss_bytes": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * 1024,
        "max_python_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "platform": platform.platform(),
        "sampler_sha256": hashlib.sha256(args.sampler.read_bytes()).hexdigest(),
        "claim": "Sanity check only; sampled sum may miss peaks/double-count shared pages, not a workload peak measurement",
    }
    receipt["passed"] = (
        receipt["sampled_growth_bytes"] >= receipt["child_confirmed_allocation_bytes"] and receipt["child_exit"] == 0
    )
    with args.output.open("x") as stream:
        stream.write(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))
    assert receipt["passed"]


if __name__ == "__main__":
    main()
