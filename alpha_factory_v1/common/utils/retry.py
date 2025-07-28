# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import Any, Awaitable, Callable, ParamSpec, TypeVar, overload, cast

try:  # pragma: no cover - optional dependency
    import backoff
except Exception:  # pragma: no cover - fallback if missing
    backoff = None

from .logging import _log
import asyncio
import inspect
import time

P = ParamSpec("P")
T = TypeVar("T")


@overload
def with_retry(func: Callable[P, Awaitable[T]], *, max_tries: int = 3) -> Callable[P, Awaitable[T]]:
    ...


@overload
def with_retry(func: Callable[P, T], *, max_tries: int = 3) -> Callable[P, T]:
    ...


def with_retry(func: Callable[P, Any], *, max_tries: int = 3) -> Callable[P, Any]:
    """Wrap *func* with exponential backoff and logging."""

    def _log_retry(details: dict[str, Any]) -> None:
        _log.warning(
            "Retry %d/%d for %s due to %s",
            details["tries"],
            max_tries,
            getattr(details.get("target"), "__name__", "call"),
            details.get("exception"),
        )

    is_async = inspect.iscoroutinefunction(func)

    if backoff is not None:
        wrapped = backoff.on_exception(
            backoff.expo,
            Exception,
            max_tries=max_tries,
            jitter=backoff.full_jitter,
            on_backoff=_log_retry,
        )(func)
        if is_async:
            return cast(Callable[P, Awaitable[T]], wrapped)
        return cast(Callable[P, T], wrapped)

    if is_async:

        async def wrapper_async(*args: P.args, **kwargs: P.kwargs) -> Any:
            for attempt in range(max_tries):
                try:
                    return await cast(Callable[P, Awaitable[T]], func)(*args, **kwargs)
                except Exception as exc:  # pragma: no cover - runtime errors
                    if attempt + 1 >= max_tries:
                        raise
                    _log_retry(
                        {
                            "tries": attempt + 1,
                            "exception": exc,
                            "target": func,
                        }
                    )
                    await asyncio.sleep(2**attempt * 0.1)
            raise AssertionError("unreachable")

        return wrapper_async

    def wrapper_sync(*args: P.args, **kwargs: P.kwargs) -> Any:
        for attempt in range(max_tries):
            try:
                return cast(Callable[P, T], func)(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - runtime errors
                if attempt + 1 >= max_tries:
                    raise
                _log_retry(
                    {
                        "tries": attempt + 1,
                        "exception": exc,
                        "target": func,
                    }
                )
                time.sleep(2**attempt * 0.1)
        raise AssertionError("unreachable")

    return wrapper_sync
