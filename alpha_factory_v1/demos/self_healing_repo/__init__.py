# SPDX-License-Identifier: Apache-2.0
"""Self-healing demo package."""

from importlib import import_module

# Expose patching utilities at package level
patcher_core = import_module(".patcher_core", __name__)

__all__ = ["patcher_core"]
