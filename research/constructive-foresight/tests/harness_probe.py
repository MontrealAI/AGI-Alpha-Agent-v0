"""Engineering fixture only: actual small solve, independent residual, native guards."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness_adapter import run_harness


def numerical():
    matrix = np.array([[4., 1.], [1., 3.]])
    rhs = np.array([1., 2.])
    solution = np.linalg.solve(matrix, rhs)
    return {"artifact_content": {"matrix": matrix.tolist(), "rhs": rhs.tolist(), "solution": solution.tolist()}, "evidence_class": "engineering fixture; excluded from scientific results"}


def check(record):
    raw = Path(record["artifact_path"]).read_bytes()
    artifact = json.loads(raw)
    residual = max(abs(sum(float(a)*float(x) for a,x in zip(row,artifact["solution"]))-float(b)) for row,b in zip(artifact["matrix"],artifact["rhs"]))
    return {"artifact_sha256": hashlib.sha256(raw).hexdigest(), "accepted": residual <= 1e-12, "max_residual": repr(residual), "threshold": "1e-12", "method": "Direct independently implemented row residual"}


if __name__ == "__main__":
    result = run_harness(Path(sys.argv[1]), numerical, check, source_files={"engineering_probe": Path(__file__)}, world={"domain": "2-by-2 positive-definite linear system"}, policy={"method": "numpy.linalg.solve"}, protocol={"residual_threshold": "1e-12", "scientific_result": False})
    assert result["handler_counts"] == {"numeric_handler_calls": 1, "checker_calls": 1, "inspection_handler_calls": 1}
    assert {x["name"] for x in result["controls"]} == {"missing-authority", "stale-authority", "stale-proof", "successor-without-fresh-proof"}
    assert all(x["rejected"] and x["handler_counts_unchanged"] for x in result["controls"])
    print(json.dumps({"proof": result["proof"]["outcome"], "controls": result["controls"], "journal_valid": result["journal"]["valid"], "api_token_created": result["fixture"]["api_token_created"], "artifact": result["phases"]["formation"]["artifact_path"]}))
