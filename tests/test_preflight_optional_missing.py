# SPDX-License-Identifier: Apache-2.0
"""Ensure preflight passes when optional dependencies are missing."""

from __future__ import annotations

import os
import unittest
import contextlib
from unittest import mock

from alpha_factory_v1.scripts import preflight


class TestPreflightOptionalMissing(unittest.TestCase):
    def test_missing_optional_packages_ok(self) -> None:
        def fake_check_pkg(name: str) -> bool:
            # Required packages are always present
            if name in {"pytest", "prometheus_client"}:
                return True
            # Simulate all optional deps missing
            if name in preflight.OPTIONAL_DEPS:
                return False
            return True

        patches = [
            mock.patch.object(preflight, "check_python", return_value=True),
            mock.patch.object(preflight, "check_cmd", return_value=True),
            mock.patch.object(preflight, "check_node", return_value=True),
            mock.patch.object(preflight, "check_docker_daemon", return_value=True),
            mock.patch.object(preflight, "check_docker_compose", return_value=True),
            mock.patch.object(preflight, "check_patch_in_sandbox", return_value=True),
            mock.patch.object(preflight, "check_pkg", side_effect=fake_check_pkg),
            mock.patch.object(preflight, "check_openai_agents_version", return_value=True),
            mock.patch.object(preflight, "ensure_dir", return_value=None),
        ]
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}, clear=False):
            with contextlib.ExitStack() as stack:
                for p in patches:
                    stack.enter_context(p)
                # Should not raise SystemExit
                preflight.main(["--offline"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
