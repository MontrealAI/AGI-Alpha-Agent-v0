#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate real local inference, review, export and recovery against a pinned model."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import time

import httpx

from alpha_factory_v1.core.runtime.engine import Engine
from alpha_factory_v1.core.runtime.models import Mission, RuntimeConfig
from alpha_factory_v1.core.runtime.store import Journal, digest
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def main() -> None:
    """Run the supplied llama.cpp binary on loopback and retain public evidence."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--with-code", action="store_true", help="Also generate, sandbox, review and export code")
    args = parser.parse_args()
    with args.model.open("rb") as source:
        model_hash = hashlib.file_digest(source, "sha256").hexdigest()
    if model_hash != args.sha256:
        raise ValueError("model checksum mismatch")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="alpha-real-model-") as temporary:
        folder = Path(temporary)
        with (folder / "server.log").open("w") as log:
            process = subprocess.Popen(
                [
                    str(args.server.resolve()),
                    "--model",
                    str(args.model.resolve()),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--ctx-size",
                    "4096",
                    "--threads",
                    "8",
                    "--alias",
                    "qwen3-4b-pinned",
                    "--no-webui",
                ],
                stdout=log,
                stderr=log,
            )
            try:
                with httpx.Client(trust_env=False, timeout=2) as client:
                    for _ in range(240):
                        if process.poll() is not None:
                            raise RuntimeError("local model server exited during startup")
                        try:
                            if client.get(f"http://127.0.0.1:{port}/health").status_code == 200:
                                break
                        except httpx.HTTPError:
                            pass
                        time.sleep(0.25)
                    else:
                        raise TimeoutError("local model server did not become ready")
                cfg = RuntimeConfig(
                    llm_url=f"http://127.0.0.1:{port}/v1",
                    llm_model="qwen3-4b-pinned",
                    llm_key_env="ALPHA_AGENT_VALIDATION_UNUSED",
                    llm_timeout=240,
                    max_output_tokens=900,
                    allow_code_execution=args.with_code,
                )
                journal = Journal.initialize(folder / "agent", cfg)
                request = Mission.model_validate_json(
                    (Path(__file__).resolve().parents[1] / "examples/missions/research.json").read_bytes()
                )
                engine = Engine(journal)
                result = engine.execute(journal.submit(request)["id"])
                if result["inference"]["mode"] != "local_inference":
                    raise AssertionError("expected real local inference")
                engine.review(
                    result["id"],
                    result["revision"],
                    digest(result["result"]),
                    True,
                    "Validation harness: exact source quotations verified; semantic claims remain reviewable.",
                )
                exported = engine.export(result["id"])
                coding = None
                if args.with_code:
                    code_input = json.loads(
                        (Path(__file__).resolve().parents[1] / "examples/missions/code.json").read_bytes()
                    )
                    code_input["work"]["candidate"] = ""
                    generated = engine.execute(journal.submit(Mission.model_validate(code_input))["id"])
                    assert generated["inference"]["mode"] == "local_inference"
                    assert generated["result"]["accuracy"] == 1.0
                    engine.review(
                        generated["id"],
                        generated["revision"],
                        digest(generated["result"]),
                        True,
                        "Actual generated candidate passed held-out cases and isolated replay.",
                    )
                    coding = {
                        "result": generated["result"],
                        "inference": generated["inference"],
                        "artifact_hash": digest(engine.export(generated["id"])),
                    }
                journal.backup(folder / "private-backup.zip")
                restored = Journal.restore(folder / "private-backup.zip", folder / "restored")
                if restored.verify() != journal.verify():
                    raise AssertionError("recovered journal differs")
                evidence = {
                    "model_file": args.model.name,
                    "coding": coding,
                    "model_sha256": model_hash,
                    "server_version": subprocess.check_output(
                        [str(args.server), "--version"], text=True, stderr=subprocess.STDOUT
                    ).strip(),
                    "verified_quote_count": len(result["result"]["findings"]),
                    "elapsed_seconds": result["elapsed_seconds"],
                    "inference": result["inference"],
                    "result": result["result"],
                    "verification": result["verification"],
                    "artifact_hash": digest(exported),
                    "recovery": restored.verify(),
                    "limits": (
                        "One supplied-source research task; not a general-intelligence or "
                        "financial-performance benchmark."
                    ),
                }
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(evidence, indent=2) + "\n")
                print(
                    json.dumps(
                        {
                            "verified_quote_count": evidence["verified_quote_count"],
                            "elapsed_seconds": evidence["elapsed_seconds"],
                            "output": str(args.output),
                        }
                    )
                )
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)


if __name__ == "__main__":
    main()
