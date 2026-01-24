# SPDX-License-Identifier: Apache-2.0
import logging
from unittest import mock

from alpha_factory_v1.common.utils import local_llm


def test_load_model_warning(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)
    monkeypatch.delenv("NO_LLM", raising=False)
    monkeypatch.setattr(local_llm, "_MODEL", None)
    monkeypatch.setattr(local_llm, "_CALL", None)
    monkeypatch.setattr(local_llm, "Llama", mock.Mock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(local_llm, "AutoModelForCausalLM", None)

    local_llm._load_model(local_llm.config.CFG)

    assert any("boom" in r.message for r in caplog.records)


def test_chat_exception_logs_error(monkeypatch, caplog):
    caplog.set_level(logging.ERROR)
    monkeypatch.setattr(local_llm, "_CALL", lambda _p, _c: (_ for _ in ()).throw(RuntimeError("boom")))

    out = local_llm.chat("hello", local_llm.config.CFG)

    assert out == "[offline] hello"
    assert any("boom" in r.getMessage() for r in caplog.records)
