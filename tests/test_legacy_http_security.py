# SPDX-License-Identifier: Apache-2.0
"""HTTP boundary regressions without training, providers, or listening sockets."""
from __future__ import annotations

import importlib
from pathlib import Path
import runpy
import sys
import types

from fastapi.testclient import TestClient
from flask import Flask
import pytest


SERVICES = (
    ("alpha_factory_v1.demos.aiga_meta_evolution.agent_aiga_entrypoint", "AIGA_CORS_ORIGINS", "/evolve/1"),
    ("alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo", "ALPHA_ASI_CORS_ORIGINS", "/command"),
)


def load_service(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, setting: str, origins: str):
    monkeypatch.setenv(setting, origins)
    monkeypatch.setenv("NO_LLM", "1")
    monkeypatch.setenv("ENABLE_GRADIO", "false")
    monkeypatch.setenv("ENABLE_AIGA_ADK", "false")
    monkeypatch.setenv("ENABLE_OTEL", "false")
    monkeypatch.setenv("ENABLE_SENTRY", "false")
    monkeypatch.setenv("CHECKPOINT_DIR", str(tmp_path / "checkpoints"))
    monkeypatch.setenv("ALPHA_ASI_DISABLE_AGENT_THREADS", "1")
    for key in ("OPENAI_API_KEY", "AUTH_BEARER_TOKEN", "JWT_PUBLIC_KEY"):
        monkeypatch.delenv(key, raising=False)
    parent_name, leaf = name.rsplit(".", 1)
    parent = importlib.import_module(parent_name)
    monkeypatch.setattr(parent, leaf, None, raising=False)
    if "aiga_meta_evolution" in name:
        evolver = types.ModuleType(parent_name + ".meta_evolver")
        evolver.MetaEvolver = object
        evolver.np = None
        evolver._TORCH = False
        monkeypatch.setattr(parent, "meta_evolver", evolver, raising=False)
        monkeypatch.setitem(sys.modules, evolver.__name__, evolver)
        curriculum = types.ModuleType(parent_name + ".curriculum_env")
        curriculum.CurriculumEnv = None
        monkeypatch.setitem(sys.modules, curriculum.__name__, curriculum)
        utils = types.ModuleType(parent_name + ".utils")
        utils.build_llm = lambda: lambda *_args, **_kwargs: ""
        monkeypatch.setitem(sys.modules, utils.__name__, utils)
    # Register even an initially absent slot so teardown removes the imported stubbed module.
    monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.delitem(sys.modules, name)
    return importlib.import_module(name)


@pytest.mark.parametrize("name,setting,route", SERVICES)
def test_service_import_restores_module_cache(monkeypatch, tmp_path, name, setting, route):
    del route
    parent_name, leaf = name.rsplit(".", 1)
    parent = importlib.import_module(parent_name)
    previous = getattr(parent, leaf, None)
    monkeypatch.delitem(sys.modules, name, raising=False)
    with pytest.MonkeyPatch.context() as isolated:
        module = load_service(isolated, tmp_path, name, setting, "")
        assert sys.modules[name] is module
    assert name not in sys.modules
    assert getattr(parent, leaf, None) is previous


