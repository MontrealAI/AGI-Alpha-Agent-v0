#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# NOTE: This demo is a research prototype and does not implement real AGI.
"""Self-contained Ω‑Lattice business demo.

The preserved research loop computes a dimensionless, Gibbs-inspired toy score.
Signals and job posting are illustrative; no physical free energy, on-chain job,
formal proof or trained weight change is produced. The enterprise CLI is the
maintained default. Integrations here require explicit opt-in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import argparse
import logging
import math
import asyncio
import os
import hashlib
import json
import random
import time
from typing import Any, Callable, cast

from alpha_factory_v1.common.utils import local_llm

log = logging.getLogger(__name__)


class OpenAIAgent:
    """Compatibility adapter using the real SDK, never the repository's stub."""

    def __init__(self, model: str, api_key: str | None) -> None:
        self.model = model
        self.api_key = api_key

    async def __call__(self, prompt: str) -> str:
        from agents import Agent, Runner, RunConfig, OpenAIResponsesModel
        from openai import AsyncOpenAI

        async with AsyncOpenAI(api_key=self.api_key, timeout=20, max_retries=0) as client:
            agent = Agent(
                name="Business 3 research commentator",
                instructions="Explain the supplied toy score. Do not claim real-world returns or validated AGI.",
                model=OpenAIResponsesModel(model=self.model, openai_client=client),
            )
            result = await Runner.run(agent, prompt, max_turns=1, run_config=RunConfig(tracing_disabled=True))
            return str(result.final_output)


try:  # optional Google ADK client
    from google_adk import Client as ADKClient
except Exception:  # pragma: no cover - offline fallback
    try:
        from google.adk import Client as ADKClient
    except Exception:
        ADKClient = None

try:  # optional A2A message socket
    from a2a import A2ASocket
except Exception:  # pragma: no cover - missing dependency
    A2ASocket = None

_A2A: Any | None = None


@dataclass(slots=True)
class Orchestrator:
    """Source and sink for alpha signals."""

    def collect_signals(self) -> dict[str, Any]:
        """Fetch a bundle of live signals.

        Returns a placeholder dictionary in this demo.  Production
        implementations would gather market data, sensor readings,
        or any other real‑time metrics.
        """
        return {
            "timestamp": time.time(),
            "market_temp": random.uniform(0.8, 1.2),
            "price_dislocation": random.gauss(0, 0.05),
        }

    def post_alpha_job(self, bundle_id: str | None, delta_g: float | None) -> None:
        """Broadcast a new job for agents when ``delta_g`` is favourable."""

        if bundle_id is None or delta_g is None:
            log.info("[Orchestrator] Ignoring job with missing data")
            return

        log.info(
            "[Orchestrator] Posting alpha job for bundle %s with ΔG=%.6f",
            bundle_id,
            delta_g,
        )


@dataclass(slots=True)
class AgentFin:
    """Finance agent returning latent-work estimates."""

    def latent_work(self, bundle: dict[str, Any]) -> float:
        """Compute mispricing alpha from ``bundle``."""
        return float(bundle.get("price_dislocation", 0))


@dataclass(slots=True)
class AgentRes:
    """Research agent estimating entropy."""

    def entropy(self, bundle: dict[str, Any]) -> float:
        """Return inferred entropy from ``bundle``."""
        return abs(float(bundle.get("price_dislocation", 0))) / 4


@dataclass(slots=True)
class AgentEne:
    """Energy agent inferring market temperature ``β``."""

    def market_temperature(self, bundle: dict[str, Any]) -> float:
        """Estimate current market temperature."""
        return float(bundle.get("market_temp", 1.0))


@dataclass(slots=True)
class AgentGdl:
    """Fail-closed research verifier hook, not a built-in formal proof system."""

    verifier: Callable[[dict[str, Any]], bool] | None = None

    def provable(self, weight_update: dict[str, Any]) -> bool:
        """Reject absent evidence or absent verification, including empty updates."""
        if not weight_update or self.verifier is None:
            return False
        try:
            return self.verifier(weight_update) is True
        except Exception:
            return False


