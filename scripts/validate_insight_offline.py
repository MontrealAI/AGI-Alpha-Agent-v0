#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require the real Insight build to load and reload through its service worker."""

from __future__ import annotations

import argparse
from functools import partial
import http.server
import json
from pathlib import Path
import threading
import time

from playwright.sync_api import sync_playwright

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--model", action="store_true", help="Require real local ONNX text generation online and offline"
    )
    args = parser.parse_args()
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(http.server.SimpleHTTPRequestHandler, directory=str(args.dist.resolve()))
    )
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}/index.html"
    errors: list[str] = []
    console_errors: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context()
            page = context.new_page()
            session = context.new_cdp_session(page)

            def evaluate(expression: str):  # type: ignore[no-untyped-def]
                # DevTools introspection must not require weakening the page's CSP.
                result = session.send(
                    "Runtime.evaluate",
                    {
                        "expression": expression,
                        "returnByValue": True,
                        "awaitPromise": True,
                        "allowUnsafeEvalBlockedByCSP": True,
                    },
                )
                assert "exceptionDetails" not in result, result
                return result["result"].get("value")

            def wait(expression: str) -> None:
                deadline = time.monotonic() + 60
                while not evaluate(expression):
                    if time.monotonic() > deadline:
                        raise TimeoutError(expression)
                    page.wait_for_timeout(100)

            page.on("pageerror", lambda error: errors.append(error.stack or str(error)))
            page.on(
                "console",
                lambda message: console_errors.append(message.text) if message.type in {"error", "warning"} else None,
            )
            page.goto(url)
            wait("typeof window.PYODIDE_WASM_BASE64 === 'string' && window.PYODIDE_WASM_BASE64.length > 0")
            wait("navigator.serviceWorker.controller !== null")
            simulation_advanced = (
                "Array.from(document.querySelectorAll('#canvas svg text')).some(node => "
                "Number((node.textContent.match(/^gen (\\d+)$/) || [])[1]) >= 2)"
            )
            wait(simulation_advanced)
            evaluate("caches.open('unrelated-application-cache').then(() => true)")
            generations = []
            page.route(
                "https://api.openai.com/v1/chat/completions",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body='{"choices":[{"message":{"content":"provider fixture"}}]}',
                ),
            )
            evaluate("window.setLlmApiKey('acceptance-fixture'); window.setLlmOffline(false)")
            assert evaluate("localStorage.getItem('OPENAI_API_KEY')") is None
            assert evaluate("window.llmChat('fixture')") == "provider fixture"
            page.unroute("https://api.openai.com/v1/chat/completions")
            page.route("https://api.openai.com/v1/chat/completions", lambda route: route.fulfill(status=503))
            assert "HTTP 503" in evaluate("window.llmChat('fixture').catch(error => error.message)")
            evaluate("window.setLlmApiKey(''); window.setLlmOffline(true)")
            page.unroute("https://api.openai.com/v1/chat/completions")
            if args.model:
                evaluate("window.setLlmOffline(true)")
                page.locator("#power-panel summary").click()
                page.locator("#llm-prompt").fill("The capital of France is")
                page.locator("#llm-generate").click()
                deadline = time.monotonic() + 180
                while page.locator("#llm-generate").is_disabled():
                    if time.monotonic() > deadline:
                        raise TimeoutError("Browser text generation did not complete")
                    page.wait_for_timeout(200)
                generations.append(page.locator("#llm-output").inner_text())
                assert isinstance(generations[-1], str) and generations[-1].strip()
                assert not generations[-1].startswith(("[offline]", "Local model unavailable", "Local model returned"))
                assert evaluate("window.LLM_BACKEND") == "wasm-simd"
                wait(
                    "caches.match(new URL('assets/local-llm/models/gpt2/onnx/model_quantized.onnx', "
                    "location.href).href).then(Boolean)"
                )
            context.set_offline(True)
            response = page.reload()
            assert response and response.ok and response.from_service_worker
            wait("typeof window.PYODIDE_WASM_BASE64 === 'string' && window.PYODIDE_WASM_BASE64.length > 0")
            wait(simulation_advanced)
            assert page.locator("#controls").is_visible()
            assert evaluate("typeof window.d3 !== 'undefined'")
            assert evaluate("fetch('style.css').then(response => response.ok)")
            assert evaluate("fetch('assets/src/i18n/en.json').then(response => response.ok)")
            assert "unrelated-application-cache" in evaluate("caches.keys()")
            if args.model:
                evaluate("window.setLlmOffline(true)")
                generations.append(evaluate("window.llmChat('The capital of France is')"))
                assert generations[0] == generations[1], generations
            assert not errors, errors
            evidence = {
                "passed": True,
                "offline_document_from_service_worker": True,
                "checks": [
                    "application initialized",
                    "embedded WASM",
                    "D3",
                    "styles",
                    "translations",
                    "unrelated cache preserved",
                    "sandboxed simulation advances online and offline",
                ],
                "page_errors": errors,
                "local_model_generations": generations,
                "local_model_verified": args.model,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(evidence, indent=2) + "\n")
            browser.close()
    except Exception:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        failure = {"passed": False, "page_errors": errors, "console_errors": console_errors}
        args.output.write_text(json.dumps(failure, indent=2) + "\n")
        print(json.dumps(failure))
        raise
    finally:
        server.shutdown()
        worker.join()
        server.server_close()
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
