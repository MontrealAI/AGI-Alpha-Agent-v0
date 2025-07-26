# SPDX-License-Identifier: Apache-2.0
"""Configuration parsing tests for alpha_asi_world_model_demo."""

from __future__ import annotations

import importlib
import sys

import pytest

pytest.importorskip("torch")


def test_bool_env_override(monkeypatch, non_network: None) -> None:
    """ALPHA_ASI_LOG_JSON=false should disable JSON logging."""
    monkeypatch.setenv("ALPHA_ASI_LOG_JSON", "false")
    monkeypatch.setenv("NO_LLM", "1")
    monkeypatch.setenv("ALPHA_ASI_SILENT", "1")
    monkeypatch.setenv("ALPHA_ASI_MAX_STEPS", "1")

    module = "alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo"
    if module in sys.modules:
        del sys.modules[module]
    mod = importlib.import_module(module)
    assert mod.CFG.log_json is False


def test_host_port_override(monkeypatch, non_network: None) -> None:
    """ALPHA_ASI_HOST and ALPHA_ASI_PORT should override defaults."""
    monkeypatch.setenv("ALPHA_ASI_HOST", "8.8.8.8")
    monkeypatch.setenv("ALPHA_ASI_PORT", "12345")
    monkeypatch.setenv("NO_LLM", "1")
    monkeypatch.setenv("ALPHA_ASI_SILENT", "1")
    monkeypatch.setenv("ALPHA_ASI_MAX_STEPS", "1")

    module = "alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo"
    if module in sys.modules:
        del sys.modules[module]
    mod = importlib.import_module(module)
    assert mod.CFG.host == "8.8.8.8"
    assert mod.CFG.port == 12345


def test_auto_device_from_config(monkeypatch, tmp_path, non_network: None) -> None:
    """ "device: auto" should resolve to cuda when available."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text("general:\n  device: auto\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NO_LLM", "1")
    monkeypatch.setenv("ALPHA_ASI_SILENT", "1")
    monkeypatch.setenv("ALPHA_ASI_MAX_STEPS", "1")

    module = "alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo"
    if module in sys.modules:
        del sys.modules[module]
    mod = importlib.import_module(module)

    import torch

    expected = "cuda" if torch.cuda.is_available() else "cpu"
    assert mod.CFG.device == expected


def test_config_seed_changes_env(monkeypatch, tmp_path, non_network: None) -> None:
    """`general.seed` should control RNG seeding."""

    module = "alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo"

    def load_env(seed: int):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(f"general:\n  seed: {seed}\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NO_LLM", "1")
        monkeypatch.setenv("ALPHA_ASI_SILENT", "1")
        monkeypatch.setenv("ALPHA_ASI_MAX_STEPS", "1")
        if module in sys.modules:
            del sys.modules[module]
        mod = importlib.import_module(module)
        env = mod.Orchestrator().envs[0]
        return env.size, sorted(env.obstacles)

    first = load_env(123)
    second_same = load_env(123)
    different = load_env(456)

    assert first == second_same
    assert first != different


def test_extended_cfg_fields(monkeypatch, tmp_path, non_network: None) -> None:
    """Values from config.yaml should populate the Config dataclass."""

    cfg = tmp_path / "config.yaml"
    cfg.write_text("training:\n" "  env_batch: 3\n" "  hidden: 64\n" "  mcts_simulations: 8\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NO_LLM", "1")
    monkeypatch.setenv("ALPHA_ASI_SILENT", "1")
    monkeypatch.setenv("ALPHA_ASI_MAX_STEPS", "1")

    module = "alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo"
    if module in sys.modules:
        del sys.modules[module]
    mod = importlib.import_module(module)

    assert mod.CFG.env_batch == 3
    assert mod.CFG.hidden == 64
    assert mod.CFG.mcts_simulations == 8
