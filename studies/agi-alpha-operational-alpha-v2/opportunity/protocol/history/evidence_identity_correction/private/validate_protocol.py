# SPDX-License-Identifier: Apache-2.0
"""Scientific negative controls for the acceptance rubric; no participant feedback."""

from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path

from evaluate import PUBLIC, check_packet


def main():
    direct = Path(__file__).resolve().parents[1] / "conventional/direct_method.py"
    spec = importlib.util.spec_from_file_location("direct_reference", direct)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    requests = json.loads((PUBLIC / "requests.json").read_text())
    original = module.build_packet(PUBLIC / "sources", PUBLIC / "requests.json")
    good = check_packet(original, requests, PUBLIC / "sources")
    assert all(x["accepted"] for x in good)
    mutations = [
        ("reject_valid_stationary_use", 0, lambda x: x.update(decision="needs_clock_calibration")),
        ("claim_full_identifiability", 0, lambda x: x.update(full_parameter_identifiability_established=True)),
        (
            "invalid_selected_model_verdict",
            0,
            lambda x: x["dimension_check"].update(selected_model_identifiability="unidentifiable"),
        ),
        ("physical_clock_without_evidence", 1, lambda x: x.update(physical_time_supported=True)),
        (
            "no_transient_counterexample",
            1,
            lambda x: x["state_at_request_time"].__setitem__(1, x["state_at_request_time"][0]),
        ),
        (
            "reversed_calibration_interval",
            2,
            lambda x: x.update(tau_physical_interval=list(reversed(x["tau_physical_interval"]))),
        ),
        ("assumption_called_measurement", 2, lambda x: x.update(calibration_is_observed=True)),
        ("stale_witness_on_new_source", 3, lambda x: x.update(inherited_equilibrium_witness_applicable=True)),
        ("source_identity_reused", 3, lambda x: x.update(source_fingerprint=x["previous_source_fingerprint"])),
        ("simulation_called_observation", 3, lambda x: x.update(contrast_evidence_kind="observed")),
        ("authority_inherited", 3, lambda x: x.update(authority=["execute"])),
    ]
    results = []
    for name, index, change in mutations:
        packet = copy.deepcopy(original)
        change(packet["missions"][index])
        outcome = check_packet(packet, requests, PUBLIC / "sources")
        rejected = not outcome[index]["accepted"]
        assert rejected, name
        results.append({"negative_control": name, "correctly_rejected": rejected})
    output = {
        "positive_missions_passed": len(good),
        "negative_controls": results,
        "negative_controls_rejected": len(results),
        "semantic_prose_review": "Human-readable explanations still require internal reviewer inspection; automated acceptance relies primarily on numerical/source and explicit scope fields.",
        "external_scientific_validation": False,
    }
    (Path(__file__).resolve().parent / "protocol_validation.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"positive_missions": len(good), "negative_controls_rejected": len(results)}))


if __name__ == "__main__":
    main()
