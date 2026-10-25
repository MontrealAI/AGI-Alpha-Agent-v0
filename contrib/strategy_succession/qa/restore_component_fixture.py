# SPDX-License-Identifier: Apache-2.0
"""Restore one recorded UI-test fixture; never label it fresh executor evidence."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
archive = ROOT / "evidence/development-checkpoint.zip"
custody = json.loads((ROOT / "evidence/development-checkpoint.json").read_text())
assert hashlib.sha256(archive.read_bytes()).hexdigest() == custody["sha256"]
location = json.loads((ROOT / "development/integrated-before-final-review/raw-record-location.json").read_text())
with zipfile.ZipFile(archive) as source:
    info = source.getinfo(location["member"])
    assert info.file_size == location["bytes"] < 8_000_000
    body = source.read(info)
assert hashlib.sha256(body).hexdigest() == location["sha256"]
target = ROOT / "acceptance-public/integrated-journey.json"
target.parent.mkdir(exist_ok=True)
target.write_bytes(body)
print("Restored recorded rendering fixture only; not new browser/executor acceptance.")
