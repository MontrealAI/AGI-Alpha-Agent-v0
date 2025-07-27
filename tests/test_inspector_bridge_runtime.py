# SPDX-License-Identifier: Apache-2.0
"""Runtime tests for the ASI inspector bridge."""

from __future__ import annotations

import importlib
import importlib.util
from packaging.version import Version
import os
import unittest
from unittest.mock import MagicMock, patch

import pytest


# Skip entire module if optional packages are missing
def _has_pkg(name: str, min_version: str | None = None) -> bool:
    try:
        spec = importlib.util.find_spec(name)
    except ValueError:
        return False
    if spec is None:
        return False
    if min_version:
        mod = importlib.import_module(name)
        if Version(getattr(mod, "__version__", "0")) < Version(min_version):
            return False
    return True


if not (_has_pkg("openai_agents", "0.0.17") and _has_pkg("google_adk")):
    pytest.skip("openai_agents>=0.0.17 and google_adk required", allow_module_level=True)


class TestInspectorBridgeRuntime(unittest.TestCase):
    """Verify InspectorAgent registration and ADK launch."""

    def test_main_registers_agent(self) -> None:
        os.environ["ALPHA_FACTORY_ENABLE_ADK"] = "true"
        from alpha_factory_v1.backend import adk_bridge as _adk_bridge

        adk_bridge = importlib.reload(_adk_bridge)

        runtime = MagicMock()
        with (
            patch("openai_agents.AgentRuntime", return_value=runtime) as rt_cls,
            patch.object(adk_bridge, "auto_register") as auto_reg,
            patch.object(adk_bridge, "maybe_launch") as maybe_launch,
        ):
            mod = importlib.reload(
                importlib.import_module("alpha_factory_v1.demos.alpha_asi_world_model.openai_agents_bridge")
            )
            mod.main()

            rt_cls.assert_called_once_with(api_key=None)
            runtime.register.assert_called_once()
            agent_arg = runtime.register.call_args.args[0]
            self.assertIsInstance(agent_arg, mod.InspectorAgent)
            auto_reg.assert_called_once_with([agent_arg])
            maybe_launch.assert_called_once_with()

        os.environ.pop("ALPHA_FACTORY_ENABLE_ADK", None)


if __name__ == "__main__":  # pragma: no cover - manual run
    unittest.main()
