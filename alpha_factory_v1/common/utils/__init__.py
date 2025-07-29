# SPDX-License-Identifier: Apache-2.0
"""Shared utilities used across Alpha-Factory demos.

Submodules provide configuration management, logging helpers, a simple
messaging bus and optional local LLM integration.
"""

# Import the generated protobuf module on package import so other modules
# can reliably reference :mod:`alpha_factory_v1.core.utils.a2a_pb2` without
# stubbing. This prevents tests from injecting a fake module before the
# real one loads.
from importlib import import_module
import contextlib

with contextlib.suppress(Exception):
    import_module("alpha_factory_v1.core.utils.a2a_pb2")
