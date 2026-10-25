"""Engineering negative control: wrong numerical output receives no grant."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness_adapter import run_harness
from harness_probe import check, numerical


def wrong_numerical():
    value = numerical()
    value["artifact_content"]["solution"][0] += 0.1
    return value


if __name__ == "__main__":
    output = Path(sys.argv[1])
    result = run_harness(output, wrong_numerical, check, source_files={"negative_probe": Path(__file__), "engineering_probe": Path(__file__).with_name("harness_probe.py")}, world={"domain": "deliberately wrong 2-by-2 solve"}, policy={"method": "numerical output corruption control"}, protocol={"residual_threshold": "1e-12", "scientific_result": False})
    state = json.loads((output / "native-state.json").read_text())
    assert result["proof"]["outcome"] == "fail"
    assert state["grants"] == {} and state["admissions"] == {} and state["serving_release"] is None
    assert result["handler_counts"]["inspection_handler_calls"] == 0
    print(json.dumps({"proof": "fail", "grants": 0, "admissions": 0, "effect_handler_calls": 0, "residual": result["proof"]["measurements"]["max_residual"]}))
