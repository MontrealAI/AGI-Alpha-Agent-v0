# SPDX-License-Identifier: Apache-2.0
"""Helper to import the project when not installed."""

from importlib.util import find_spec
from pathlib import Path
import sys

# Allow tests to run from the repository without installing the package
if find_spec("alpha_factory_v1") is None:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.append(str(ROOT))

STUBS = Path(__file__).resolve().parents[1] / "stubs"
if STUBS.is_dir():
    if find_spec("openai_agents") is None:
        sys.path.append(str(STUBS))
    import importlib

    try:
        adk_spec = find_spec("google_adk") or find_spec("google.adk")
    except ModuleNotFoundError:
        adk_spec = None
    if adk_spec is None:
        pass
    else:
        module = importlib.import_module(adk_spec.name)
        if adk_spec.name == "google.adk" and find_spec("google_adk") is None:
            sys.modules.setdefault("google_adk", module)
    if adk_spec is None or not hasattr(importlib.import_module(adk_spec.name), "task"):
        sys.path.insert(0, str(STUBS))
        importlib.invalidate_caches()
        stub = importlib.import_module("google_adk")
        sys.modules.setdefault("google.adk", stub)
