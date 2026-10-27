#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build a self-contained EN/FR HTML edition from recorded study evidence."""

import json
from pathlib import Path
from typing import Any

WEB = Path(__file__).resolve().parent
STUDY = WEB.parent


def read(path: Path) -> Any:
    return json.loads(path.read_text())


workflow = []
for condition in ["U", "E", "Eplus"]:
    rounds = []
    for packet in ["a", "b"]:
        local = STUDY / "workflow_evidence" / condition / f"receipt_{packet}.json"
        r = read(local)
        rounds.append({"packet": packet.upper(), "seconds": r["elapsed_seconds"]})
    workflow.append({"condition": condition, "rounds": rounds})
data = {
    "cases": read(STUDY / "results/fresh_reports.json"),
    "witness": read(STUDY / "results/information_loss_witness.json"),
    "catalog": read(STUDY / "capability/catalog.json"),
    "workflow": workflow,
}
encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
html = (
    (WEB / "template.html")
    .read_text()
    .replace("__CSS__", (WEB / "style.css").read_text())
    .replace("__JS__", (WEB / "app.js").read_text())
    .replace("__DATA__", encoded)
)
(WEB / "index.html").write_text(html)
print(f"Built index.html: {len(html.encode())} bytes; {len(data['cases'])} recorded cases")