@pytest.mark.parametrize("name,setting,route", SERVICES)
def test_default_cors_refuses_unrelated_mutation_origin(monkeypatch, tmp_path, name, setting, route):
    module = load_service(monkeypatch, tmp_path, name, setting, "")
    # Outside a lifespan context: no evolver, orchestration thread, or provider starts.
    client = TestClient(module.app)
    response = client.options(
        route, headers={"Origin": "https://unrelated.example", "Access-Control-Request-Method": "POST"}
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
    assert client.get("/openapi.json").status_code == 200


@pytest.mark.parametrize("name,setting,route", SERVICES)
def test_explicit_cors_origin_is_exact_and_keeps_routes(monkeypatch, tmp_path, name, setting, route):
    module = load_service(monkeypatch, tmp_path, name, setting, "https://console.example,http://localhost:3000")
    client = TestClient(module.app)
    for origin in ("https://console.example", "http://localhost:3000"):
        response = client.options(route, headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
    rejected = client.options(
        route, headers={"Origin": "https://console.example.evil", "Access-Control-Request-Method": "POST"}
    )
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers


@pytest.mark.parametrize("service_index,route", [(0, "/evolve/1"), (0, "/checkpoint"), (0, "/reset"), (1, "/command")])
@pytest.mark.parametrize("configured", ["", "https://console.example"])
def test_http_mutations_reject_origin_before_handler_and_preserve_allowed_api(
    monkeypatch, tmp_path, service_index, route, configured
):
    name, setting, _ = SERVICES[service_index]
    module = load_service(monkeypatch, tmp_path, name, setting, configured)
    calls = []
    if service_index == 0:
        service = types.SimpleNamespace(
            evolve=lambda gens: calls.append(("evolve", gens)),
            checkpoint=lambda: calls.append(("checkpoint",)),
            reset=lambda: calls.append(("reset",)),
        )
        monkeypatch.setattr(module, "_require_service", lambda **_kwargs: service)
    else:
        monkeypatch.setattr(module.A2ABus, "publish", lambda *args: calls.append(args))
    client = TestClient(module.app)
    rejected = (
        "https://unrelated.example",
        "null",
        "",
        "https://console.example/path",
        "https://console.example.evil",
        "https://user:must-not-log@console.example",
        "https://console.example,https://other.example",
        " https://console.example",
    )
    for origin in rejected:
        response = client.post(route, headers={"Origin": origin}, json={"command": "authored-test"})
        assert response.status_code == 403
        assert "must-not-log" not in response.text
        assert calls == []
    response = client.post(
        route,
        headers=[("Origin", "https://console.example"), ("Origin", "https://unrelated.example")],
        json={"command": "authored-test"},
    )
    assert response.status_code == 403
    assert calls == []
    allowed = ("http://testserver", None) + ((configured,) if configured else ())
    for origin in allowed:
        response = client.post(
            route, headers={"Origin": origin} if origin is not None else {}, json={"command": "authored-test"}
        )
        assert response.status_code == 200
    assert len(calls) == len(allowed)


def test_permitted_origin_does_not_replace_existing_authentication(monkeypatch, tmp_path):
    name, setting, _ = SERVICES[0]
    module = load_service(monkeypatch, tmp_path, name, setting, "https://console.example")
    monkeypatch.setattr(module, "AUTH_TOKEN", "authored-token")
    calls = []
    monkeypatch.setattr(module, "_require_service", lambda **_kwargs: calls.append(True))
    response = TestClient(module.app).post("/evolve/1", headers={"Origin": "https://console.example"})
    assert response.status_code == 401
    assert calls == []


@pytest.mark.parametrize("name,setting,route", SERVICES)
def test_cors_configuration_rejects_wildcards_and_url_smuggling(monkeypatch, tmp_path, name, setting, route):
    del route
    module = load_service(monkeypatch, tmp_path, name, setting, "")
    invalid = (
        "*",
        "https://*.example",
        "http*://console.example",
        "null",
        "file:///tmp/local",
        "//console.example",
        "https://user:must-not-log@console.example",
        "https://console.example/path",
        "https://console.example?",
        "https://console.example#",
        "https://console.example:0",
        "https://console.example:65536",
        "https://console.example:invalid",
        "https://console.example:",
        "https://console.example\\@evil.example",
        "https://console%2eexample",
        "https://console.example\n",
        "https://console.example\r\nOrigin: evil",
        "http://[::1]evil.example",
        "http://prefix[::1]",
        "https://console.example,,https://other.example",
    )
    for origin in invalid:
        with pytest.raises(ValueError) as error:
            module._cors_origins(origin)
        assert "must-not-log" not in str(error.value)
    assert module._cors_origins("http://[::1]:3000") == ["http://[::1]:3000"]
    assert module._cors_origins("https://console.example,https://console.example") == ["https://console.example"]


@pytest.mark.parametrize("name,setting,route", SERVICES)
def test_invalid_cors_configuration_stops_startup(monkeypatch, tmp_path, name, setting, route):
    del route
    with pytest.raises(ValueError, match=setting):
        load_service(monkeypatch, tmp_path, name, setting, "*")


@pytest.mark.parametrize("host", [None, "0.0.0.0", "::1"])
def test_log_ui_loopback_default_and_explicit_bind(monkeypatch, tmp_path, host):
    monkeypatch.setenv("AF_MEMORY_DIR", str(tmp_path / "memory"))
    if host is None:
        monkeypatch.delenv("ALPHA_UI_HOST", raising=False)
    else:
        monkeypatch.setenv("ALPHA_UI_HOST", host)
    calls = []
    monkeypatch.setattr(Flask, "run", lambda self, **kwargs: calls.append(kwargs))
    runpy.run_module("alpha_factory_v1.ui.app", run_name="__main__")
    assert calls == [{"port": 3000, "host": host or "127.0.0.1"}]


@pytest.mark.parametrize(
    "host", ["", "*", "http://127.0.0.1", "user@host", "host:3000", "[::1]", "::1%lo", "host/path", "host\n"]
)
def test_log_ui_refuses_malformed_bind_before_listening(monkeypatch, tmp_path, host):
    monkeypatch.setenv("AF_MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("ALPHA_UI_HOST", host)
    calls = []
    monkeypatch.setattr(Flask, "run", lambda self, **kwargs: calls.append(kwargs))
    with pytest.raises(ValueError, match="ALPHA_UI_HOST"):
        runpy.run_module("alpha_factory_v1.ui.app", run_name="__main__")
    assert calls == []


def test_log_route_still_reads_only_its_configured_test_memory(monkeypatch, tmp_path):
    monkeypatch.setenv("AF_MEMORY_DIR", str(tmp_path / "isolated-memory"))
    name = "alpha_factory_v1.ui.app"
    parent_name, leaf = name.rsplit(".", 1)
    parent = importlib.import_module(parent_name)
    monkeypatch.setattr(parent, leaf, None, raising=False)
    monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.delitem(sys.modules, name)
    module = importlib.import_module(name)
    module.mem.write("authored-test", "boundary", {"value": 1})
    response = module.app.test_client().get("/api/logs?limit=1")
    assert response.status_code == 200
    assert response.json[0]["data"] == {"value": 1}
