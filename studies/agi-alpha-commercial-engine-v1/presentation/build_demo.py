# SPDX-License-Identifier: Apache-2.0
import argparse
import base64
import hashlib
import json
import zipfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--template", type=Path, default=Path(__file__).with_name("demo_template.html"))
p.add_argument("--data", type=Path, required=True)
p.add_argument("--packet", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
data = json.loads(a.data.read_text())
if not isinstance(data, dict) or not isinstance(data.get("actual"), dict):
    raise SystemExit("Expected a data object with actual evidence.")
packet = a.packet.read_bytes()
digest = hashlib.sha256(packet).hexdigest()
if data["actual"].get("packet_sha256") != digest:
    raise SystemExit("Supplied actual.packet_sha256 does not match the exact embedded packet.")
if data["actual"].get("packet_filename") != a.packet.name:
    raise SystemExit("Supplied actual.packet_filename must identify the exact packet basename.")
with zipfile.ZipFile(a.packet) as z:
    bad = z.testzip()
    if bad is not None:
        raise SystemExit("Invalid ZIP member: " + bad)
template = a.template.read_text()
if template.count("__DEMO_DATA__") != 1 or template.count("__PACKET_BASE64__") != 1:
    raise SystemExit("Template placeholders are missing or ambiguous.")
encoded = (
    json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    .replace("<", "\\u003c")
    .replace("\u2028", "\\u2028")
    .replace("\u2029", "\\u2029")
)
output = template.replace("__DEMO_DATA__", encoded).replace(
    "__PACKET_BASE64__", base64.b64encode(packet).decode("ascii")
)
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(output)
print(
    json.dumps(
        {
            "output": str(a.output),
            "packet_sha256": digest,
            "html_sha256": hashlib.sha256(a.output.read_bytes()).hexdigest(),
            "packet_bytes": len(packet),
            "data_sha256": hashlib.sha256(a.data.read_bytes()).hexdigest(),
        },
        indent=2,
    )
)
