# SPDX-License-Identifier: Apache-2.0
import importlib
import os
import sys
from pathlib import Path
import subprocess
import contextlib

import numpy as np  # ensure numpy optional dependency is present
import pytest

MODULE = "alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo"


def _reload_module(monkeypatch):
    # Keep optional-runtime stubs local to this import. A module object retains
    # its fake torch references after the scope closes, while later training
    # tests recover the real cached module and package attribute.
    parent_name, _, child = MODULE.rpartition(".")
    parent = importlib.import_module(parent_name)
    with monkeypatch.context() as scoped:
        scoped.setitem(sys.modules, MODULE, None)
        sys.modules.pop(MODULE)
        scoped.setattr(parent, child, None, raising=False)
        import types

        fake = types.ModuleType("torch")
        fake.__path__ = []  # mark as package
        fake.manual_seed = lambda *_a, **_k: None
        fake.cuda = types.SimpleNamespace(is_available=lambda: False)
        fake.tensor = lambda *a, **k: None
        fake.float32 = "float32"
        fake.no_grad = contextlib.nullcontext
        fake.tanh = lambda x: x
        fake.cat = lambda xs, dim=None: None
        nn_mod = types.ModuleType("torch.nn")
        nn_mod.Module = object
        nn_mod.Linear = lambda *a, **k: object()
        f_mod = types.ModuleType("torch.nn.functional")
        f_mod.one_hot = lambda x, num_classes: x
        f_mod.mse_loss = lambda a, b: 0.0
        f_mod.log_softmax = lambda x, dim=-1: x
        nn_mod.functional = f_mod
        optim_mod = types.ModuleType("torch.optim")
        optim_mod.Adam = lambda params, lr: object()
        fake.nn = nn_mod
        fake.optim = optim_mod
        scoped.setitem(sys.modules, "torch", fake)
        scoped.setitem(sys.modules, "torch.nn", nn_mod)
        scoped.setitem(sys.modules, "torch.nn.functional", f_mod)
        scoped.setitem(sys.modules, "torch.optim", optim_mod)
        return importlib.import_module(MODULE)


def test_safety_agent_halts_on_nan(monkeypatch):
    monkeypatch.setenv("NO_LLM", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALPHA_ASI_SILENT", "1")
    monkeypatch.setenv("ALPHA_ASI_MAX_STEPS", "1")
    mod = _reload_module(monkeypatch)
    mod.A2ABus._subs = {}
    safety = mod.BasicSafetyAgent()
    msgs: list[dict] = []
    mod.A2ABus.subscribe("orch", lambda m: msgs.append(m))
    safety.handle({"loss": np.nan})
    assert {"cmd": "stop"} in msgs
    safety.close()


def test_safety_agent_halts_on_large_loss(monkeypatch):
    monkeypatch.setenv("NO_LLM", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ALPHA_ASI_SILENT", "1")
    monkeypatch.setenv("ALPHA_ASI_MAX_STEPS", "1")
    mod = _reload_module(monkeypatch)
    mod.A2ABus._subs = {}
    safety = mod.BasicSafetyAgent()
    msgs: list[dict] = []
    mod.A2ABus.subscribe("orch", lambda m: msgs.append(m))
    safety.handle({"loss": 5000.0})
    assert {"cmd": "stop"} in msgs
    safety.close()


def test_llm_planner_activates_with_key(monkeypatch):
    pytest.importorskip("openai")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.delenv("NO_LLM", raising=False)
    monkeypatch.setenv("ALPHA_ASI_SILENT", "1")
    monkeypatch.setenv("ALPHA_ASI_MAX_STEPS", "1")
    mod = _reload_module(monkeypatch)
    assert "llm_planner" in mod.A2ABus._subs


def test_real_safety_agent_loaded(monkeypatch) -> None:
    monkeypatch.setenv("NO_LLM", "1")
    monkeypatch.setenv("ALPHA_ASI_SILENT", "1")
    monkeypatch.setenv("ALPHA_ASI_MAX_STEPS", "1")

    mod = _reload_module(monkeypatch)

    assert "safety" in mod.AGENTS
    assert list(mod.AGENTS).count("safety") == 1
    subs = mod.A2ABus._subs.get("safety") or []
    assert len(subs) == 1


@pytest.mark.parametrize("preloaded", [False, True])
def test_stubbed_runtime_restores_import_cache(monkeypatch, preloaded):
    package_name, _, attribute = MODULE.rpartition(".")
    package = importlib.import_module(package_name)
    if not preloaded:
        monkeypatch.delitem(sys.modules, MODULE, raising=False)
        monkeypatch.delattr(package, attribute, raising=False)
    previous = sys.modules.get(MODULE)
    previous_attribute = getattr(package, attribute, None)
    previous_torch = sys.modules.get("torch")
    module = _reload_module(monkeypatch)
    try:
        assert module.torch is not previous_torch
        assert sys.modules.get(MODULE) is previous
        assert getattr(package, attribute, None) is previous_attribute
        assert sys.modules.get("torch") is previous_torch
    finally:
        for agent in module.AGENTS.values():
            agent.close()


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _run_deploy_script(tmp_path: Path, env_vars: dict[str, str]) -> str:
    script = Path("alpha_factory_v1/demos/alpha_asi_world_model/deploy_alpha_asi_world_model_demo.sh")
    assert script.exists(), script
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture = tmp_path / "env.txt"
    _write_executable(
        bin_dir / "python",
        '#!/usr/bin/env bash\nprintenv > "$CAPTURE"\n',
    )
    env = os.environ.copy()
    if "OPENAI_API_KEY" not in env_vars:
        env.pop("OPENAI_API_KEY", None)
    env.update(env_vars)
    env.update({"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}", "CAPTURE": str(capture)})
    subprocess.run(["bash", str(script)], env=env, check=True, timeout=5)
    return capture.read_text()


def test_deploy_script_sets_no_llm(tmp_path: Path) -> None:
    out = _run_deploy_script(tmp_path, {})
    assert "NO_LLM=1" in out


def test_deploy_script_preserves_api_key(tmp_path: Path) -> None:
    out = _run_deploy_script(tmp_path, {"OPENAI_API_KEY": "x"})
    assert "NO_LLM" not in out