async def _llm_comment(delta_g: float) -> str:
    """Return a short LLM comment on ``delta_g`` if OpenAI Agents is available."""

    prompt = f"In one sentence, comment on ΔG={delta_g:.4f} for the business."

    # Preserve compatibility with explicitly injected research adapters.
    if OpenAIAgent is None or not callable(OpenAIAgent):
        return cast(str, local_llm.chat(prompt))

    if not os.getenv("OPENAI_API_KEY"):
        return cast(str, local_llm.chat(prompt))

    agent = OpenAIAgent(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    try:
        return cast(str, await asyncio.wait_for(agent(prompt), timeout=30))
    except Exception as exc:  # pragma: no cover - provider failures
        raise RuntimeError(
            f"Requested model commentary failed ({type(exc).__name__}); no fallback was substituted"
        ) from exc


@dataclass(slots=True)
class Model:
    """In-memory research proposals; no trained model weights are represented."""

    proposals: list[dict[str, Any]] = field(default_factory=list)

    def commit(self, weight_update: dict[str, Any]) -> None:
        """Retain an explicitly checked nonempty proposal without claiming training."""
        if not weight_update:
            raise ValueError("An empty proposal is not a model update")
        self.proposals.append(json.loads(json.dumps(weight_update, allow_nan=False)))
        log.info("[Model] Research proposal retained in memory; no trained weights changed")


async def _close_adk_client(client: Any | None) -> None:
    """Attempt to gracefully close an ADK client."""

    if client is None:
        return

    closer = getattr(client, "close", None)
    if closer is not None:
        try:
            if asyncio.iscoroutinefunction(closer):
                await closer()
            else:
                await asyncio.to_thread(closer)
        except Exception:  # pragma: no cover - best effort
            log.warning("Failed to close ADK client", exc_info=True)
    elif hasattr(client, "__aexit__"):
        aexit = getattr(client, "__aexit__")
        try:
            if asyncio.iscoroutinefunction(aexit):
                await aexit(None, None, None)
            else:
                await asyncio.to_thread(aexit, None, None, None)
        except Exception:  # pragma: no cover - best effort
            log.warning("Failed to close ADK client", exc_info=True)


async def run_cycle_async(
    orchestrator: Orchestrator,
    fin_agent: AgentFin,
    res_agent: AgentRes,
    ene_agent: AgentEne,
    gdl_agent: AgentGdl,
    model: Model,
    adk_client: Any | None = None,
    a2a_socket: Any | None = None,
    *,
    commentary: bool = True,
    close_adk: bool = True,
    require_model: bool = False,
) -> None:
    """Execute one evaluation + commitment cycle."""

    try:
        bundle = orchestrator.collect_signals()
        delta_h = fin_agent.latent_work(bundle)
        delta_s = res_agent.entropy(bundle)
        beta = ene_agent.market_temperature(bundle)
        if not all(math.isfinite(value) for value in (delta_h, delta_s, beta)) or beta <= 0:
            raise ValueError("Research inputs must be finite and beta must be positive")
        delta_g = delta_h - (delta_s / beta)
        if not math.isfinite(delta_g):
            raise ValueError("Research score overflowed; use bounded finite inputs")

        log.info("ΔH=%s ΔS=%s β=%s → ΔG=%s", delta_h, delta_s, beta, delta_g)

        comment = await _llm_comment(delta_g) if commentary else "Model commentary not requested"
        if require_model and comment.startswith("[offline]"):
            raise RuntimeError(
                "Requested local model did not load; install its runtime and verify the local weight path"
            )
        log.info("LLM: %s", comment)

        if a2a_socket is not None:
            try:
                a2a_socket.sendjson({"delta_g": delta_g})
            except Exception:  # pragma: no cover - best effort
                log.warning("A2A send failed", exc_info=True)

        if adk_client is not None:
            try:
                if asyncio.iscoroutinefunction(getattr(adk_client, "run", None)):
                    await adk_client.run(comment)
                elif hasattr(adk_client, "run"):
                    await asyncio.to_thread(adk_client.run, comment)
            except Exception:  # pragma: no cover - best effort
                log.warning("ADK client error", exc_info=True)

        if delta_g < 0:
            bundle_hash = hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest()[:8]
            orchestrator.post_alpha_job(bundle_hash, delta_g)

        weight_update: dict[str, Any] = {}
        if gdl_agent.provable(weight_update):
            model.commit(weight_update)
        else:
            log.info("[Godel] No independently verified update; model change blocked")
    finally:
        if close_adk:
            await _close_adk_client(adk_client)


def run_cycle(
    orchestrator: Orchestrator,
    fin_agent: AgentFin,
    res_agent: AgentRes,
    ene_agent: AgentEne,
    gdl_agent: AgentGdl,
    model: Model,
    adk_client: Any | None = None,
    a2a_socket: Any | None = None,
) -> asyncio.Task[None] | None:
    """Execute one evaluation cycle, creating an event loop if required."""

    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop is not None:
        return running_loop.create_task(
            run_cycle_async(
                orchestrator,
                fin_agent,
                res_agent,
                ene_agent,
                gdl_agent,
                model,
                adk_client,
                a2a_socket,
            )
        )

    asyncio.run(
        run_cycle_async(
            orchestrator,
            fin_agent,
            res_agent,
            ene_agent,
            gdl_agent,
            model,
            adk_client,
            a2a_socket,
        )
    )


async def _main(argv: list[str] | None = None) -> None:
    """Entry point for command line execution."""

    ap = argparse.ArgumentParser(description="Preserved Ω-Lattice research loop; signals and job posting are simulated")
    ap.add_argument("--loglevel", default="INFO", type=str.upper, choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    ap.add_argument(
        "--commentary", choices=["none", "local", "openai"], default="none", help="Explicit optional inference"
    )
    ap.add_argument("--enable-integrations", action="store_true", help="Enable configured ADK/A2A research adapters")
    ap.add_argument(
        "--cycles",
        type=int,
        default=1,
        help="Number of cycles to run (0 = forever)",
    )
    ap.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds to sleep between cycles",
    )
    ap.add_argument("--a2a-port", type=int, help="A2A gRPC port")
    ap.add_argument("--a2a-host", help="A2A gRPC host")
    ap.add_argument("--adk-host", help="ADK gateway host")
    ap.add_argument("--local-llm-url", help="Base URL for the local model")
    ap.add_argument("--llama-model-path", help="Path to local .gguf weights")
    ap.add_argument("--llama-n-ctx", type=int, help="Context window for local models")
    ap.add_argument("--openai-api-key", help="OpenAI API key")
    args = ap.parse_args(argv)

    if args.cycles < 0 or args.cycles > 1_000_000:
        ap.error("--cycles must be 0 (explicit continuous mode) through 1000000")
    if not math.isfinite(args.interval) or not 0 <= args.interval <= 3600:
        ap.error("--interval must be finite and between 0 and 3600 seconds")
    if args.a2a_port is not None and not 0 <= args.a2a_port <= 65535:
        ap.error("--a2a-port must be 0 through 65535")
    if args.llama_n_ctx is not None and not 1 <= args.llama_n_ctx <= 131072:
        ap.error("--llama-n-ctx must be 1 through 131072")
    if args.openai_api_key is not None:
        args.commentary = "openai"
    if args.commentary == "openai" and not (args.openai_api_key or os.getenv("OPENAI_API_KEY")):
        ap.error("OpenAI commentary requires OPENAI_API_KEY")
    if args.commentary == "local" and not (args.llama_model_path or os.getenv("LLAMA_MODEL_PATH")):
        ap.error("Local commentary requires an existing --llama-model-path")

    if args.commentary == "local":
        os.environ["OPENAI_API_KEY"] = ""
    if args.openai_api_key is not None:
        os.environ["OPENAI_API_KEY"] = args.openai_api_key
    if args.local_llm_url is not None:
        os.environ["LOCAL_LLM_URL"] = args.local_llm_url
    if args.llama_model_path is not None:
        os.environ["LLAMA_MODEL_PATH"] = args.llama_model_path
    if args.llama_n_ctx is not None:
        os.environ["LLAMA_N_CTX"] = str(args.llama_n_ctx)
    if args.adk_host is not None:
        os.environ["ADK_HOST"] = args.adk_host
    if args.a2a_host is not None:
        os.environ["A2A_HOST"] = args.a2a_host
    if args.a2a_port is not None:
        os.environ["A2A_PORT"] = str(args.a2a_port)

    global _A2A
    if args.a2a_port is not None:
        port = args.a2a_port
    elif args.enable_integrations:
        try:
            port = int(os.getenv("A2A_PORT", "0"))
        except ValueError:  # pragma: no cover - invalid env var
            log.warning("Invalid A2A_PORT=%r", os.getenv("A2A_PORT"))
            port = 0
    else:
        port = 0
    if not 0 <= port <= 65535:
        ap.error("A2A_PORT must be 0 through 65535")
    if port and A2ASocket is None:
        ap.error("The requested A2A research adapter is not installed")
    adk_host = args.adk_host or (os.getenv("ADK_HOST") if args.enable_integrations else None)
    if adk_host and ADKClient is None:
        ap.error("The requested ADK research adapter is not installed")
    if port > 0 and A2ASocket is not None:
        host = args.a2a_host or os.getenv("A2A_HOST", "localhost")
        _A2A = A2ASocket(host=host, port=port, app_id="alpha_business_v3")
    else:
        _A2A = None
    a2a_socket = _A2A

    logging.basicConfig(
        level=args.loglevel.upper(),
        format="%(asctime)s %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    orchestrator = Orchestrator()
    fin_agent = AgentFin()
    res_agent = AgentRes()
    ene_agent = AgentEne()
    gdl_agent = AgentGdl()
    model = Model()

    adk_client = None

    cycle = 0
    try:
        adk_client = ADKClient(adk_host) if adk_host and ADKClient else None
        if a2a_socket:
            a2a_socket.start()
        while True:
            await run_cycle_async(
                orchestrator,
                fin_agent,
                res_agent,
                ene_agent,
                gdl_agent,
                model,
                adk_client,
                a2a_socket,
                commentary=args.commentary != "none",
                close_adk=False,
                require_model=args.commentary == "local",
            )
            cycle += 1
            if args.cycles and cycle >= args.cycles:
                break
            await asyncio.sleep(args.interval)
    finally:
        if a2a_socket:
            try:
                a2a_socket.stop()
            except Exception:  # pragma: no cover - best effort
                log.warning("Failed to stop A2A socket", exc_info=True)
        if adk_client is not None:
            await _close_adk_client(adk_client)


async def main(argv: list[str] | None = None) -> None:
    """Run explicit research integrations while restoring the caller's settings."""
    keys = ("OPENAI_API_KEY", "LOCAL_LLM_URL", "LLAMA_MODEL_PATH", "LLAMA_N_CTX", "ADK_HOST", "A2A_HOST", "A2A_PORT")
    previous = {key: os.environ.get(key) for key in keys}
    try:
        await _main(argv)
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":  # pragma: no cover - manual execution
    asyncio.run(main())
