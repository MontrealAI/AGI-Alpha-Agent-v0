# SPDX-License-Identifier: Apache-2.0
"""Bounded integer rewrites with explicit optional provider calls and offline fallback."""
from __future__ import annotations

import importlib.util
import logging
import math
import os
import random
import re
import time
from typing import List

try:
    import httpx
except ImportError:  # pragma: no cover - optional dependency
    httpx = None


def store_sync(messages: list[dict[str, str]]) -> None:
    """Send bounded prompt records only when an MCP endpoint is explicitly configured."""
    endpoint = os.getenv("MCP_ENDPOINT")
    if not endpoint or httpx is None:
        return
    try:
        timeout = float(os.getenv("MCP_TIMEOUT_SEC", "10"))
        if not math.isfinite(timeout) or not 0 < timeout <= 30:
            raise ValueError("MCP timeout must be finite and at most 30 seconds")
        httpx.post(f"{endpoint}/context", json={"messages": messages, "timestamp": time.time()}, timeout=timeout)
    except Exception:
        logging.getLogger(__name__).debug("MCP persistence unavailable", exc_info=True)


def meta_rewrite(agents: List[int], *, rng: random.Random | None = None) -> List[int]:
    """Tweak one component; an empty population remains empty."""
    result = list(agents)
    if result:
        source = rng if rng is not None else random
        index = source.randrange(len(result))
        result[index] += source.choice([-1, 1])
    return result


def _parse_numbers(text: str, fallback: List[int]) -> List[int]:
    """Bound provider text and policy integers; retain the historical increment fallback."""
    if not fallback:
        return []
    tokens = re.findall(r"-?\d+", text) if len(text) <= 10000 else []
    if len(tokens) != len(fallback) or any(len(token) > 6 for token in tokens):
        return [p + 1 for p in fallback]
    numbers = [int(token) for token in tokens]
    return numbers if all(abs(number) <= 10000 for number in numbers) else [p + 1 for p in fallback]


def _available(name: str, key: str) -> bool:
    if os.getenv("NO_LLM") == "1" or not os.getenv(key):
        return False
    try:
        return importlib.util.find_spec(name) is not None
    except (ValueError, ModuleNotFoundError):
        return False


def openai_rewrite(
    agents: List[int], model: str | None = None, *, target: int = 5, rng: random.Random | None = None
) -> List[int]:
    """Perform one synchronous, time-bounded OpenAI call when explicitly selected."""
    if _available("openai", "OPENAI_API_KEY"):
        try:  # pragma: no cover - real provider requests are not required by offline tests
            from openai import OpenAI

            messages = [
                {"role": "system", "content": "Return only a JSON array of integers. Do not include explanation."},
                {"role": "user", "content": f"Improve {agents} toward target {target}, preserving its length."},
            ]
            with OpenAI(timeout=15.0, max_retries=0) as client:
                response = client.chat.completions.create(
                    model=model or os.getenv("OPENAI_MODEL", "gpt-4o"), messages=messages, max_tokens=128
                )
            content = response.choices[0].message.content or ""
            store_sync(messages + [{"role": "assistant", "content": content}])
            return _parse_numbers(content, agents)
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "OpenAI rewrite unavailable (%s); using offline mutation", type(exc).__name__
            )
    return meta_rewrite(agents, rng=rng)


def anthropic_rewrite(
    agents: List[int], model: str | None = None, *, target: int = 5, rng: random.Random | None = None
) -> List[int]:
    """Perform one synchronous, time-bounded Anthropic call when explicitly selected."""
    if _available("anthropic", "ANTHROPIC_API_KEY"):
        try:  # pragma: no cover - optional provider
            import anthropic

            messages = [
                {
                    "role": "user",
                    "content": f"Return only a JSON integer array improving {agents} toward {target}; preserve its length.",
                }
            ]
            with anthropic.Anthropic(timeout=15.0, max_retries=0) as client:
                response = client.messages.create(
                    model=model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
                    max_tokens=128,
                    messages=messages,
                )
            content = "".join(getattr(block, "text", "") for block in response.content)
            store_sync(messages + [{"role": "assistant", "content": content}])
            return _parse_numbers(content, agents)
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Anthropic rewrite unavailable (%s); using offline mutation", type(exc).__name__
            )
    return meta_rewrite(agents, rng=rng)
