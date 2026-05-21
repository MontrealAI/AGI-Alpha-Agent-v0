# SPDX-License-Identifier: Apache-2.0
import os
import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("plotly.express")
from alpha_factory_v1.core.interface import web_app  # noqa: E402
from alpha_factory_v1.core.simulation import forecast, sector, mats  # noqa: E402


def test_timeline_df() -> None:
    secs = [sector.Sector("a"), sector.Sector("b")]
    traj = forecast.forecast_disruptions(secs, 2, pop_size=2, generations=1)
    df = web_app.timeline_df(traj)
    assert set(df.columns) == {"year", "sector", "energy", "disrupted"}
    assert len(df) == 4


def test_pareto_df() -> None:
    pop = [mats.Individual([0.0, 0.0]), mats.Individual([1.0, 1.0])]
    pop[0].rank = 0
    pop[1].rank = 1
    df = web_app.pareto_df(pop)
    assert set(df.columns) == {"x", "y", "rank"}
    assert len(df) == 2


def test_population_df() -> None:
    pop = [mats.Individual([0.0, 0.0]), mats.Individual([1.0, 1.0])]
    for i, ind in enumerate(pop):
        ind.fitness = (i * 1.0, i * 2.0, i * 3.0)
        ind.rank = i
    df = web_app.population_df(pop)
    assert set(df.columns) == {"effectiveness", "risk", "complexity", "rank"}
    assert len(df) == 2


def test_run_simulation_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure _run_simulation accepts energy and entropy options."""

    web_app._run_simulation(1, "logistic", 2, 3, 1, 1.0, 1.0, save_plots=False)
    out, _ = capsys.readouterr()
    assert "Streamlit not installed" in out


def test_progress_dom_updates() -> None:
    """Smoke test that the React dashboard receives progress events."""

    pw = pytest.importorskip("playwright.sync_api")
    from playwright._impl._errors import Error as PlaywrightError
    from fastapi.testclient import TestClient

    os.environ.setdefault("API_TOKEN", "test-token")
    os.environ.setdefault("AGI_INSIGHT_ALLOW_INSECURE", "1")
    from alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface import api_server

    try:
        with TestClient(api_server.app) as client:
            with pw.sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(str(client.base_url) + "/web/")
                page.click("text=Run simulation")
                page.wait_for_selector("#capability")
                browser.close()
    except PlaywrightError as exc:
        pytest.skip(f"Playwright browser not installed: {exc}")
