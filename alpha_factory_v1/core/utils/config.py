# SPDX-License-Identifier: Apache-2.0
"""Environment-driven configuration shared across components."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional, cast

import yaml

from alpha_factory_v1.utils.config_common import (
    SettingsBase,
    _load_dotenv,
    _prefetch_vault,
)

from pydantic import BaseModel, Field

_log = logging.getLogger(__name__)


class SelfImprovePrompts(BaseModel):
    """Prompt templates for the self-improvement workflow."""

    system: str = ""
    user: str = ""


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """Return ``name`` from the configured secret backend or environment.

    The backend is selected via ``AGI_INSIGHT_SECRET_BACKEND``. Supported values
    are ``vault``, ``aws`` and ``gcp``. When unset or empty, the environment
    variable ``name`` is returned. Any backend error logs a warning and falls
    back to ``os.getenv(name, default)``.
    """
    backend = os.getenv("AGI_INSIGHT_SECRET_BACKEND", "").lower()
    if not backend or backend == "env":
        return os.getenv(name, default)

    if backend == "vault":
        try:  # pragma: no cover - optional deps
            import importlib

            hvac = importlib.import_module("hvac")

            addr = os.environ["VAULT_ADDR"]
            token = os.environ["VAULT_TOKEN"]
            secret_path = os.getenv(f"{name}_PATH", name)
            client = hvac.Client(url=addr, token=token)
            data = client.secrets.kv.read_secret_version(path=secret_path)
            return cast(Optional[str], data["data"]["data"].get(name, default))
        except Exception as exc:  # noqa: BLE001 - network/auth failures
            _log.warning("Vault secret '%s' failed: %s", name, exc)
            return os.getenv(name, default)

    if backend == "aws":
        try:  # pragma: no cover - optional deps
            import importlib

            boto3 = importlib.import_module("boto3")

            region = os.getenv("AWS_REGION", "us-east-1")
            secret_id = os.getenv(f"{name}_SECRET_ID", name)
            client = boto3.client("secretsmanager", region_name=region)
            resp = client.get_secret_value(SecretId=secret_id)
            return cast(Optional[str], resp.get("SecretString", default))
        except Exception as exc:  # noqa: BLE001 - network/auth failures
            _log.warning("AWS secret '%s' failed: %s", name, exc)
            return os.getenv(name, default)

    if backend == "gcp":
        try:  # pragma: no cover - optional deps
            import importlib

            secretmanager = importlib.import_module("google.cloud.secretmanager")

            project = os.environ["GCP_PROJECT_ID"]
            secret_id = os.getenv(f"{name}_SECRET_ID", name)
            client = secretmanager.SecretManagerServiceClient()
            secret_name = f"projects/{project}/secrets/{secret_id}/versions/latest"
            resp = client.access_secret_version(name=secret_name)
            return cast(str, resp.payload.data.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - network/auth failures
            _log.warning("GCP secret '%s' failed: %s", name, exc)
            return os.getenv(name, default)

    _log.warning("Unknown secret backend '%s'", backend)
    return os.getenv(name, default)


def init_config(env_file: str = ".env") -> None:
    """Load environment variables and refresh :data:`CFG`."""

    _load_dotenv(env_file)
    _prefetch_vault()
    global CFG
    CFG = Settings()


class Settings(SettingsBase):
    """Environment-driven configuration."""

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    offline: bool = Field(default=False, alias="AGI_INSIGHT_OFFLINE")
    bus_port: int = Field(default=6006, alias="AGI_INSIGHT_BUS_PORT")
    ledger_path: str = Field(default="./ledger/audit.db", alias="AGI_INSIGHT_LEDGER_PATH")
    seed: Optional[int] = Field(default=None, alias="SEED")
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
    island_backends: dict[str, str] = Field(
        default_factory=lambda: {"default": "gpt-4o"},
        alias="AGI_ISLAND_BACKENDS",
    )
    self_improve_template: str = Field(
        default=str(Path(__file__).resolve().parents[1] / "prompts" / "self_improve.yaml"),
        alias="SELF_IMPROVE_TEMPLATE",
    )
    self_improve: "SelfImprovePrompts" = Field(default_factory=lambda: SelfImprovePrompts())

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
            self.openai_api_key = get_secret("OPENAI_API_KEY")
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
        try:
            raw = yaml.safe_load(Path(self.self_improve_template).read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            _log.warning("Failed to load self-improve template: %s", exc)
            raw = {}
        self.self_improve = SelfImprovePrompts(**(raw or {}))


CFG = Settings()
