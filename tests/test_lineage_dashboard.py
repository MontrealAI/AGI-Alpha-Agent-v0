# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("plotly.express")
from alpha_factory_v1.core.archive import Archive
from alpha_factory_v1.core.interface import lineage_dashboard as ld

go = pytest.importorskip("plotly.graph_objects")


def test_load_df(tmp_path: Path) -> None:
    db = tmp_path / "a.db"
    arch = Archive(db)
    arch.add({"diff": "root.patch"}, 0.5)
    arch.add({"parent": 1, "diff": "child.patch"}, 0.8)
    df = ld.load_df(db)
    assert list(df.columns) == ["id", "parent", "patch", "score"]
    assert len(df) == 2
    assert df.iloc[1]["parent"] == 1


def test_build_tree(tmp_path: Path) -> None:
    db = tmp_path / "a.db"
    arch = Archive(db)
    arch.add({"diff": "root.patch"}, 1.0)
    arch.add({"parent": 1, "diff": "child.patch"}, 0.6)
    df = ld.load_df(db)
    fig = ld.build_tree(df)
    assert isinstance(fig, go.Figure)
    data = fig.data[0]
    assert len(data.ids) == 2
    assert "patch=%{customdata[0]}" in data.hovertemplate
    assert "child.patch" in list(data.customdata[:, 0])


def test_main_no_streamlit(monkeypatch: pytest.MonkeyPatch) -> None:
    mod_name = "alpha_factory_v1.core.interface.lineage_dashboard"
    monkeypatch.setitem(sys.modules, "streamlit", None)
    monkeypatch.setitem(sys.modules, "streamlit_autorefresh", None)
    mod = importlib.reload(importlib.import_module(mod_name))
    mod.main([])
