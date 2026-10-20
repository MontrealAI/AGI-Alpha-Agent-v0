# SPDX-License-Identifier: Apache-2.0
"""The reproduction must identify executed bytes, even if paths change mid-run."""

import hashlib
import json
import runpy
import sys
from pathlib import Path

from alpha_factory_v1.core.runtime.successor.campaign_experiment import CampaignExperiment


def test_input_provenance_binds_bytes_read_before_file_mutation(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    fixtures = root / "examples/transformational-intelligence/policy-study"
    paths = {}
    before = {}
    for name in ("spec", "training", "confirmation"):
        data = (fixtures / (name + ".json")).read_bytes()
        paths[name] = tmp_path / (name + ".json")
        paths[name].write_bytes(data)
        before[name] = hashlib.sha256(data).hexdigest()
    original = CampaignExperiment.train

    def mutate_after_training(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        paths["training"].write_text('{"different-later-file":true}\n')
        return result

    monkeypatch.setattr(CampaignExperiment, "train", mutate_after_training)
    output = tmp_path / "evidence.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "reproduce_transformational_study.py",
            "--spec",
            str(paths["spec"]),
            "--training",
            str(paths["training"]),
            "--confirmation",
            str(paths["confirmation"]),
            "--state",
            str(tmp_path / "journal"),
            "--output",
            str(output),
            "--approve-free-local-study",
        ],
    )
    runpy.run_path(str(root / "scripts/reproduce_transformational_study.py"), run_name="__main__")
    evidence = json.loads(output.read_bytes())
    assert evidence["reproduction"]["input_sha256"] == before
    assert hashlib.sha256(paths["training"].read_bytes()).hexdigest() != before["training"]
    assert evidence["study"]["state"] == "completed"
    assert len(evidence["campaigns"]) == 18
