# SPDX-License-Identifier: Apache-2.0
"""Shared configuration helpers."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from alpha_factory_v1.utils.env import _load_env_file
from typing import Any, ClassVar, Dict, TYPE_CHECKING, Protocol


class _TypedBaseSettings(Protocol):
    def model_dump(self) -> Dict[str, Any]:
        ...


if TYPE_CHECKING:
    BaseSettings = _TypedBaseSettings
    SettingsConfigDict = Dict[str, Any]
else:  # pragma: no cover - runtime import
    try:
        from pydantic_settings import BaseSettings, SettingsConfigDict
    except Exception:
        from pydantic import BaseSettings

        SettingsConfigDict = Dict[str, Any]

_log = logging.getLogger(__name__)


def _load_dotenv(path: str = ".env") -> None:
    """Load default variables from ``path`` when available."""
    if Path(path).is_file():
        for k, v in _load_env_file(path).items():
            os.environ[k] = v


def _prefetch_vault() -> None:
    """Populate environment secrets from HashiCorp Vault if configured."""
    if "VAULT_ADDR" in os.environ:
        try:  # pragma: no cover - optional dependency
            import importlib

            hvac = importlib.import_module("hvac")

            addr = os.environ["VAULT_ADDR"]
            token = os.getenv("VAULT_TOKEN")
            secret_path = os.getenv("OPENAI_API_KEY_PATH", "OPENAI_API_KEY")
            client = hvac.Client(url=addr, token=token)
            data = client.secrets.kv.read_secret_version(path=secret_path)
            value = data["data"]["data"].get("OPENAI_API_KEY")
            if value:
                os.environ["OPENAI_API_KEY"] = value
        except Exception as exc:  # noqa: BLE001
            _log.warning("Vault lookup failed: %s", exc)


class SettingsBase(BaseSettings):
    """Base settings with shared behavior."""

    model_config: ClassVar[SettingsConfigDict] = {
        "env_file": ".env",
        "extra": "ignore",
        "populate_by_name": True,
        "env_prefix": "",
    }

    def __repr__(self) -> str:  # pragma: no cover - trivial
        data = self.model_dump()
        for k in tuple(data):
            if any(s in k.lower() for s in ("token", "key", "password")) and data[k]:
                data[k] = "***"
        return f"{self.__class__.__name__}({data})"
