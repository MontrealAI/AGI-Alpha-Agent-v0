# SPDX-License-Identifier: Apache-2.0
"""Environment driven settings used by the agents and interfaces.

The :class:`Settings` dataclass gathers options from ``.env`` files and
environment variables. ``CFG`` is the default instance consumed throughout
the demo.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional, Dict, ClassVar

from alpha_factory_v1.utils.config_common import (
    _load_dotenv,
    _prefetch_vault,
    SettingsConfigDict,
)
from pydantic_settings import BaseSettings

from pydantic import Field


_log = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def init_config(env_file: str = ".env") -> None:
    """Load environment variables and refresh :data:`CFG`."""

    _load_dotenv(env_file)
    _prefetch_vault()
    global CFG
    CFG = Settings()


class Settings(BaseSettings):  # type: ignore[misc]
    """Environment-driven configuration."""

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    offline: bool = Field(default=False, alias="AGI_INSIGHT_OFFLINE")
    bus_port: int = Field(default=6006, alias="AGI_INSIGHT_BUS_PORT")
    ledger_path: str = Field(default="./ledger/audit.db", alias="AGI_INSIGHT_LEDGER_PATH")
    seed: Optional[int] = Field(default=None, alias="AGI_INSIGHT_SEED")
    memory_path: Optional[str] = Field(default=None, alias="AGI_INSIGHT_MEMORY_PATH")
    broker_url: Optional[str] = Field(default=None, alias="AGI_INSIGHT_BROKER_URL")
    bus_token: Optional[str] = Field(default=None, alias="AGI_INSIGHT_BUS_TOKEN")
    bus_cert: Optional[str] = Field(default=None, alias="AGI_INSIGHT_BUS_CERT")
    bus_key: Optional[str] = Field(default=None, alias="AGI_INSIGHT_BUS_KEY")
    bus_fail_limit: int = Field(default=3, alias="AGI_INSIGHT_BUS_FAIL_LIMIT")
    alert_webhook_url: Optional[str] = Field(default=None, alias="ALERT_WEBHOOK_URL")
    allow_insecure: bool = Field(default=False, alias="AGI_INSIGHT_ALLOW_INSECURE")
    broadcast: bool = Field(default=True, alias="AGI_INSIGHT_BROADCAST")
    solana_rpc_url: str = Field(default="https://api.testnet.solana.com", alias="AGI_INSIGHT_SOLANA_URL")
    solana_wallet: Optional[str] = Field(default=None, alias="AGI_INSIGHT_SOLANA_WALLET")
    solana_wallet_file: Optional[str] = Field(default=None, alias="AGI_INSIGHT_SOLANA_WALLET_FILE")
    model_name: str = Field(default="gpt-4o-mini", alias="AGI_MODEL_NAME")
    temperature: float = Field(default=0.2, alias="AGI_TEMPERATURE")
    context_window: int = Field(default=8192, alias="AGI_CONTEXT_WINDOW")
    json_logs: bool = Field(default=False, alias="AGI_INSIGHT_JSON_LOGS")
    db_type: str = Field(default="sqlite", alias="AGI_INSIGHT_DB")
    island_backends: Dict[str, str] = Field(
        default_factory=lambda: {"default": "gpt-4o"},
        alias="AGI_ISLAND_BACKENDS",
    )

    model_config: ClassVar[SettingsConfigDict] = {
        "env_file": ".env",
        "extra": "ignore",
        "populate_by_name": True,
        "env_prefix": "",
    }

    def __init__(self, **data: Any) -> None:  # pragma: no cover - exercised in tests
        super().__init__(**data)
        raw = os.getenv("AGI_ISLAND_BACKENDS")
        if raw and not data.get("island_backends"):
            mapping = {}
            for part in raw.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    mapping[k.strip()] = v.strip()
            if mapping:
                self.island_backends = mapping
        if not self.openai_api_key:
            _log.warning("OPENAI_API_KEY missing – offline mode enabled")
            self.offline = True
        if self.offline:
            self.broadcast = False
        if not self.solana_wallet and self.solana_wallet_file:
            try:
                self.solana_wallet = Path(self.solana_wallet_file).read_text(encoding="utf-8").strip()
            except Exception as exc:  # pragma: no cover - optional
                _log.warning("Failed to load wallet file %s: %s", self.solana_wallet_file, exc)
        if self.bus_cert and self.bus_key:
            if not self.bus_token or self.bus_token == "change_this_token":
                raise ValueError(
                    "AGI_INSIGHT_BUS_TOKEN must be set and cannot be 'change_this_token' when TLS is enabled"
                )


CFG = Settings()
