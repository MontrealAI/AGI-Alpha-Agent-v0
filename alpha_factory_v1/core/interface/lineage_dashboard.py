# SPDX-License-Identifier: Apache-2.0
"""Streamlit dashboard visualising archive lineage."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, TYPE_CHECKING

import pandas as pd
import plotly.express as px

from alpha_factory_v1.core.archive import Archive

try:  # pragma: no cover - optional dependency
    import streamlit as _st
    from streamlit_autorefresh import st_autorefresh as _autorefresh
except Exception:  # pragma: no cover - optional
    _st = None
    _autorefresh = None

st: Any | None = _st
st_autorefresh: Any | None = _autorefresh

__all__ = ["load_df", "build_tree", "main"]

if TYPE_CHECKING:  # pragma: no cover - typing only
    from plotly.graph_objs import Figure
else:  # pragma: no cover - typing runtime
    Figure = Any


def load_df(db_path: str | Path) -> pd.DataFrame:
    """Return archive contents as a DataFrame."""
    arch = Archive(db_path)
    rows = []
    for a in arch.all():
        rows.append(
            {
                "id": a.id,
                "parent": a.meta.get("parent"),
                "patch": a.meta.get("diff") or a.meta.get("patch"),
                "score": a.score,
            }
        )
    return pd.DataFrame(rows)


def build_tree(df: pd.DataFrame) -> Figure:
    """Return Plotly treemap figure for lineage."""
    if df.empty:
        return px.treemap()

    ids = df["id"].astype(str)
    parents = df["parent"].fillna("").astype(str)
    fig = px.treemap(
        df,
        ids=ids,
        parents=parents,
        values=[1] * len(df),
        color="score",
        custom_data=[df["patch"].fillna("")],
        color_continuous_scale="Blues",
    )
    labels = [f"<a href='{p}'>{i}</a>" if p else str(i) for i, p in zip(ids, df["patch"].fillna(""))]
    fig.data[0].text = labels
    patches = ", ".join(df["patch"].fillna("").astype(str).tolist())
    fig.data[0].hovertemplate = (
        "score=%{color}<br>patch=%{customdata[0]}<br>"
        f"patches={patches}<extra></extra>"
    )
    fig.data[0].hovertemplate = df["patch"].fillna("").astype(str).tolist()
    return fig


def main(argv: list[str] | None = None) -> None:  # pragma: no cover - entry point
    """Launch the lineage dashboard."""
    if st is None:
        print("Streamlit not installed")
        return

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        default=os.getenv("ARCHIVE_PATH", "archive.db"),
        help="Path to archive database",
    )
    parser.add_argument(
        "--refresh",
        type=int,
        default=int(os.getenv("DASH_REFRESH", "10")),
        help="Auto-refresh interval in seconds",
    )
    args = parser.parse_args(argv)

    st.set_page_config(page_title="Lineage Dashboard", layout="wide")
    if st_autorefresh is not None:
        st_autorefresh(interval=args.refresh * 1000, key="refresh")

    df = load_df(Path(args.db))
    if df.empty:
        st.info("Archive empty")
        return

    fig = build_tree(df)
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":  # pragma: no cover - script entry
    main()
