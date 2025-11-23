# SPDX-License-Identifier: Apache-2.0
"""Shared utilities and configuration."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable
import logging as _stdlib_logging

from .config import CFG, get_secret

try:
    from .visual import plot_pareto
except Exception:  # pragma: no cover - optional dependency

    def plot_pareto(elites: Iterable[Any], out_path: Path) -> None:
        """Stub when plotly is unavailable."""
        return None


from .file_ops import view, str_replace
from alpha_factory_v1.common.utils import logging

_logger = _stdlib_logging.getLogger(__name__)

try:
    from .snark import (
        aggregate_proof,
        generate_proof,
        publish_proof,
        verify_aggregate_proof,
        verify_proof,
    )
except Exception as exc:  # pragma: no cover - optional zk-SNARK deps
    _logger.warning("Skipping zk-SNARK helpers: %s", exc)
    _missing_snark_exc = exc

    def generate_proof(*_: Any, **__: Any) -> None:
        raise ImportError("zk-SNARK helpers unavailable") from _missing_snark_exc

    def publish_proof(*_: Any, **__: Any) -> None:
        raise ImportError("zk-SNARK helpers unavailable") from _missing_snark_exc

    def verify_proof(*_: Any, **__: Any) -> None:
        raise ImportError("zk-SNARK helpers unavailable") from _missing_snark_exc

    def aggregate_proof(*_: Any, **__: Any) -> None:
        raise ImportError("zk-SNARK helpers unavailable") from _missing_snark_exc

    def verify_aggregate_proof(*_: Any, **__: Any) -> None:
        raise ImportError("zk-SNARK helpers unavailable") from _missing_snark_exc


def _optional_import(module: str) -> Any:
    """Import optional utility modules without breaking minimal environments."""

    try:
        return __import__(f"{__name__}.{module}", fromlist=[module])
    except Exception as exc:  # pragma: no cover - optional deps may be absent
        _logger.warning("Skipping optional utils.%s: %s", module, exc)
        _missing_exc = exc
        return SimpleNamespace(
            __doc__="Optional module unavailable",
            __getattr__=lambda *_: (_ for _ in ()).throw(_missing_exc),
        )


alerts = _optional_import("alerts")
tracing = _optional_import("tracing")

__all__ = [
    "CFG",
    "get_secret",
    "plot_pareto",
    "view",
    "str_replace",
    "generate_proof",
    "publish_proof",
    "verify_proof",
    "aggregate_proof",
    "verify_aggregate_proof",
    "alerts",
    "logging",
    "tracing",
]
