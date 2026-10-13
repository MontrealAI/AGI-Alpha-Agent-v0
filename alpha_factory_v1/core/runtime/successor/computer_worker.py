# SPDX-License-Identifier: Apache-2.0
"""Fixed disposable browser worker. Run only inside the documented networkless container."""

from __future__ import annotations

import asyncio
import base64
import json
import sys
from typing import Any


def emit(value: dict[str, Any]) -> None:
    """Send bounded observations or requests to the parent, never browser console text."""
    print(json.dumps(value, ensure_ascii=True, separators=(",", ":")), flush=True)


async def main() -> None:
    """Read commands while servicing asynchronous, parent-mediated network requests."""
    from playwright.async_api import async_playwright

    commands: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=2)
    pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
    next_request = 0

    async def read() -> None:
        while True:
            line = await asyncio.to_thread(sys.stdin.buffer.readline, 3_000_001)
            if not line or len(line) > 3_000_000:
                raise ValueError("worker input ended or exceeded its bound")
            request = json.loads(line)
            if request.get("operation") == "fetched":
                future = pending.pop(request["id"])
                future.set_result(request)
            else:
                await commands.put(request)

    reader = asyncio.create_task(read())
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        context = await browser.new_context(
            viewport={"width": 1024, "height": 768}, accept_downloads=False, service_workers="block"
        )
        context.set_default_timeout(5000)

        async def route(handler: Any) -> None:
            nonlocal next_request
            next_request += 1
            ident = str(next_request)
            future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
            pending[ident] = future
            emit({"type": "fetch", "id": ident, "url": handler.request.url, "method": handler.request.method})
            response = await asyncio.wait_for(future, timeout=12)
            await handler.fulfill(
                status=response["status"],
                content_type=response["content_type"],
                body=base64.b64decode(response["body"], validate=True),
            )

        await context.route("**/*", route)
        await context.route_web_socket("**/*", lambda websocket: websocket.close())
        page = await context.new_page()
        page.on("dialog", lambda dialog: dialog.dismiss())
        context.on("page", lambda popup: popup.close())

        async def observe() -> None:
            png = await page.screenshot(type="png", animations="disabled", timeout=5000)
            if len(png) > 2_000_000:
                raise ValueError("screenshot exceeds byte budget")
            text = (await page.locator("body").inner_text(timeout=5000))[:100_000]
            emit({"type": "observation", "png": base64.b64encode(png).decode(), "text": text, "url": page.url})

        request = await asyncio.wait_for(commands.get(), timeout=10)
        if request.get("operation") != "start" or not isinstance(request.get("html"), str):
            raise ValueError("expected fixed initial HTML")
        await page.set_content(request["html"], wait_until="domcontentloaded", timeout=15_000)
        await observe()
        while True:
            request = await commands.get()
            if request.get("operation") != "act":
                raise ValueError("unknown worker command")
            action = request["action"]
            kind = action["type"]
            if kind == "click":
                await page.mouse.click(action["x"], action["y"], button=action["button"])
            elif kind == "double_click":
                await page.mouse.dblclick(action["x"], action["y"])
            elif kind == "move":
                await page.mouse.move(action["x"], action["y"])
            elif kind == "type":
                await page.keyboard.insert_text(action["text"])
            elif kind == "keypress":
                names = {
                    "CTRL": "Control",
                    "ENTER": "Enter",
                    "TAB": "Tab",
                    "ESC": "Escape",
                    "BACKSPACE": "Backspace",
                    "DELETE": "Delete",
                    "SPACE": "Space",
                    "UP": "ArrowUp",
                    "DOWN": "ArrowDown",
                    "LEFT": "ArrowLeft",
                    "RIGHT": "ArrowRight",
                    "HOME": "Home",
                    "END": "End",
                    "A": "a",
                }
                await page.keyboard.press("+".join(names[key] for key in action["keys"]))
            elif kind == "scroll":
                await page.mouse.move(action["x"], action["y"])
                await page.mouse.wheel(action["scroll_x"], action["scroll_y"])
            elif kind == "drag":
                path = action["path"]
                await page.mouse.move(path[0]["x"], path[0]["y"])
                await page.mouse.down()
                for point in path[1:]:
                    await page.mouse.move(point["x"], point["y"])
                await page.mouse.up()
            elif kind == "wait":
                await asyncio.sleep(0.5)
            elif kind != "screenshot":
                raise ValueError("unsupported worker action")
            await observe()
    reader.cancel()


if __name__ == "__main__":
    asyncio.run(main())
