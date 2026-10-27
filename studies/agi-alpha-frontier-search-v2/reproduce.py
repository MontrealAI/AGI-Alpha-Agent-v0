"""Offline bounded-study replay. Frozen evidence is never overwritten."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def main() -> None:
    frozen = json.loads((ROOT / "protocol/confirmation_freeze.json").read_text())
    for name, digest in frozen["frozen_inputs"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    records = []
    with tempfile.TemporaryDirectory(prefix="agi-alpha-frontier-replay-") as temporary:
        work = Path(temporary) / "study"
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns("paper", "publication", "__pycache__", "*.zip", "qa", "reproduction_receipt.json"))
        commands = [
            [sys.executable, "probes/original_U.py"],
            [sys.executable, "probes/original_E.py"],
            [sys.executable, "discovery_targeted_probe.py"],
            [sys.executable, "probes/final_mechanisms.py"],
            [sys.executable, "probes/independent_confirmation.py"],
            [sys.executable, "economics/model.py"],
            ["node", "integration/native_bridge.mjs", "integration/native_source", "integration/research_input.json", "integration/replay_output"],
        ]
        for command in commands:
            result = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=120)
            records.append({"command": ["python" if x == sys.executable else x for x in command],
                            "returncode": result.returncode, "stdout": result.stdout,
                            "stderr": result.stderr})
            assert result.returncode == 0, records[-1]
        comparisons = []
        for relative in ["results/independent_confirmation.json", "economics/results.json", "discovery_targeted_probe_results.json"]:
            same = json.loads((work / relative).read_text()) == json.loads((ROOT / relative).read_text())
            assert same, relative
            comparisons.append({"file": relative, "semantic_equality": same})
        original = json.loads((ROOT / "integration/output/native_receipt.json").read_text())
        replay = json.loads((work / "integration/replay_output/native_receipt.json").read_text())
        assert len(replay["checks"]) == 19 and all(x["passed"] for x in replay["checks"])
        assert original["genome_sha256"] == replay["genome_sha256"]
        assert original["plan_root"] == replay["plan_root"]
        assert replay["qualification"]["qualified_venture"] is False
        assert replay["qualification"]["collected_cash_usd"] == 0
        summary = {
            "schema": "agialpha.frontier-search.reproduction.v1",
            "commands_passed": len(records), "command_records": records,
            "deterministic_comparisons": comparisons,
            "native_checks_passed": len(replay["checks"]),
            "recovered_genome_and_plan_agree": True,
            "crypto_bytes_expected_to_change": True,
            "frozen_evidence_overwritten": False,
            "remote_model_sessions_rerun": False,
            "scope": "offline numerical and local-source replay; no physical or human trial, revenue, or runtime release qualification",
        }
    (ROOT / "results/reproduction_receipt.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ["commands_passed", "native_checks_passed", "recovered_genome_and_plan_agree", "frozen_evidence_overwritten"]}))


if __name__ == "__main__":
    main()
