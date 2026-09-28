#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Local Streamlit discovery dashboard and preserved numeric search controls."""
from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "alpha_factory_v1.demos.alpha_agi_insight_v0"

from .discovery import artifacts, evaluate, read_json
from .insight_demo import DEFAULT_SECTORS, parse_sectors, run


def main() -> None:
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError as exc:
        raise SystemExit("Install the dashboard extra with: python -m pip install streamlit") from exc
    if get_script_run_ctx(suppress_warning=True) is None:
        raise SystemExit(
            subprocess.call(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    str(Path(__file__).resolve()),
                    "--server.address",
                    "127.0.0.1",
                    "--server.headless",
                    "true",
                    "--browser.gatherUsageStats",
                    "false",
                ]
            )
        )
    st.set_page_config(page_title="Insight · Discovery Workbench", page_icon="👁️", layout="wide")
    st.title("See the opportunity. Build the evidence.")
    st.caption("α-AGI Insight v0 · local discovery and review planning")
    mode = st.sidebar.radio("Workspace", ["Discovery portfolio", "Original numeric search"])
    if mode == "Original numeric search":
        st.info(
            "The preserved search is a numeric-target illustration. Sector labels do not turn its rewards into forecasts."
        )
        episodes = st.sidebar.number_input("Episodes", 1, 500, 5)
        exploration = st.sidebar.number_input("Exploration", 0.0, 10.0, 1.4)
        target = st.sidebar.number_input("Numeric target", -10000, 10000, 3)
        sectors_text = st.sidebar.text_area("Sectors (comma separated)", ", ".join(DEFAULT_SECTORS))
        seed = st.sidebar.number_input("Seed", 0, 4294967295, 0)
        rewriter = st.sidebar.selectbox("Rewriter", ["random", "openai", "anthropic"])
        model = st.sidebar.text_input("Provider model (only for explicit provider calls)")
        if rewriter != "random":
            st.warning(
                "Run search will make up to 20 external provider calls using this server's configured credentials. No source excerpts are sent."
            )
        if st.button("Run Search"):
            try:
                data = json.loads(
                    run(
                        episodes,
                        exploration,
                        rewriter,
                        target=target,
                        seed=seed,
                        model=model,
                        sectors=parse_sectors(None, sectors_text, allow_files=False, use_env=False),
                        json_output=True,
                    )
                )
                st.subheader(f"Best sector: {data['best']}")
                st.dataframe(
                    [{"sector": name, "mean reward": score} for name, score in data["ranking"]], hide_index=True
                )
                st.download_button(
                    "Download search JSON", json.dumps(data, indent=2), "search.json", "application/json"
                )
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        return
    cases = read_json(Path(__file__).with_name("scenarios.json"))
    chosen = st.selectbox("Start with a case", range(len(cases)), format_func=lambda i: cases[i]["title"])
    scenario = json.loads(json.dumps(cases[chosen]))
    st.info(scenario["note"])
    scenario["policy"]["reviewMinutes"] = st.number_input(
        "Available review minutes", 0, 2400, scenario["policy"]["reviewMinutes"]
    )
    report = evaluate(scenario)
    result = report["result"]
    st.subheader(f"{len(result['selectedIds'])} opportunities proposed for review")
    st.caption(
        f"{result['reviewMinutesUsed']} / {scenario['policy']['reviewMinutes']} minutes reserved. Selection requires independent review."
    )
    st.dataframe(
        [
            {
                "opportunity": row["title"],
                "sector": row["sector"],
                "conservative / 100": row["scores"]["low"] / 1e6,
                "coverage %": row["coverageBps"] / 100,
                "minutes": row["reviewMinutes"],
                "status": row["status"],
            }
            for row in result["ranking"]
        ],
        hide_index=True,
    )
    with st.expander("Inspect full inputs and computations"):
        st.json(report)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in artifacts(report).items():
            archive.writestr(name, data)
    st.download_button("Download review bundle · ZIP", buffer.getvalue(), "insight-review.zip", "application/zip")
    st.caption(result["scope"])


if __name__ == "__main__":
    main()
