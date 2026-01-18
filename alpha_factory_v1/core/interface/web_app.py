# SPDX-License-Identifier: Apache-2.0
"""Interactive Streamlit dashboard for running AGI simulations.

The app mirrors the ``cli.py`` options with widgets for the forecast horizon,
growth curve and evolutionary settings. During execution it streams run
progress, renders Plotly charts for the disruption timeline and the MATS
Pareto‑front and exposes download buttons for the collected results.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import time
from typing import Any, TYPE_CHECKING

from pathlib import Path

import pandas as pd
import plotly.express as px
from alpha_factory_v1.core.utils.visual import plot_pareto
from alpha_factory_v1.core.utils.tracing import agent_cycle_seconds, span

try:
    import prometheus_client
except Exception:  # pragma: no cover - optional
    prometheus_client = None

try:  # pragma: no cover - optional dependency
    import streamlit as st
except Exception:  # pragma: no cover - optional
    st = None

__all__ = ["pareto_df", "population_df", "timeline_df", "main"]

if TYPE_CHECKING:  # pragma: no cover - typing only
    ForecastModule = Any
    SectorModule = Any
    MatsModule = Any
else:
    ForecastModule = Any
    SectorModule = Any
    MatsModule = Any

forecast = importlib.import_module("alpha_factory_v1.core.simulation.forecast")
sector = importlib.import_module("alpha_factory_v1.core.simulation.sector")
mats = importlib.import_module("alpha_factory_v1.core.simulation.mats")


def timeline_df(traj: list[Any]) -> pd.DataFrame:
    """Return a DataFrame summarising sector performance."""

    rows = []
    for point in traj:
        for sec in point.sectors:
            rows.append(
                {
                    "year": point.year,
                    "sector": sec.name,
                    "energy": sec.energy,
                    "disrupted": sec.disrupted,
                }
            )
    return pd.DataFrame(rows)


def pareto_df(pop: list[Any]) -> pd.DataFrame:
    """Return a DataFrame for plotting a Pareto front."""

    return pd.DataFrame(
        {"x": [p.genome[0] for p in pop], "y": [p.genome[1] for p in pop], "rank": [p.rank for p in pop]}
    )


def population_df(pop: list[Any]) -> pd.DataFrame:
    """Return a DataFrame for effectiveness vs. risk vs. complexity."""

    return pd.DataFrame(
        {
            "effectiveness": [p.fitness[0] for p in pop],
            "risk": [p.fitness[1] for p in pop],
            "complexity": [p.fitness[2] for p in pop],
            "rank": [p.rank for p in pop],
        }
    )


def _run_simulation(
    horizon: int,
    curve: str,
    num_sectors: int,
    pop_size: int,
    generations: int,
    energy: float,
    entropy: float,
    *,
    save_plots: bool = False,
) -> None:
    """Execute the simulation and update charts live.

    Args:
        horizon: Forecast horizon in years.
        curve: Capability growth curve.
        num_sectors: Number of simulated sectors.
        pop_size: Evolutionary population size.
        generations: Number of evolution steps.
        energy: Initial sector energy.
        entropy: Initial sector entropy.

    Returns:
        None
    """
    if st is None or os.getenv("PYTEST_CURRENT_TEST"):  # pragma: no cover - fallback
        print("Streamlit not installed")
        return

    st.session_state.logs = []
    secs = [sector.Sector(f"s{i:02d}", energy, entropy) for i in range(num_sectors)]
    timeline_placeholder = st.empty()
    pareto_placeholder = st.empty()
    scatter_placeholder = st.empty()
    log_box = st.empty()
    progress = st.progress(0.0)

    start_time = time.perf_counter()
    with span("run_simulation"):
        traj = forecast.forecast_disruptions(
            secs,
            horizon,
            curve,
            pop_size=pop_size,
            generations=generations,
        )

    timeline_rows: list[dict[str, Any]] = []
    total_steps = horizon + generations
    step = 0
    for t in traj:
        step += 1
        affected = [s for s in t.sectors if s.disrupted]
        st.session_state.logs.append(f"Year {t.year}: {len(affected)} affected")
        log_box.text("\n".join(st.session_state.logs[-20:]))
        timeline_rows.extend(
            {
                "year": t.year,
                "sector": s.name,
                "energy": s.energy,
                "disrupted": s.disrupted,
            }
            for s in t.sectors
        )
        df = pd.DataFrame(timeline_rows)
        if not df.empty:
            fig = px.line(
                df,
                x="year",
                y="energy",
                color="sector",
                line_dash=df["disrupted"].map({True: "dash", False: "solid"}),
            )
            timeline_placeholder.plotly_chart(fig, use_container_width=True)
        progress.progress(step / total_steps)
        time.sleep(0.1)

    def eval_fn(genome: list[float]) -> tuple[float, float, float]:
        x, y = genome
        effectiveness = x**2
        risk = y**2
        complexity = (x + y) ** 2
        return effectiveness, risk, complexity

    pop = mats.run_evolution(
        eval_fn,
        2,
        population_size=pop_size,
        generations=generations,
    )
    step = total_steps
    progress.progress(1.0)
    df_pareto = pareto_df(pop)
    fig_p = px.scatter(df_pareto, x="x", y="y", color="rank")
    pareto_placeholder.plotly_chart(fig_p, use_container_width=True)

    df_pop = population_df(pop)
    fig_pop = px.scatter_3d(
        df_pop,
        x="effectiveness",
        y="risk",
        z="complexity",
        color="rank",
    )
    scatter_placeholder.plotly_chart(fig_pop, use_container_width=True)

    if save_plots:
        elites = [ind for ind in pop if ind.rank == 0]
        plot_pareto(elites, Path("pareto.png"))

    st.download_button(
        "Download results (JSON)",
        json.dumps(
            {
                "timeline": timeline_rows,
                "pareto": df_pareto.to_dict(orient="records"),
                "population": df_pop.to_dict(orient="records"),
            }
        ).encode(),
        file_name="results.json",
    )
    csv_bytes = pd.DataFrame(timeline_rows).to_csv(index=False).encode()
    st.download_button("Download timeline (CSV)", csv_bytes, file_name="timeline.csv")
    agent_cycle_seconds.labels("streamlit").observe(time.perf_counter() - start_time)


def main(argv: list[str] | None = None) -> None:  # pragma: no cover - entry point
    """Launch the Streamlit app."""
    if st is None:  # pragma: no cover - fallback
        print("Streamlit not installed")
        return

    parser = argparse.ArgumentParser(description="AGI dashboard")
    parser.add_argument("--save-plots", action="store_true", help="Write pareto.png and pareto.json")
    args, _ = parser.parse_known_args(argv)

    st.title("AGI Simulation Dashboard")
    horizon = st.sidebar.number_input("Forecast horizon", min_value=1, max_value=20, value=5)
    curve = st.sidebar.selectbox("Growth curve", ["logistic", "linear", "exponential"], index=0)
    num_sectors = st.sidebar.number_input("Number of sectors", min_value=1, max_value=20, value=6)
    pop_size = st.sidebar.number_input("Population size", min_value=2, max_value=20, value=6)
    generations = st.sidebar.number_input("Generations", min_value=1, max_value=20, value=3)
    energy = st.sidebar.slider("Initial energy", min_value=0.0, max_value=10.0, value=1.0)
    entropy = st.sidebar.slider("Initial entropy", min_value=0.0, max_value=10.0, value=1.0)
    if st.sidebar.button("Run simulation"):
        _run_simulation(
            horizon,
            curve,
            num_sectors,
            pop_size,
            generations,
            energy,
            entropy,
            save_plots=args.save_plots,
        )
    if st.sidebar.checkbox("Show metrics"):
        if prometheus_client is not None:
            st.code(prometheus_client.generate_latest().decode(), language="text")
        else:
            st.write("prometheus_client not installed")


if __name__ == "__main__":  # pragma: no cover - script entry
    main()
