# SPDX-License-Identifier: Apache-2.0
"""Tests for :mod:`alpha_factory_v1.common.utils.config` helper functions."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import alpha_factory_v1.core.utils.config as cfg

pytestmark = pytest.mark.smoke


def test_load_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = tmp_path / "sample.env"
    env.write_text("FOO=bar\n", encoding="utf-8")
    monkeypatch.delenv("FOO", raising=False)
    cfg._load_dotenv(str(env))
    assert os.environ["FOO"] == "bar"


def test_get_secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_SECRET", "value")
    monkeypatch.delenv("AGI_INSIGHT_SECRET_BACKEND", raising=False)
    assert cfg.get_secret("MY_SECRET") == "value"
    monkeypatch.delenv("MY_SECRET", raising=False)
    assert cfg.get_secret("MY_SECRET", "default") == "default"


def test_settings_secret_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AGI_INSIGHT_SECRET_BACKEND", raising=False)
    monkeypatch.delenv("AGI_INSIGHT_OFFLINE", raising=False)
    cfg.init_config()
    monkeypatch.setattr(cfg, "get_secret", lambda name, default=None: "backend")
    settings = cfg.Settings()
    assert settings.openai_api_key == "backend"
    assert not settings.offline


def test_settings_respects_forced_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "present")
    monkeypatch.setenv("AGI_INSIGHT_OFFLINE", "1")
    cfg.init_config()
    settings = cfg.Settings()
    assert settings.openai_api_key == "present"
    assert settings.offline
