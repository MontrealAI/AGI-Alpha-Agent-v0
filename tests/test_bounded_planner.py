# SPDX-License-Identifier: Apache-2.0
"""Independent bounded planner acceptance and input refusal tests."""
import copy
import json
from pathlib import Path

import pytest

from alpha_factory_v1.demos.alpha_super_planner_v1.planner import solve

FIXTURES = Path(__file__).parents[1] / "alpha_factory_v1/demos/alpha_super_planner_v1/fixtures"


def sample():
    return json.loads((FIXTURES / "supplier-plan.json").read_text())


def test_known_optimum_and_no_mutation():
    spec = sample()
    original = copy.deepcopy(spec)
    assert solve(spec) == json.loads((FIXTURES / "supplier-result.json").read_text())
    assert solve(spec)["selected_ids"] == ["collect", "compare", "review"]
    assert solve(spec)["totals"]["value"] == 15
    assert spec == original


@pytest.mark.parametrize(
    "field,value",
    [
        ("budget", True),
        ("budget", 1.0),
        ("budget", -1),
        ("budget", 1000001),
        ("max_risk", 101),
        ("goal", " "),
        ("goal", " x"),
    ],
)
def test_invalid_limits(field, value):
    spec = sample()
    spec[field] = value
    with pytest.raises(ValueError):
        solve(spec)


@pytest.mark.parametrize("deps", [["missing"], ["collect"], ["review"], ["compare", "compare"], [True]])
def test_bad_dependencies(deps):
    spec = sample()
    spec["tasks"][0]["requires"] = deps
    with pytest.raises(ValueError):
        solve(spec)


def test_empty_plan_and_permutation():
    spec = sample()
    result = solve(spec)
    spec["tasks"].reverse()
    assert solve(spec) == result
    spec["budget"] = 0
    assert solve(spec)["selected_ids"] == []
    assert solve(spec)["feasible_subsets"] == 1


def test_tie_break_and_topological_order():
    spec = sample()
    spec["tasks"] = [dict(id=n, label=n, cost=1, effort=1, value=1, risk=0, requires=[]) for n in ("z", "a")]
    spec["budget"] = 1
    assert solve(spec)["selected_ids"] == ["a"]
    spec["tasks"][1]["requires"] = ["z"]
    spec["budget"] = 2
    assert solve(spec)["steps"] == ["z", "a"]


def test_full_boundary():
    spec = sample()
    spec["tasks"] = [
        dict(id="t" + str(i), label="Task", cost=0, effort=0, value=1, risk=0, requires=[]) for i in range(16)
    ]
    result = solve(spec)
    assert result["feasible_subsets"] == 65536
    assert result["totals"]["value"] == 16
    spec["tasks"].append(dict(spec["tasks"][0]))
    with pytest.raises(ValueError):
        solve(spec)


def test_cli_invalid_json_and_size(tmp_path):
    import subprocess
    import sys

    for raw in ('{"schema":1,"schema":2}', "x" * 65537, "{"):
        path = tmp_path / "input.json"
        path.write_text(raw)
        result = subprocess.run(
            [sys.executable, "-m", "alpha_factory_v1.demos.alpha_super_planner_v1", "--input", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 2
        assert not result.stdout


def test_cli_valid_fixture():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "alpha_factory_v1.demos.alpha_super_planner_v1"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert json.loads(result.stdout) == solve(sample())
