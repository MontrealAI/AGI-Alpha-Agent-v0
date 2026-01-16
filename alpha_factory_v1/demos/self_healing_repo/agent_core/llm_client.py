# SPDX-License-Identifier: Apache-2.0
# llm_client.py
"""LLM interface for generating patch suggestions."""
import asyncio
import logging
import os
import openai

logger = logging.getLogger(__name__)

# Load config from env or default
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-0613")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"

# Timeout (seconds) for OpenAI API requests
OPENAI_TIMEOUT_SEC = int(os.getenv("OPENAI_TIMEOUT_SEC", "30"))


def call_local_model(prompt_messages: list[dict[str, str]]) -> str:
    """Return a response from a locally hosted model."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "mixtral-8x7b")

    try:
        from openai_agents import OpenAIAgent
    except Exception:  # openai_agents missing, fall back to direct HTTP call
        url = f"{base_url}/chat/completions"
        payload = {"model": model, "messages": prompt_messages}
        try:  # prefer httpx if installed
            import httpx

            response = httpx.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception:
            import af_requests as requests

            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

        return str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))

    agent = OpenAIAgent(model=model, api_key=None, base_url=base_url)
    prompt = "\n".join(f"{m['role']}: {m['content']}" for m in prompt_messages)
    result = agent(prompt)
    if asyncio.iscoroutine(result):
        return str(asyncio.run(result))
    return str(result)


def build_prompt(error_log: str, code_dir: str) -> list[dict[str, str]]:
    """Construct the prompt for the LLM based on the error log (and optional code context)."""
    # We include a system prompt to instruct the assistant to only output a diff.
    system_msg = (
        "You are an AI developer assistant. A software test has failed, and your task is to suggest a fix. "
        "You will be given an error log and possibly some code snippets. "
        "Provide a unified diff patch that fixes the issue, and nothing else. "
        "The diff should be in unified format (starting with filenames '+++')."
    )
    user_msg = "The following test failed with this error:\n```\n" + error_log + "\n```\n"
    user_msg += "Please propose a fix as a patch (unified diff) that would resolve this error."
    # Optionally, we could attach relevant code context (like the file and line indicated in error_log).
    # For example, if error_log mentions a file and line, we can read a few lines around that and include in prompt.
    code_context = extract_code_context(error_log, code_dir)
    if code_context:
        user_msg += "\n\nRelevant Code Context:\n```python\n" + code_context + "\n```"
    return [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}]


def extract_code_context(error_log: str, code_dir: str) -> str:
    """Optional: find file path and line number in error_log and retrieve surrounding code."""
    # Simplistic implementation: search for patterns like 'File "path/to/file.py", line X'
    import re

    m = re.search(r"File \"(.+\.py)\", line (\d+)", error_log)
    if m:
        file_path = os.path.join(code_dir, m.group(1))
        line_no = int(m.group(2))
        if os.path.exists(file_path):
            lines = open(file_path).read().splitlines()
            start = max(0, line_no - 5)
            end = min(len(lines), line_no + 5)
            snippet = "\n".join(lines[start:end])
            return f"...\n{snippet}\n..."
    return ""


def request_patch(prompt_messages: list[dict[str, str]]) -> str:
    """Call the LLM (OpenAI or local) to get a patch suggestion."""
    if USE_LOCAL_LLM or not OPENAI_API_KEY:
        return call_local_model(prompt_messages)
    openai.api_key = OPENAI_API_KEY
    # Use function calling to ensure output is a diff via a "function"
    functions = [
        {
            "name": "propose_patch",
            "description": "Return a unified diff patch as a fix.",
            "parameters": {
                "type": "object",
                "properties": {"diff": {"type": "string", "description": "Unified diff patch."}},
                "required": ["diff"],
            },
        }
    ]
    try:
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=prompt_messages,
            functions=functions,
            function_call={"name": "propose_patch"},
            timeout=OPENAI_TIMEOUT_SEC,
        )
    except openai.Error as exc:  # pragma: no cover - API error handling
        logger.error("OpenAI API request failed: %s", exc)
        return ""
    except Exception as exc:  # pragma: no cover - generic safety net
        logger.error("Unexpected error contacting OpenAI: %s", exc)
        return ""
    # If the model decided to call the function:
    choices = response.get("choices", [])
    if choices and choices[0].get("finish_reason") == "function_call":
        # The model is requesting to call a function (e.g., could integrate tools if needed)
        func_call = choices[0]["message"]["function_call"]
        if func_call["name"] == "propose_patch":
            # This means model returned a function call with diff content
            diff_content = func_call["arguments"].get("diff")
            if diff_content:
                return str(diff_content)
    # Otherwise, the model might have directly given an answer
    text = str(choices[0]["message"].get("content", ""))
    return text or ""


def summarize_error(log: str) -> str:
    """Return a short summary of the failure log."""
    first_line = next((ln.strip() for ln in log.splitlines() if ln.strip()), "")
    return first_line[:80]


def _slugify(text: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return re.sub(r"-+", "-", slug).strip("-")


def generate_branch_name(log: str) -> str:
    """Create a slugified branch name from the error summary."""
    slug = _slugify(summarize_error(log))
    return (slug[:30].rstrip("-")) or "auto-fix"
