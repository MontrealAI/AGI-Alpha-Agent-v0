# SPDX-License-Identifier: Apache-2.0
"""Verify meta-agentic tree visualization highlights the best path."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

import pytest

pw = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


@pytest.mark.skipif(shutil.which("npm") is None, reason="npm not installed")  # type: ignore[misc]
def test_tree_visualization(tmp_path: Path) -> None:
    if os.getenv("SKIP_WEBKIT_TESTS"):
        pytest.skip("WebKit unavailable")
    browser_dir = Path(__file__).resolve().parents[1]
    target = tmp_path / "browser"
    shutil.copytree(browser_dir, target)
    subprocess.check_call(["npm", "run", "build"], cwd=target)

    url = (target / "dist" / "index.html").as_uri()
    tree_path = Path(__file__).resolve().parents[4] / "docs" / "alpha_agi_insight_v1" / "tree.json"
    tree = json.loads(tree_path.read_text())

    def count_nodes(node: Mapping[str, Any]) -> int:
        return 1 + sum(count_nodes(c) for c in node.get("children", []))

    node_count = count_nodes(tree)
    best_path = tree.get("bestPath", [])

    with sync_playwright() as p:
        browser_name = os.getenv("PLAYWRIGHT_BROWSER", "chromium")

        try:
            launcher = getattr(p, browser_name)
        except AttributeError:
            pytest.skip(f"Unsupported browser: {browser_name}")

        browser = launcher.launch()
        context = browser.new_context()
        page = context.new_page()
        page.goto(url)
        page.wait_for_selector("#tree-container")
        page.wait_for_selector("#tree-container .node")

        count_initial = page.eval_on_selector_all("#tree-container .node", "els => els.length")
        page.wait_for_timeout(1000)
        count_later = page.eval_on_selector_all("#tree-container .node", "els => els.length")
        assert count_later > count_initial

        context.route("**", lambda route: route.abort())
        page.wait_for_function(f"document.querySelectorAll('#tree-container .node').length >= {node_count}")
        page.wait_for_timeout(len(best_path) * 800 + 500)
        highlighted = page.evaluate(
            "Array.from(document.querySelectorAll('#tree-container circle[fill='#d62728']'))"
            ".map(n => n.parentNode.querySelector('text').textContent)"
        )
        assert highlighted == best_path
        browser.close()
