# SPDX-License-Identifier: Apache-2.0
"""Fetch public PyPI JSON metadata only; never fetch a wheel or source body."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.request


def subset_file(row: dict) -> dict:
    names = ("filename", "packagetype", "python_version", "requires_python", "size", "url", "digests",
             "upload_time_iso_8601", "yanked", "yanked_reason")
    return {key: row.get(key) for key in names}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--package", action="append", default=[])
    p.add_argument("--exact", action="append", default=[])
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    requests = [(name, None) for name in args.package]
    for item in args.exact:
        name, version = item.split("==", 1)
        requests.append((name, version))
    if len(requests) > 20:
        raise ValueError("METADATA_REQUEST_BUDGET")
    for name, version in requests:
        if name not in {"starlette", "pydantic", "fastapi", "pydantic-settings", "annotated-doc", "ruff"}:
            raise ValueError("PACKAGE_NOT_ALLOWED")
        if version is not None and not re.fullmatch(r"[0-9A-Za-z.+!-]+", version):
            raise ValueError("VERSION_IDENTITY")
        url = f"https://pypi.org/pypi/{name}/" + (f"{version}/" if version else "") + "json"
        target = args.out / (name + ("-" + version if version else "-project") + ".json")
        if target.exists():
            raise ValueError("METADATA_OUTPUT_EXISTS")
        event = {"url": url, "kind": "metadata_only", "source_or_wheel_body": False,
                 "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        start, cpu = time.perf_counter(), time.process_time()
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "AGI-ALPHA-useful-work-v2-metadata-curator"})
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.geturl() != url:
                    raise ValueError("UNEXPECTED_METADATA_REDIRECT")
                raw = response.read(16_000_001)
            if len(raw) > 16_000_000:
                raise ValueError("METADATA_BYTE_BUDGET")
            value = json.loads(raw)
            info = value["info"]
            result = {"schema": "useful-work-v2-pypi-metadata/v1", "source_url": url,
                      "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      "raw_metadata_sha256": hashlib.sha256(raw).hexdigest(), "raw_metadata_bytes": len(raw),
                      "info": {key: info.get(key) for key in ("name", "version", "requires_python", "requires_dist", "license_expression", "license")},
                      "urls": [subset_file(row) for row in value.get("urls", [])],
                      "releases": {v: [subset_file(row) for row in files] for v, files in value.get("releases", {}).items()},
                      "last_serial": value.get("last_serial"), "source_or_wheel_body_downloaded": False}
            target.write_text(json.dumps(result, indent=2) + "\n")
            event.update(success=True, raw_metadata_bytes=len(raw), output=str(target), output_bytes=target.stat().st_size,
                         output_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
            print(json.dumps({"package": name, "requested_version": version, "latest_or_exact_version": info["version"],
                              "release_versions": len(result["releases"]), "metadata_bytes": len(raw),
                              "requires_dist": info.get("requires_dist", [])}), flush=True)
        except Exception as error:
            event.update(success=False, error=type(error).__name__ + ": " + str(error))
            raise
        finally:
            event.update(wall_seconds=time.perf_counter() - start, process_cpu_seconds=time.process_time() - cpu,
                         inference_tokens=None, inference_usd=None)
            with (args.out / "requests.jsonl").open("a") as record:
                record.write(json.dumps(event) + "\n")


if __name__ == "__main__":
    main()
