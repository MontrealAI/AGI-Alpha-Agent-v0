# SPDX-License-Identifier: Apache-2.0
"""Independent optimization oracle, evidence integrity and bounded input tests."""
from copy import deepcopy
import itertools
import json
from pathlib import Path
import random

import pytest

from alpha_factory_v1.demos.alpha_agi_insight_v0 import discovery as d
from alpha_factory_v1.demos.alpha_agi_insight_v0.discovery_cli import main

CASES = d.read_json(Path(d.__file__).with_name("scenarios.json"))


def oracle(source):
    candidates = []
    for item in source["opportunities"]:
        weights = source["weights"]
        low = sum(weights[m] * item["signals"][m]["low"] for m in weights)
        covered = sum(weights[m] for m in weights if item["signals"][m]["source"])
        if low >= source["policy"]["minScoreBps"] * 10000 and covered >= source["policy"]["minCoverageBps"]:
            candidates.append((item["id"], low, item["reviewMinutes"]))
    options = []
    for mask in itertools.product((0, 1), repeat=len(candidates)):
        subset = [item for item, take in zip(candidates, mask) if take]
        cost = sum(item[2] for item in subset)
        if cost <= source["policy"]["reviewMinutes"]:
            options.append((-sum(item[1] for item in subset), cost, tuple(sorted(item[0] for item in subset))))
    return min(options)


def test_exact_portfolio_against_exhaustive_oracle():
    rng = random.Random(761)
    for index in range(90):
        source = deepcopy(CASES[index % len(CASES)])
        source["policy"]["reviewMinutes"] = rng.randrange(200)
        for item in source["opportunities"]:
            item["reviewMinutes"] = rng.randrange(1, 60)
            for signal in item["signals"].values():
                signal.update(dict(zip(("low", "base", "high"), sorted(rng.randrange(10001) for _ in range(3)))))
        report = d.evaluate(source)
        result = report["result"]
        assert (-result["objectiveNumerator"], result["reviewMinutesUsed"], tuple(result["selectedIds"])) == oracle(
            source
        )
        assert d.verify(report) == report


def test_ties_and_zero_scores():
    source = deepcopy(CASES[0])
    source["policy"].update(reviewMinutes=20, minScoreBps=0, minCoverageBps=0)
    for item in source["opportunities"]:
        item["reviewMinutes"] = 20
        for signal in item["signals"].values():
            signal.update(low=100, base=100, high=100)
    assert d.evaluate(source)["result"]["selectedIds"] == [min(item["id"] for item in source["opportunities"])]
    for item in source["opportunities"]:
        for signal in item["signals"].values():
            signal.update(low=0)
    assert d.evaluate(source)["result"]["selectedIds"] == []


@pytest.mark.parametrize(
    "data",
    [
        b'{"x":1,"x":2}',
        b'{"x":NaN}',
        b'{"x":1e999}',
        b'"\\ud800"',
        b"\xff",
        b"[" * 26 + b"0" + b"]" * 26,
        b" " * (d.MAX_BYTES + 1),
    ],
)
def test_reject_ambiguous_json(data):
    with pytest.raises(ValueError):
        d.parse(data)


@pytest.mark.parametrize(
    "path,value",
    [
        (("policy", "reviewMinutes"), True),
        (("policy", "minScoreBps"), -1),
        (("policy", "jobBountyTokens"), 0),
        (("weights", "demand"), 3001),
        (("title",), "🌌" * 41),
        (("sources", 0, "url"), "https://user:pass@example.com"),
        (("sources", 0, "url"), "javascript:alert(1)"),
        (("sources", 0, "url"), "https://example.com\\evil"),
        (("opportunities", 0, "signals", "demand", "low"), 10001),
        (("opportunities", 0, "signals", "demand", "source"), "absent"),
    ],
)
def test_input_bounds(path, value):
    source = deepcopy(CASES[0])
    target = source
    for field in path[:-1]:
        target = target[field]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        d.evaluate(source)


