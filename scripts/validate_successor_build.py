# SPDX-License-Identifier: Apache-2.0
"""Browser acceptance for the paired-project portable SUCCESSOR workshop."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, expect

from scripts.validate_ascension import inspect


def validate_workshop(browser: Browser, origin: str, output: Path, axe: str) -> dict[str, Any]:
    """Check offline export, real computations, responsive layouts and claim boundaries."""
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    errors: list[str] = []
    requests: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(origin + "successor/build/", wait_until="networkidle")
    page.on("request", lambda request: requests.append(request.url))
    expect(page.locator("#app")).to_be_visible()
    name = '</script><img src=x onerror="alert(1)">'
    page.locator("#name").fill(name)
    page.locator("#run").focus()
    page.keyboard.press("Enter")
    expect(page.locator("#checks")).to_have_text("6 / 6")
    expect(page.locator("#result-title")).to_have_text(name)
    expect(page.locator("#result-title img")).to_have_count(0)
    pack = json.loads(page.locator("#evidence").text_content() or "{}")
    assert len(pack["compilation"]["graph"]["nodes"]) == 21
    assert pack["admission"] == {"decision": "HOLD", "independentProof": False, "authority": [], "specialistASI": False}
    assert pack["settlement"]["spentBaseUnits"] == "0"
    page.locator("#larger").click()
    with page.expect_download() as download:
        page.locator("#save").click()
    portable = output.resolve() / "builder-offline.html"
    download.value.save_as(portable)
    assert portable.stat().st_size < 500_000
    assert not requests
    offline = browser.new_context(offline=True)
    local = offline.new_page()
    local.on("pageerror", lambda error: errors.append(str(error)))
    local.goto(portable.as_uri())
    expect(local.locator("#name")).to_have_value(name)
    expect(local.locator("#pack")).to_be_disabled()
    expect(local.locator("#status")).to_contain_text("historical")
    expect(local.locator("#larger")).to_have_attribute("aria-pressed", "true")
    expect(local.locator("html")).to_have_class("large")
    local.locator("#name").fill("Mon Atlas Ω")
    local.locator("#language").click()
    local.locator("#run").click()
    expect(local.locator("#checks")).to_have_text("6 / 6")
    expect(local.locator("html")).to_have_attribute("lang", "fr")
    with local.expect_download() as download:
        local.locator("#request").click()
    native_request = output / "builder-request-fr.json"
    download.value.save_as(native_request)
    assert json.loads(native_request.read_text())["language"] == "fr"
    local.locator("#language").click()
    expect(local.locator("#request")).to_be_disabled()
    local.locator("#language").click()
    local.locator("#run").click()
    expect(local.locator("#pack")).to_be_enabled()
    audits = []
    for width in (1440, 390, 320):
        local.set_viewport_size({"width": width, "height": 1000})
        local.locator("#portfolio details").first.locator("summary").click()
        local.locator("#contracts details").first.locator("summary").click()
        assert inspect(local, "document.documentElement.scrollWidth <= innerWidth + 1")
        inspect(local, axe + "; void 0")
        audit = inspect(
            local, "axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','best-practice']}})"
        )
        assert not audit["violations"], audit["violations"]
        audits.append({"width": width, "violations": []})
        local.screenshot(path=str(output / f"builder-{width}.png"), full_page=True)
    local.locator("#events").select_option("4000")
    expect(local.locator("#pack")).to_be_disabled()
    local.locator("#run").click()
    expect(local.locator("#pack")).to_be_enabled()
    local.locator("#rollback").click()
    expect(local.locator("#pack")).to_be_disabled()
    expect(local.locator("#evidence")).to_contain_text("BASELINE_RETAINED")
    unsupported = browser.new_context(offline=True)
    unsupported.add_init_script("Object.defineProperty(globalThis.crypto,'randomUUID',{value:undefined})")
    limited = unsupported.new_page()
    limited.goto(portable.as_uri())
    expect(limited.locator("#run")).to_be_disabled()
    expect(limited.locator("#status")).to_contain_text("Web Crypto")
    unsupported.close()
    assert not errors, errors
    context.close()
    offline.close()
    return {"passed": True, "workOrders": 21, "checks": 6, "offline": True, "accessibility": audits}
