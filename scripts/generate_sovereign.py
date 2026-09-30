# SPDX-License-Identifier: Apache-2.0
"""Validate native signed fixtures and preserve the original Sovereign presentation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile
import uuid

from alpha_factory_v1.core.runtime.store import Journal, digest
from alpha_factory_v1.demos.sovereign_agentic_agialpha_agent_v0.models import Mandate
from alpha_factory_v1.demos.sovereign_agentic_agialpha_agent_v0.service import examples
from alpha_factory_v1.demos.sovereign_agentic_agialpha_agent_v0.workbench import STAGES, Workbench, verify_packet
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

DEMO = "sovereign_agentic_agialpha_agent_v0"


def record(root: Path) -> None:
    """Explicitly regenerate public fixtures with a temporary identity and automated reviews."""
    cases = {}
    with tempfile.TemporaryDirectory(prefix="sovereign-public-fixtures-") as temp:
        bench = Workbench(Journal.initialize(Path(temp) / "workspace"))
        for name, value in examples().items():
            ident = str(uuid.uuid4())
            bench.create(Mandate.model_validate(value), ident)
            for stage in STAGES:
                job = bench.advance(ident)["jobs"][stage]
                bench.review(
                    ident,
                    job["revision"],
                    digest(job["result"]),
                    True,
                    "AUTOMATED GALLERY FIXTURE APPROVAL. Not independent validation or operational authorization.",
                )
            packet = bench.export(ident)
            verify_packet(packet, bench.journal.public)
            cases[name] = {
                "packet_json": json.dumps(packet, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            }
    document = {
        "schema": "sovereign-recordings-v1",
        "scope": "Native synthetic fixtures with automated approvals",
        "cases": cases,
    }
    (root / f"alpha_factory_v1/demos/{DEMO}/recorded.json").write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8"
    )


def build(root: Path) -> None:
    """Verify all receipts before copying deterministic gallery assets."""
    source = root / f"alpha_factory_v1/demos/{DEMO}"
    recordings = json.loads((source / "recorded.json").read_text(encoding="utf-8"))
    if recordings["schema"] != "sovereign-recordings-v1" or set(recordings["cases"]) != set(examples()):
        raise ValueError("Sovereign recordings do not match the packaged cases")
    for case in recordings["cases"].values():
        packet = json.loads(case["packet_json"])
        verify_packet(packet, packet["public_key"])
    target = root / f"docs/{DEMO}"
    target.mkdir(parents=True, exist_ok=True)
    if not (target / "research.html").exists() and (target / "index.html").exists():
        shutil.copy2(target / "index.html", target / "research.html")
    for name in ("app.js", "style.css"):
        shutil.copy2(source / "web" / name, target / name)
    for name in ("recorded.json", "examples.json"):
        shutil.copy2(source / name, target / name)
    html = (source / "web/index.html").read_text(encoding="utf-8").replace('data-mode="local"', 'data-mode="gallery"')
    (target / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--record", action="store_true", help="Create new native fixtures with explicitly automated reviews"
    )
    arguments = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    if arguments.record:
        record(repository)
    build(repository)
