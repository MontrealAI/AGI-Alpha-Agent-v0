# SPDX-License-Identifier: Apache-2.0
"""Minimal stub for openai_agents.

Provides basic classes so demos import without the real SDK."""

import importlib.machinery
import os
from pathlib import Path
from typing import Any, Callable, TypeVar

_loader = importlib.machinery.SourceFileLoader(__name__, __file__)
__spec__ = importlib.machinery.ModuleSpec(__name__, _loader, origin=__file__)

__version__ = "0.0.17"


class AgentRuntime:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def register(self, *args: Any, **kwargs: Any) -> None:
        pass


class OpenAIAgent:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __call__(self, text: str) -> str:  # pragma: no cover - demo stub
        patch_file = os.environ.get("PATCH_FILE")
        if patch_file:
            return Path(patch_file).read_text(encoding="utf-8")
        return "ok"


# Mirror new SDK naming
Agent = OpenAIAgent


F = TypeVar("F", bound=Callable[..., Any])


def Tool(*_args: Any, **_kwargs: Any) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        return func

    return decorator


function_tool = Tool
