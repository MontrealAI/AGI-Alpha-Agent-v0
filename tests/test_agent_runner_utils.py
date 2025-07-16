import os
import asyncio
from alpha_factory_v1.backend.agent_runner import _env_float, maybe_await, utc_now


def test_env_float_valid(monkeypatch):
    monkeypatch.setenv("AF_TEST", "1.5")
    assert _env_float("AF_TEST", 2.0) == 1.5


def test_env_float_invalid(monkeypatch):
    monkeypatch.setenv("AF_TEST", "bad")
    assert _env_float("AF_TEST", 3.0) == 3.0


async def _async_fn(x):
    await asyncio.sleep(0)
    return x * 2


def _sync_fn(x):
    return x + 1


def test_maybe_await_async():
    result = asyncio.run(maybe_await(_async_fn, 5))
    assert result == 10


def test_maybe_await_sync():
    result = asyncio.run(maybe_await(_sync_fn, 5))
    assert result == 6


def test_utc_now_timezone():
    assert utc_now().endswith("+00:00")
