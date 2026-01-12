# SPDX-License-Identifier: Apache-2.0
"""
alpha_factory_v1.backend.llm_provider
=====================================

Unified Large-Language-Model facade for Alpha-Factory v1
--------------------------------------------------------
• Seamlessly chooses the best backend available at runtime:
      ─ OpenAI GPT-4o / GPT-4o-mini  (needs OPENAI_API_KEY)
      ─ Anthropic Claude-3-Opus      (needs ANTHROPIC_API_KEY)
      ─ Local SBERT heuristic        (works fully offline)

• Optional Model-Context-Protocol off-loading via MCP_ENDPOINT.

• Streaming or blocking replies, plus provider-agnostic embeddings with
  automatic SBERT/hashing fallback if OpenAI errors.

Usage
~~~~~
>>> from backend.llm_provider import chat
>>> reply = await chat("Who founded Montreal?")

Legacy code that still calls the OpenAI SDK keeps working unchanged.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from functools import lru_cache
from typing import (
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Union,
)

from .mcp_bridge import store as _mcp_store_async

__all__ = ["chat", "embed"]

# Chat message type alias for clarity
ChatMessage = Dict[str, str]

# --------------------------------------------------------------------- #
#  Third-party SDKs – imported lazily so the file works even when the   #
#  corresponding cloud key / wheel is absent.                           #
# --------------------------------------------------------------------- #
try:
    import openai
except ModuleNotFoundError:  # Keyless or stripped container image
    openai = None  # type: ignore[assignment]

try:
    import anthropic
except ModuleNotFoundError:
    anthropic = None  # type: ignore[assignment]

# --------------------------------------------------------------------- #
#  Environment & logging                                                #
# --------------------------------------------------------------------- #
_OPENAI_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
_ANTHROPIC_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SEC", 30))
_DEFAULT_TEMP = float(os.getenv("LLM_TEMPERATURE", 0.2))

_LOG = logging.getLogger("alpha_factory.llm")
_LOG.addHandler(logging.NullHandler())


# --------------------------------------------------------------------- #
#  Helper functions                                                     #
# --------------------------------------------------------------------- #
def _provider() -> str:
    """Return the *effective* provider name chosen for this run."""
    if _OPENAI_KEY and openai:
        return "openai"
    if _ANTHROPIC_KEY and anthropic:
        return "anthropic"
    return "local"


def _note(model: str) -> None:
    _LOG.info("🔮  LLM call | provider=%s | model=%s", _provider(), model)


# --------------------------------------------------------------------- #
#  Public API – embeddings                                              #
# --------------------------------------------------------------------- #
@lru_cache(maxsize=128)
def _sync_embed(text: str) -> List[float]:
    """
    Synchronous embedding helper (cached).
    Delegates to the first provider that is both installed *and* keyed.
    """

    def _hash_embed(value: str, dim: int = 384) -> List[float]:
        digest = hashlib.sha256(value.encode("utf-8")).digest()
        values = [(1 if b & 1 else -1) * ((b >> 1) / 128.0) for b in digest]
        values *= (dim + len(values) - 1) // len(values)
        vec = values[:dim]
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]

    def _local() -> List[float]:
        from sentence_transformers import SentenceTransformer

        _note("local-sbert")
        try:
            model = SentenceTransformer("all-MiniLM-L6-v2")
            return model.encode(text).tolist()  # type: ignore[return-value]
        except Exception as exc:  # pragma: no cover - offline/model fetch issues
            _LOG.warning("Local SBERT embedding failed: %s – using hash fallback", exc)
            return _hash_embed(text)

    if openai and _OPENAI_KEY:
        _note("text-embedding-3-small")
        openai.api_key = _OPENAI_KEY
        try:
            res = openai.Embedding.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=1536,
                timeout=_TIMEOUT,
            )
            return res["data"][0]["embedding"]  # type: ignore[index]
        except (openai.OpenAIError, OSError) as exc:  # type: ignore[attr-defined]
            _LOG.warning("OpenAI embedding failed: %s – using local fallback", exc)
            return _local()

    if anthropic and _ANTHROPIC_KEY:
        _note("claude-embedding-1")
        client = anthropic.Anthropic(api_key=_ANTHROPIC_KEY, timeout=_TIMEOUT)
        res = client.embeddings.create(model="claude-embedding-1", input=text)
        return res.embedding  # type: ignore[attr-defined]

    return _local()


async def embed(text: str) -> List[float]:
    """Asynchronous wrapper around :func:`_sync_embed`."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_embed, text)


