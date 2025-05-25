"""Minimal Streamlit interface for disruption forecasts."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING, cast

try:  # pragma: no cover - optional dependency
    import streamlit as _st
except Exception:  # pragma: no cover - optional
    _st = None
st: Any | None = cast(Any, _st)

from ..simulation import forecast, sector

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd


def _simulate(horizon: int, curve: str, pop_size: int, generations: int) -> list[Any]:
    """Run the disruption forecast and return the trajectory."""
    secs = [sector.Sector(f"s{i:02d}") for i in range(pop_size)]
    return cast(
        list[Any],
        forecast.forecast_disruptions(
            secs,
            horizon,
            curve,
            pop_size=pop_size,
            generations=generations,
        ),
    )


def _timeline_df(traj: list[Any]) -> "pd.DataFrame":
    """Convert trajectory data into a pandas DataFrame."""
    import pandas as pd

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


def _disruption_df(traj: list[Any]) -> "pd.DataFrame":
    """Return the first disruption year per sector."""
    import pandas as pd

    years: dict[str, int] = {}
    for point in traj:
        for sec in point.sectors:
            if sec.disrupted and sec.name not in years:
                years[sec.name] = point.year
    return pd.DataFrame({"sector": list(years.keys()), "year": list(years.values())})


def main() -> None:  # pragma: no cover - entry point
    """Launch the minimal dashboard or print results."""
    if st is None:
        print("Streamlit not installed")
        traj = _simulate(5, "logistic", 6, 3)
        for record in _disruption_df(traj).to_dict(orient="records"):
            print(f"{record['sector']}: year {record['year']}")
        return

    st.title("Disruption Forecast")
    horizon = st.sidebar.slider("Horizon", 1, 20, 5)
    curve = st.sidebar.selectbox("Curve", ["logistic", "linear", "exponential"], index=0)
    pop_size = st.sidebar.slider("Population size", 2, 20, 6)
    generations = st.sidebar.slider("Generations", 1, 20, 3)

    if st.sidebar.button("Run"):
        traj = _simulate(horizon, curve, pop_size, generations)
        df = _timeline_df(traj)
        pivot = df.pivot(index="year", columns="sector", values="energy")
        st.line_chart(pivot)
        st.table(_disruption_df(traj))


if __name__ == "__main__":  # pragma: no cover - script entry
    main()
