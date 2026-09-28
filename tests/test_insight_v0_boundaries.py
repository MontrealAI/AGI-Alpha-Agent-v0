# SPDX-License-Identifier: Apache-2.0
"""Local-only API, offline launch and independent search accounting tests."""
from collections import defaultdict
import json
import importlib
from pathlib import Path
import random

import pytest
from fastapi.testclient import TestClient

api = importlib.import_module("alpha_factory_v1.demos.alpha_agi_insight_v0.api_server")
from alpha_factory_v1.demos.alpha_agi_insight_v0.insight_demo import load_config, run
from alpha_factory_v1.demos.alpha_agi_insight_v0.discovery import evaluate, read_json


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("API_TOKEN", raising=False)
    if api.app is None:
        importlib.reload(api)
    return TestClient(api.app)


def test_search_observation_accounting_and_rng_isolation():
    random.seed(71)
    state = random.getstate()
    result = json.loads(run(episodes=60, seed=42, json_output=True))
    assert random.getstate() == state
    observations = defaultdict(list)
    for row in result["trace"]:
        observations[row["candidate"]].append(row["reward"])
    assert len(result["trace"]) == 60
    for sector, score in result["ranking"]:
        assert score == pytest.approx(sum(observations[sector]) / len(observations[sector]))
    assert result["trace"][0]["policy"] != result["trace"][1]["policy"]
    assert sum(result["observations"].values()) == 60
    assert json.loads(run(episodes=60, seed=42, json_output=True)) == result


def test_offline_rejects_provider_even_with_credentials(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setenv("NO_LLM", "1")
    with pytest.raises(ValueError, match="Offline"):
        run(rewriter="openai", model="test", offline=False)
    assert json.loads(run(json_output=True))["rewriter"] == "random"


@pytest.mark.parametrize(
    "field,value",
    [
        ("episodes", True),
        ("episodes", 501),
        ("episodes", 0),
        ("exploration", float("nan")),
        ("target", True),
        ("seed", -1),
    ],
)
def test_search_bounds(field, value):
    with pytest.raises(ValueError):
        run(**{field: value})


def test_config_and_output_integrity(tmp_path, monkeypatch):
    path = tmp_path / "settings.yaml"
    path.write_text("episodes: true")
    with pytest.raises(ValueError, match="integer"):
        load_config(path)
    monkeypatch.setattr(
        "alpha_factory_v1.demos.alpha_agi_insight_v0.insight_demo.save_ranking_plot", lambda *args: None
    )
    run(json_output=True, log_dir=tmp_path)
    folder = next(p for p in tmp_path.iterdir() if p.is_dir())
    (folder / "scores.csv").write_text("modified")
    with pytest.raises(ValueError, match="differs"):
        run(json_output=True, log_dir=tmp_path)


def test_api_never_reads_sector_paths(client, tmp_path, monkeypatch):
    path = tmp_path / "private.txt"
    path.write_text("private content must not become a sector")
    monkeypatch.setenv("ALPHA_AGI_SECTORS", str(path))
    response = client.post("/insight", json={"sectors": str(path)})
    assert response.status_code == 200
    assert response.json()["best"] == str(path)
    assert "private content" not in response.text
    assert client.get("/healthz").json()["mode"] == "offline"


@pytest.mark.parametrize(
    "body",
    [
        {"episodes": True},
        {"episodes": "1"},
        {"episodes": 501},
        {"log_dir": "/tmp"},
        {"rewriter": "openai"},
        {"model": "x"},
        {"sectors": []},
    ],
)
def test_api_rejects_unsafe_or_coerced_inputs(client, body):
    assert client.post("/insight", json=body).status_code == 422


def test_api_auth_content_limits_and_busy(client, monkeypatch):
    monkeypatch.setenv("API_TOKEN", "test-token")
    assert client.post("/insight", json={}).status_code == 401
    headers = {"Authorization": "Bearer test-token"}
    assert client.post("/insight", json={}, headers={**headers, "Origin": "https://example.com"}).status_code == 403
    assert client.post("/insight", content="{}", headers=headers).status_code == 415
    headers["Content-Type"] = "application/json"
    for content in ('{"episodes":1,"episodes":2}', '{"exploration":1e999}'):
        assert client.post("/insight", content=content, headers=headers).status_code == 422
    assert client.post("/insight", content=" " * 16001, headers=headers).status_code == 413
    assert api._busy.acquire(blocking=False)
    try:
        response = client.post("/insight", json={}, headers=headers)
        assert response.status_code == 429 and response.headers["retry-after"] == "1"
    finally:
        api._busy.release()
    assert client.post("/insight", json={}, headers=headers).status_code == 200


def test_discovery_api_matches_native(client):
    source = read_json(Path(api.__file__).with_name("scenarios.json"))[0]
    assert client.post("/discovery", json=source).json() == evaluate(source)
    assert client.post("/discovery", json={}).status_code == 422


def test_offline_dashboard_and_zero_data_override_then_restore_environment(monkeypatch):
    final = importlib.import_module("alpha_factory_v1.demos.alpha_agi_insight_v0.official_demo_final")
    zero = importlib.import_module("alpha_factory_v1.demos.alpha_agi_insight_v0.official_demo_zero_data")
    from alpha_factory_v1.demos.alpha_agi_insight_v0.insight_demo import offline_requested

    monkeypatch.delenv("NO_LLM", raising=False)
    monkeypatch.delenv("ALPHA_TEST_OFFLINE", raising=False)
    monkeypatch.setenv("ALPHA_AGI_OFFLINE", "false")
    observed = []
    monkeypatch.setattr(final, "launch_dashboard", lambda: observed.append(offline_requested()))
    final.main(["--offline", "--dashboard", "--no-banner"])
    assert observed == [True]
    assert not offline_requested()
    monkeypatch.setattr(zero, "_run_final", lambda args: observed.append(offline_requested()))
    zero.main([])
    assert observed == [True, True]
    assert not offline_requested()
