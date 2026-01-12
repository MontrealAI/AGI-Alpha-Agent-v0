# SPDX-License-Identifier: Apache-2.0
import importlib.metadata as im
import tomllib
import unittest
from pathlib import Path


class TestMatsBridgeEntryPoint(unittest.TestCase):
    """Verify the mats-bridge console script is registered."""

    def test_entry_point_resolves(self) -> None:
        eps = im.entry_points().select(group="console_scripts")
        match = [ep for ep in eps if ep.name == "mats-bridge"]
        expected = "alpha_factory_v1.demos.meta_agentic_tree_search_v0.openai_agents_bridge:main"
        if match:
            self.assertEqual(match[0].value, expected)
            return

        pyproject = Path("pyproject.toml")
        self.assertTrue(pyproject.exists(), "pyproject.toml missing")
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        scripts = (data.get("project") or {}).get("scripts") or {}
        self.assertEqual(scripts.get("mats-bridge"), expected)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