def test_rehashed_forgery_and_source_binding():
    report = d.evaluate(CASES[0])
    forged = deepcopy(report)
    forged["result"]["selectedIds"] = []
    forged["sha256"] = d.digest({k: v for k, v in forged.items() if k != "sha256"})
    with pytest.raises(ValueError, match="recomputation"):
        d.verify(forged)
    source = deepcopy(CASES[0])
    source["sources"][0]["excerpt"] += " Changed assumption."
    changed = d.evaluate(source)
    assert report["sha256"] != changed["sha256"]
    assert report["result"]["jobs"] != changed["result"]["jobs"]
    for draft in report["result"]["novaSeedDrafts"]:
        assert draft["sha256"] == d.digest({k: v for k, v in draft.items() if k != "sha256"})


def test_maximum_dossier_roundtrip():
    source = deepcopy(CASES[0])
    source["policy"].update(reviewMinutes=2400, minScoreBps=0, minCoverageBps=0, jobBountyTokens=1000000)
    source["sources"] = [
        dict(
            source["sources"][0],
            id=f"source-{i}",
            excerpt="x" * 1200,
            title="x" * 160,
            url="https://example.com/" + "x" * 480,
        )
        for i in range(32)
    ]
    source["opportunities"] = [
        dict(
            deepcopy(source["opportunities"][0]),
            id=f"opportunity-{i}",
            title="x" * 160,
            thesis="x" * 500,
            goal="x" * 240,
            successMetric="x" * 400,
            reviewMinutes=1,
        )
        for i in range(24)
    ]
    for item in source["opportunities"]:
        for i, signal in enumerate(item["signals"].values()):
            signal["source"] = f"source-{i}"
    report = d.evaluate(source)
    encoded = d.canonical(report)
    assert len(encoded) < d.MAX_BYTES
    assert d.verify(d.parse(encoded)) == report


def test_bundle_reuse_corruption_and_cli(tmp_path, capsys):
    assert main(["--case", "public-software", "--output", str(tmp_path), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    folder = d.write_bundle(report, tmp_path)
    assert len(list(folder.iterdir())) == 6
    assert main(["--verify", str(folder / "dossier.json")]) == 0
    (folder / "jobs.json").write_text("[]")
    with pytest.raises(ValueError, match="differs"):
        d.write_bundle(report, tmp_path)
    assert main(["--case", "absent"]) == 2


def test_original_research_preserved():
    root = Path(__file__).resolve().parents[1]
    archive = root / "alpha_factory_v1/demos/alpha_agi_insight_v0/RESEARCH_ARCHIVE.md"
    assert "```mermaid" in archive.read_text()
    assert (root / "scripts/templates/discovery-original.html").read_bytes() == (
        root / "docs/alpha_agi_insight_v0/research.html"
    ).read_bytes()


def test_notebook_executes_from_explicit_offline_source(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("ALPHA_INSIGHT_SOURCE", str(root))
    monkeypatch.chdir(tmp_path)
    notebook = json.loads(
        (root / "alpha_factory_v1/demos/alpha_agi_insight_v0/colab_alpha_agi_insight_demo.ipynb").read_text()
    )
    namespace = {}
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            exec(compile("".join(cell["source"]), "insight-notebook", "exec"), namespace)
    assert len(namespace["reports"]) == 5
    assert namespace["archive"].is_file()


def test_integral_json_normalization_and_unicode_blanks():
    report = d.evaluate(CASES[0])
    alternate = deepcopy(report)
    alternate["input"]["policy"]["reviewMinutes"] = 60.0
    alternate["result"]["reviewMinutesUsed"] = float(report["result"]["reviewMinutesUsed"])
    assert d.verify(alternate) == report
    source = deepcopy(CASES[0])
    source["title"] = "\ufeff"
    with pytest.raises(ValueError):
        d.evaluate(source)
