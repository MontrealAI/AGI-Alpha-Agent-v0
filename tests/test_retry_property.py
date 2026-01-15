# SPDX-License-Identifier: Apache-2.0
import asyncio
import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import HealthCheck, given, strategies as st, settings, assume  # noqa: E402

from alpha_factory_v1.common.utils import retry  # noqa: E402


@settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(failures=st.integers(min_value=0, max_value=4), max_tries=st.integers(min_value=1, max_value=5))
def test_with_retry_sync_property(monkeypatch: pytest.MonkeyPatch, failures: int, max_tries: int) -> None:
    assume(max_tries > 0)
    monkeypatch.setattr(retry, "backoff", None)
    monkeypatch.setattr(retry.time, "sleep", lambda *_: None)
    calls = {"n": 0}

    def func() -> str:
        calls["n"] += 1
        if calls["n"] <= failures:
            raise ValueError("boom")
        return "ok"

    wrapped = retry.with_retry(func, max_tries=max_tries)
    if failures >= max_tries:
        with pytest.raises(ValueError):
            wrapped()
        assert calls["n"] == max_tries
    else:
        assert wrapped() == "ok"
        assert calls["n"] == failures + 1


@settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(failures=st.integers(min_value=0, max_value=4), max_tries=st.integers(min_value=1, max_value=5))
def test_with_retry_async_property(monkeypatch: pytest.MonkeyPatch, failures: int, max_tries: int) -> None:
    assume(max_tries > 0)
    monkeypatch.setattr(retry, "backoff", None)

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(retry.asyncio, "sleep", no_sleep)
    calls = {"n": 0}

    async def func() -> str:
        calls["n"] += 1
        if calls["n"] <= failures:
            raise ValueError("boom")
        return "ok"

    wrapped = retry.with_retry(func, max_tries=max_tries)
    if failures >= max_tries:
        with pytest.raises(ValueError):
            asyncio.run(wrapped())
        assert calls["n"] == max_tries
    else:
        assert asyncio.run(wrapped()) == "ok"
        assert calls["n"] == failures + 1
