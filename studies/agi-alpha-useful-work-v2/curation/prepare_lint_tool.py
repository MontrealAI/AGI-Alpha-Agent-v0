# SPDX-License-Identifier: Apache-2.0
"""Provision the exact Ruff version observed in the repository CI lock."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import urllib.request
import zipfile

from pip._vendor.packaging.tags import sys_tags
from pip._vendor.packaging.utils import parse_wheel_filename


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    start, cpu = time.perf_counter(), time.process_time()
    steps = []
    result = {"complete": False, "metadata_path": str(args.metadata), "requests": [], "money_usd": None}
    try:
        raw_metadata = args.metadata.read_bytes()
        metadata = json.loads(raw_metadata)
        if metadata["info"]["name"] != "ruff" or metadata["info"]["version"] != "0.12.5":
            raise ValueError("REPOSITORY_CI_RUFF_VERSION_REQUIRED")
        result["metadata_sha256"] = hashlib.sha256(raw_metadata).hexdigest()
        tags = {tag: rank for rank, tag in enumerate(sys_tags())}
        candidates = []
        for item in metadata["urls"]:
            if item["packagetype"] != "bdist_wheel" or item["yanked"]:
                continue
            _, _, _, supported = parse_wheel_filename(item["filename"])
            ranks = [tags[tag] for tag in supported if tag in tags]
            if ranks:
                candidates.append((min(ranks), item["filename"], item))
        item = min(candidates)[2]
        if not item["url"].startswith("https://files.pythonhosted.org/packages/"):
            raise ValueError("OFFICIAL_WHEEL_URL_REQUIRED")
        t = time.perf_counter()
        with urllib.request.urlopen(item["url"], timeout=30) as response:
            if response.geturl() != item["url"]:
                raise ValueError("UNEXPECTED_REDIRECT")
            raw = response.read(20_000_001)
        result["requests"].append({"url": item["url"], "bytes": len(raw), "wall_seconds": time.perf_counter() - t})
        if len(raw) > 20_000_000 or hashlib.sha256(raw).hexdigest() != item["digests"]["sha256"]:
            raise ValueError("WHEEL_IDENTITY")
        wheel = args.out / item["filename"]
        wheel.write_bytes(raw)
        result["wheel"] = item
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.namelist():
                if ".dist-info/" in member and Path(member).name.lower().startswith("license"):
                    (args.out / Path(member).name).write_bytes(archive.read(member))
        command = [sys.executable, "-m", "pip", "--isolated", "install", "--no-index", "--no-deps",
                   "--no-compile", "--target", str(args.out / "site"), str(wheel)]
        t = time.perf_counter()
        completed = subprocess.run(command, text=True, capture_output=True, timeout=120, check=False)
        steps.append({"command": command, "exit_code": completed.returncode,
                      "wall_seconds": time.perf_counter() - t})
        (args.out / "install.stdout").write_text(completed.stdout)
        (args.out / "install.stderr").write_text(completed.stderr)
        if completed.returncode:
            raise ValueError("OFFLINE_INSTALL_FAILED")
        result["complete"] = True
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result.update(steps=steps, wall_seconds=time.perf_counter() - start, cpu_seconds=time.process_time() - cpu,
                  child_cpu_seconds=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime
                  + resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime)
    (args.out / "preparation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in {"wheel", "steps", "requests"}}))
    if not result["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
