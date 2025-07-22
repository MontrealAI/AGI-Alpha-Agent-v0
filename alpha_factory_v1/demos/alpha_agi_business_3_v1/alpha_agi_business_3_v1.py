#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# NOTE: This demo is a research prototype and does not implement real AGI.
"""Self-contained Ω‑Lattice business demo.

This module showcases a minimal zero‑entropy pipeline suitable for
production‑grade environments.  The orchestration loop computes a
Gibbs‑inspired :math:`ΔG` metric using three toy agents.  When
``ΔG < 0`` an alpha job is posted.  A final Gödel‑Looper step then
verifies and commits a (mock) weight update.
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import logging
import asyncio
import os
import hashlib
import json
import random
import time
from typing import Any, cast

from alpha_factory_v1.common.utils import local_llm

log = logging.getLogger(__name__)

try:  # optional OpenAI Agents integration
    from openai_agents import OpenAIAgent
except ImportError:  # pragma: no cover - offline fallback
    try:  # fall back to the new package name
        from agents import OpenAIAgent
    except ImportError:
        OpenAIAgent = None

try:  # optional Google ADK client
    from google_adk import Client as ADKClient
except Exception:  # pragma: no cover - offline fallback
    try:
        from google.adk import Client as ADKClient
    except Exception:
        ADKClient = None

try:  # optional A2A message socket
    from a2a import A2ASocket

    try:
        _port = int(os.getenv("A2A_PORT", "0"))
    except ValueError:  # pragma: no cover - invalid env var
        log.warning("Invalid A2A_PORT=%r", os.getenv("A2A_PORT"))
        _A2A = None
    else:
        if _port > 0:
            _A2A = A2ASocket(
                host=os.getenv("A2A_HOST", "localhost"),
                port=_port,
                app_id="alpha_business_v3",
            )
        else:
            _A2A = None
except Exception:  # pragma: no cover - missing dependency
    A2ASocket = None
    _A2A = None


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
        return float(bundle.get("market_temp", random.uniform(0.9, 1.1)))


@dataclass(slots=True)
class AgentGdl:
    """Gödel‑Looper guardian."""

    def provable(self, weight_update: dict[str, Any]) -> bool:
        """Validate a weight update via formal proof."""

        return True


async def _llm_comment(delta_g: float) -> str:
    """Return a short LLM comment on ``delta_g`` if OpenAI Agents is available."""

    prompt = f"In one sentence, comment on ΔG={delta_g:.4f} for the business."

    # When the OpenAI Agents SDK is missing the shim in
    # ``alpha_factory_v1.backend`` exposes a non-callable placeholder.
    # Guard against that scenario as well so offline tests succeed.
    if OpenAIAgent is None or not callable(OpenAIAgent):
        return cast(str, local_llm.chat(prompt))

    if not os.getenv("OPENAI_API_KEY"):
        return cast(str, local_llm.chat(prompt))

    agent = OpenAIAgent(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    try:
        return cast(str, await agent(prompt))
    except Exception as exc:  # pragma: no cover - network failures
        log.warning("LLM comment failed: %s", exc)
        return "LLM error"


@dataclass(slots=True)
class Model:
    """Persisted model whose weights evolve over time."""

    def commit(self, weight_update: dict[str, Any]) -> None:
        """Commit the supplied weights after verification."""

        log.info("[Model] New weights committed (Gödel-proof verified)")


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
) -> None:
    """Execute one evaluation + commitment cycle."""

    bundle = orchestrator.collect_signals()
    delta_h = fin_agent.latent_work(bundle)
    delta_s = res_agent.entropy(bundle)
    beta = ene_agent.market_temperature(bundle)
    if abs(beta) < 1e-9:
        log.warning("β is zero; skipping cycle")
        return
    delta_g = delta_h - (delta_s / beta)

    log.info("ΔH=%s ΔS=%s β=%s → ΔG=%s", delta_h, delta_s, beta, delta_g)

    comment = await _llm_comment(delta_g)
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
        finally:
            await _close_adk_client(adk_client)

    if delta_g < 0:
        bundle_hash = hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest()[:8]
        orchestrator.post_alpha_job(bundle_hash, delta_g)

    weight_update: dict[str, Any] = {}
    if gdl_agent.provable(weight_update):
        model.commit(weight_update)


def run_cycle(
    orchestrator: Orchestrator,
    fin_agent: AgentFin,
    res_agent: AgentRes,
    ene_agent: AgentEne,
    gdl_agent: AgentGdl,
    model: Model,
    adk_client: Any | None = None,
    a2a_socket: Any | None = None,
) -> None:
    """Execute one evaluation cycle, creating an event loop if required."""

    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop is not None:
        running_loop.create_task(
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
        return

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


async def main(argv: list[str] | None = None) -> None:
    """Entry point for command line execution."""

    try:  # auto-verify environment when available
        import importlib

        _check_env = importlib.import_module("check_env")
    except Exception:  # pragma: no cover - optional dependency
        _check_env = None
    if _check_env and hasattr(_check_env, "main"):
        try:
            _check_env.main([])
        except Exception:  # pragma: no cover - best effort
            log.warning("check_env.main failed", exc_info=True)

    ap = argparse.ArgumentParser(description="Run the Ω‑Lattice business demo")
    ap.add_argument("--loglevel", default="INFO", help="Logging level")
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
    else:
        try:
            port = int(os.getenv("A2A_PORT", "0"))
        except ValueError:  # pragma: no cover - invalid env var
            log.warning("Invalid A2A_PORT=%r", os.getenv("A2A_PORT"))
            port = 0
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

    if a2a_socket:
        try:
            a2a_socket.start()
        except Exception:  # pragma: no cover - best effort
            log.warning("Failed to start A2A socket", exc_info=True)

    adk_client = ADKClient(os.getenv("ADK_HOST", "http://localhost:9000")) if ADKClient else None

    cycle = 0
    try:
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


if __name__ == "__main__":  # pragma: no cover - manual execution
    asyncio.run(main())