# --------------------------------------------------------------------- #
#  Public API – chat / completions                                      #
# --------------------------------------------------------------------- #
async def chat(
    prompt_or_messages: Union[str, List[ChatMessage]],
    *,
    stream: bool = False,
    temperature: float = _DEFAULT_TEMP,
    max_tokens: int = 1024,
) -> Union[str, AsyncGenerator[str, None]]:
    """
    Provider-agnostic chat endpoint.

    Parameters
    ----------
    prompt_or_messages
        Either a plain user string or a list of OpenAI-style chat messages.
    stream
        When *True* an async generator yielding tokens is returned.
    """
    # Normalise input --------------------------------------------------- #
    if isinstance(prompt_or_messages, str):
        messages: List[ChatMessage] = [{"role": "user", "content": prompt_or_messages}]
    else:
        messages = prompt_or_messages

    # Best-effort MCP off-load (does not block main request) ------------ #
    asyncio.create_task(_mcp_store_async(messages))

    # Dispatch to chosen provider -------------------------------------- #
    prov = _provider()
    if prov == "openai":
        return await _chat_openai(messages, stream, temperature, max_tokens)
    if prov == "anthropic":
        return await _chat_anthropic(messages, stream, temperature, max_tokens)
    return await _chat_local(messages, stream)


# --------------------------------------------------------------------- #
#  Provider implementations                                             #
# --------------------------------------------------------------------- #
async def _chat_openai(
    messages: List[ChatMessage],
    stream: bool,
    temperature: float,
    max_tokens: int,
) -> Union[str, AsyncGenerator[str, None]]:
    assert openai and _OPENAI_KEY  # Sanity – guaranteed by _provider
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    _note(model)

    openai.api_key = _OPENAI_KEY
    openai.httpx_timeout = _TIMEOUT  # OpenAI v1.x setting

    if not stream:
        resp = await openai.ChatCompletion.acreate(  # type: ignore[attr-defined]
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        return resp.choices[0].message.content  # type: ignore[return-value]

    async def _token_stream() -> AsyncGenerator[str, None]:
        async for chunk in await openai.ChatCompletion.acreate(  # type: ignore[attr-defined]
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        ):
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    return _token_stream()


async def _chat_anthropic(
    messages: List[ChatMessage],
    stream: bool,
    temperature: float,
    max_tokens: int,
) -> Union[str, AsyncGenerator[str, None]]:
    assert anthropic and _ANTHROPIC_KEY
    model = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
    _note(model)

    client = anthropic.AsyncAnthropic(api_key=_ANTHROPIC_KEY, timeout=_TIMEOUT)

    system_prompt = "\n".join(m["content"] for m in messages if m["role"] == "system") or "You are a helpful assistant."
    user_content = "\n".join(m["content"] for m in messages if m["role"] != "system")

    if not stream:
        resp = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return resp.content[0].text  # type: ignore[return-value]

    async def _token_stream() -> AsyncGenerator[str, None]:
        async with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        ) as stream_iter:
            async for chunk in stream_iter:
                delta = chunk.delta.text
                if delta:
                    yield delta

    return _token_stream()


async def _chat_local(
    messages: List[ChatMessage],
    stream: bool,
) -> Union[str, AsyncGenerator[str, None]]:
    """Last-resort heuristic – keeps demos alive when no cloud key is present."""
    _note("local-sbert-heuristic")
    answer = "⚠️ Offline mode heuristic reply:\n\n" + messages[-1]["content"][:400] + "\n\n[end of local answer]"

    if not stream:
        return answer

    async def _token_stream() -> AsyncGenerator[str, None]:
        for tok in answer.split():
            yield tok + " "
            await asyncio.sleep(0.01)

    return _token_stream()
