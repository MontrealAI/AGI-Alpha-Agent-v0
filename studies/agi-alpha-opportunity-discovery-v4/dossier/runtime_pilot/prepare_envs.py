"""Prepare two isolated, source-recorded qualification environments only."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent


def main() -> None:
    metadata = {}
    for package in ("zarr", "dask"):
        url = f"https://pypi.org/pypi/{package}/json"
        raw = urllib.request.urlopen(url, timeout=25).read()
        data = json.loads(raw)
        (ROOT / "sources" / f"pypi-{package}.json").write_bytes(raw)
        metadata[package] = {
            "url": url, "version": data["info"]["version"],
            "sha256": hashlib.sha256(raw).hexdigest(),
            "retrieved_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "files": [{"filename": row["filename"], "uploaded": row["upload_time_iso_8601"],
                       "sha256": row["digests"]["sha256"]} for row in data["urls"]],
        }
    (ROOT / "sources" / "release_selection.json").write_text(json.dumps(metadata, indent=2) + "\n")
    configurations = {
        "reported": ["zarr==3.1.3", "dask[array]==2025.9.1", "numpy==2.3.3", "numcodecs==0.16.1"],
        "current": [f"zarr=={metadata['zarr']['version']}", f"dask[array]=={metadata['dask']['version']}"],
    }
    for label, requirements in configurations.items():
        environment = ROOT / f"venv_{label}"
        if environment.exists():
            raise RuntimeError(f"Refuse to overwrite {environment}")
        subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
        python = environment / "bin" / "python"
        command = [str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-cache-dir",
                   "--index-url", "https://pypi.org/simple", "--report", str(ROOT / "sources" / f"install-{label}.json"),
                   *requirements]
        (ROOT / "sources" / f"requirements-{label}.txt").write_text("\n".join(requirements) + "\n")
        with (ROOT / "logs" / f"install-{label}.log").open("w") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=240)
        if result.returncode:
            raise RuntimeError(f"Installation failed; see install-{label}.log")
        freeze = subprocess.run([str(python), "-m", "pip", "freeze", "--all"], capture_output=True, text=True, check=True)
        (ROOT / "sources" / f"freeze-{label}.txt").write_text(freeze.stdout)
        print(json.dumps({"environment": label, "requirements": requirements, "installed": True}), flush=True)


if __name__ == "__main__":
    main()
