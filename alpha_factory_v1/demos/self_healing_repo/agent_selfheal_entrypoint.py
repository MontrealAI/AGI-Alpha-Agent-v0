# SPDX-License-Identifier: Apache-2.0
# mypy: ignore-errors
"""
Self‑Healing Repo demo
──────────────────────
1. Clones a deliberately broken sample repo (tiny_py_calc).
2. Detects failing pytest run.
3. Uses OpenAI Agents SDK to propose & apply a patch via patcher_core.
4. Opens a Pull Request‑style diff in the dashboard and re‑runs tests.
"""
import asyncio
import importlib
import logging
import os
import pathlib
import shutil
import subprocess
import sys

if "gradio" in sys.modules:
    gr = sys.modules["gradio"]
elif importlib.util.find_spec("gradio"):
    gr = importlib.import_module("gradio")
else:
    class _FallbackBlocks:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FallbackMarkdown:
        def __init__(self, *a, **k):
            pass

    class _FallbackButton:
        def __init__(self, *a, **k):
            pass

        def click(self, *a, **k):
            return None

    def _mount_gradio_app(app, *_a, **_k):
        return app

    gr = type(
        "FallbackGradio",
        (),
        {
            "Blocks": _FallbackBlocks,
            "Markdown": _FallbackMarkdown,
            "Button": _FallbackButton,
            "mount_gradio_app": staticmethod(_mount_gradio_app),
        },
    )
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import uvicorn

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if "openai_agents" in sys.modules:
    _oa = sys.modules["openai_agents"]
elif importlib.util.find_spec("openai_agents"):
    _oa = importlib.import_module("openai_agents")
else:  # pragma: no cover - optional fallback
    _oa = None

if _oa is None or not all(hasattr(_oa, attr) for attr in ("Agent", "OpenAIAgent", "Tool")):
    from alpha_factory_v1.demos.self_healing_repo.agent_core import llm_client

    def Tool(*_a, **_kw):  # type: ignore
        def _decorator(func):
            return func

        return _decorator

    class OpenAIAgent:  # type: ignore
        def __init__(self, *_, **__):
            pass

        def __call__(self, prompt: str) -> str:
            return llm_client.call_local_model([{"role": "user", "content": prompt}])

    class Agent:  # type: ignore
        def __init__(self, llm=None, tools=None, name=None) -> None:
            self.llm = llm
            self.tools = tools or []
            self.name = name

else:
    Agent = _oa.Agent
    OpenAIAgent = _oa.OpenAIAgent
    Tool = _oa.Tool


def _patcher():
    from alpha_factory_v1.demos.self_healing_repo import patcher_core

    return patcher_core

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

if shutil.which("patch") is None:
    logger.error(
        '`patch` command not found. Install the utility, e.g., "sudo apt-get update && sudo apt-get install -y patch"'
    )
    sys.exit(1)


GRADIO_SHARE = os.getenv("GRADIO_SHARE", "0") == "1"

REPO_URL = "https://github.com/MontrealAI/sample_broken_calc.git"
LOCAL_REPO = pathlib.Path(__file__).resolve().parent / "sample_broken_calc"
CLONE_DIR = os.getenv("CLONE_DIR", "/tmp/demo_repo")


def clone_sample_repo() -> None:
    """Clone the example repo, falling back to the bundled copy."""
    result = subprocess.run(["git", "clone", REPO_URL, CLONE_DIR], capture_output=True)
    if result.returncode != 0:
        if LOCAL_REPO.exists():
            shutil.copytree(LOCAL_REPO, CLONE_DIR)
        else:
            result.check_returncode()


# ── LLM bridge ────────────────────────────────────────────────────────────────
_temp_env = os.getenv("TEMPERATURE")


def _build_llm():
    model = os.getenv("OPENAI_MODEL") or os.getenv("MODEL_NAME") or "gpt-4o-mini"
    api_key = os.getenv("OPENAI_API_KEY", None)
    base_url = "http://ollama:11434/v1" if not api_key else None
    temperature = float(_temp_env) if _temp_env is not None else None
    try:
        return OpenAIAgent(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
        )
    except TypeError:
        try:
            return OpenAIAgent()
        except Exception:
            return lambda _prompt: ""


LLM = _build_llm()


@Tool(name="run_tests", description="execute pytest on repo")
async def run_tests():
    """Run the project's tests with a timeout and no color codes."""
    try:
        result = subprocess.run(
            ["pytest", "-q", "--color=no"],
            cwd=CLONE_DIR,
            capture_output=True,
            text=True,
            timeout=300,
        )
        rc = result.returncode
        out = result.stdout + result.stderr
    except subprocess.TimeoutExpired as exc:
        rc = 1
        out = f"Test run timed out after {exc.timeout} seconds."
    return {"rc": rc, "out": out}


@Tool(name="suggest_patch", description="propose code fix")
async def suggest_patch():
    report = await run_tests()
    patcher_core = _patcher()
    patch = patcher_core.generate_patch(report["out"], llm=LLM, repo_path=CLONE_DIR)
    return {"patch": patch}


@Tool(name="apply_and_test", description="apply patch & retest")
async def apply_and_test(patch: str):
    patcher_core = _patcher()
    patcher_core.apply_patch(patch, repo_path=CLONE_DIR)
    return await run_tests()


apply_patch_and_retst = apply_and_test

# ── Agent orchestration ───────────────────────────────────────────────────────
agent = Agent(llm=LLM, tools=[run_tests, suggest_patch, apply_and_test], name="Repo‑Healer")


def create_app() -> FastAPI:
    """Build the Gradio UI and mount it on a FastAPI app."""
    with gr.Blocks(title="Self‑Healing Repo") as ui:
        log = gr.Markdown("# Output log\n")

        async def run_pipeline() -> str:
            if pathlib.Path(CLONE_DIR).exists():
                shutil.rmtree(CLONE_DIR)
            clone_sample_repo()
            out1 = await run_tests()
            patch = (await suggest_patch())["patch"]
            out2 = await apply_and_test(patch)
            log_text = "### Initial test failure\n```\n" + out1["out"] + "```"
            log_text += "\n### Proposed patch\n```diff\n" + patch + "```"
            log_text += "\n### Re‑test output\n```\n" + out2["out"] + "```"
            return log_text

        run_btn = gr.Button("🩹 Heal Repository")
        run_btn.click(run_pipeline, outputs=log)

    app = FastAPI()

    @app.get("/__live", response_class=PlainTextResponse, include_in_schema=False)
    async def _live() -> str:  # noqa: D401
        return "OK"

    return gr.mount_gradio_app(app, ui, path="/")


async def launch_gradio() -> None:
    app = create_app()
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=7863, loop="asyncio"))
    await server.serve()


if __name__ == "__main__":
    asyncio.run(launch_gradio())
