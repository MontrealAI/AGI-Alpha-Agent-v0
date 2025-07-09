# SPDX-License-Identifier: Apache-2.0
"""Agent discovery helpers."""
from __future__ import annotations

import importlib
import inspect
import logging
import os
import pkgutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional

try:  # ≥ Py 3.10 std-lib metadata
    import importlib.metadata as imetadata
except ModuleNotFoundError:  # pragma: no cover
    logging.getLogger(__name__).warning("importlib_metadata backport required on this Python")
    import importlib_metadata as imetadata  # type: ignore

try:  # Google Agent Development Kit
    import adk  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    logging.getLogger(__name__).warning("google-adk not installed – mesh integration disabled")
    adk = None  # type: ignore

from .registry import (
    AGENT_REGISTRY,
    AgentMetadata,
    logger,
    _register,
    _agent_base,
)

_HOT_DIR = Path(os.getenv("AGENT_HOT_DIR", "~/.alpha_agents")).expanduser()
from .plugins import verify_wheel, install_wheel

FAILED_AGENTS: dict[str, str] = {}

# indicates whether discovery has already executed
_DISCOVERY_DONE = False


def _inspect_module(mod: ModuleType) -> Optional[AgentMetadata]:
    """Return metadata for an agent implementation."""
    AgentBase = _agent_base()
    for _, obj in inspect.getmembers(mod, inspect.isclass):
        if issubclass(obj, AgentBase) and obj is not AgentBase:
            return AgentMetadata(
                name=getattr(obj, "NAME", obj.__name__),
                cls=obj,
                version=getattr(obj, "__version__", "0.1.0"),
                capabilities=list(getattr(obj, "CAPABILITIES", [])),
                compliance_tags=list(getattr(obj, "COMPLIANCE_TAGS", [])),
                requires_api_key=getattr(obj, "REQUIRES_API_KEY", False),
            )
    return None


def discover_local() -> None:
    if _DISCOVERY_DONE:
        return
    pkg_root = Path(__file__).parent
    prefix = f"{__name__.rsplit('.', 1)[0]}."
    for _, mod_name, is_pkg in pkgutil.iter_modules([str(pkg_root)]):
        if is_pkg or not mod_name.endswith("_agent"):
            continue
        try:
            fqmn = prefix + mod_name
            mod = sys.modules.get(fqmn)
            if mod is None:
                mod = importlib.import_module(fqmn)
            meta = _inspect_module(mod)
            if meta and meta.name not in AGENT_REGISTRY:
                _register(meta)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Import error for %s", mod_name)
            FAILED_AGENTS[mod_name] = str(exc)


def discover_entrypoints() -> None:
    if _DISCOVERY_DONE:
        return
    try:
        eps = imetadata.entry_points(group="alpha_factory.agents")  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return
    for ep in eps:
        try:
            obj = ep.load()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Entry-point load failed: %s", ep.name)
            FAILED_AGENTS[ep.name] = str(exc)
            continue
        AgentBase = _agent_base()
        if inspect.isclass(obj) and issubclass(obj, AgentBase):
            name = getattr(obj, "NAME", ep.name)
            if name not in AGENT_REGISTRY:
                _register(
                    AgentMetadata(
                        name=name,
                        cls=obj,
                        version=getattr(obj, "__version__", "0.1.0"),
                        capabilities=list(getattr(obj, "CAPABILITIES", [])),
                        compliance_tags=list(getattr(obj, "COMPLIANCE_TAGS", [])),
                        requires_api_key=getattr(obj, "REQUIRES_API_KEY", False),
                    )
                )


def discover_hot_dir() -> None:
    if _DISCOVERY_DONE:
        return
    if not _HOT_DIR.is_dir():
        return
    for wheel in _HOT_DIR.glob("*.whl"):
        if wheel.stem.replace("-", "_") in AGENT_REGISTRY:
            continue
        try:
            if not verify_wheel(wheel):
                continue
            mod = install_wheel(wheel)
            if mod:
                meta = _inspect_module(mod)
                if meta and meta.name not in AGENT_REGISTRY:
                    _register(meta)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Hot-dir load failed for %s", wheel.name)
            FAILED_AGENTS[wheel.stem] = str(exc)


def discover_adk() -> None:
    """Pull remote agent wheels via Google ADK if ``$ADK_MESH`` is set."""
    if _DISCOVERY_DONE:
        return
    if adk is None or not os.getenv("ADK_MESH"):
        return
    try:
        client = adk.Client()
        for pkg in client.list_remote_packages():
            if pkg.name in AGENT_REGISTRY:
                continue
            wheel_path = client.download_package(pkg.name)
            try:
                sig_path = client.download_package(pkg.name + ".sig")
            except Exception:
                sig_path = None
            _HOT_DIR.mkdir(parents=True, exist_ok=True)
            dest = _HOT_DIR / wheel_path.name
            dest.write_bytes(wheel_path.read_bytes())
            if sig_path:
                (dest.with_suffix(dest.suffix + ".sig")).write_bytes(sig_path.read_bytes())
            if not verify_wheel(dest):
                logger.error("Discarding unverified wheel from ADK: %s", pkg.name)
                dest.unlink(missing_ok=True)
                if sig_path:
                    dest.with_suffix(dest.suffix + ".sig").unlink(missing_ok=True)
                continue
            logger.info("Pulled %s from ADK mesh", pkg.name)
        discover_hot_dir()
    except Exception as exc:  # noqa: BLE001
        logger.exception("ADK discovery failed")
        FAILED_AGENTS["adk"] = str(exc)


def run_discovery_once() -> None:
    """Run all discovery functions exactly once."""
    global _DISCOVERY_DONE
    if _DISCOVERY_DONE:
        return
    discover_local()
    discover_entrypoints()
    discover_hot_dir()
    discover_adk()
    _DISCOVERY_DONE = True
