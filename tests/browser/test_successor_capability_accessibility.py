# SPDX-License-Identifier: Apache-2.0
"""Review Axe incompletes using semantic checks and conservative composited contrast bounds."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(os.environ.get("CAPABILITY_ACCESSIBILITY_ROOT", str(Path(__file__).resolve().parents[2])))
OUTPUT = Path(os.environ.get("CAPABILITY_ACCESSIBILITY_EVIDENCE", "/tmp/capability-accessibility-review"))
AXE = Path(
    os.environ.get(
        "AXE_SCRIPT", str(Path(__file__).resolve().parents[2] / "tests/browser/node_modules/axe-core/axe.min.js")
    )
)
COLORS = re.compile(r"rgba?\(([^)]+)\)")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: object) -> None:
        """Keep fixture traffic out of the retained verification log."""


def rgba(text: str) -> list[float]:
    """Parse the computed RGB form emitted by the pinned Chromium browser."""
    match = COLORS.fullmatch(text)
    assert match, f"Unreviewed computed color: {text}"
    parts = [float(part) for part in re.split(r"[, /]+", match[1].strip())]
    assert len(parts) in (3, 4)
    return parts if len(parts) == 4 else parts + [1]


def composite_bounds(
    lower: list[float], upper: list[float], colors: list[list[float]]
) -> tuple[list[float], list[float]]:
    """Enclose every RGB stop interpolation and alpha composition, including transparent stops."""
    alpha = [min(color[3] for color in colors), max(color[3] for color in colors)]
    result = []
    for index in range(3):
        components = [min(color[index] for color in colors), max(color[index] for color in colors)]
        values = [c * a + b * (1 - a) for c in components for a in alpha for b in (lower[index], upper[index])]
        result.append((min(values), max(values)))
    return [item[0] for item in result], [item[1] for item in result]


def luminance(rgb: list[float]) -> float:
    """Use WCAG relative luminance with the sRGB transfer function."""
    linear = [
        channel / 255 / 12.92 if channel / 255 <= 0.04045 else ((channel / 255 + 0.055) / 1.055) ** 2.4
        for channel in rgb
    ]
    return sum(a * b for a, b in zip(linear, [0.2126, 0.7152, 0.0722], strict=True))


def contrast_bound(styles: dict[str, Any]) -> dict[str, Any]:
    """Prove a lower bound over all gradient positions instead of sampling favorable pixels."""
    lower, upper = [255.0] * 3, [255.0] * 3
    for layer in reversed(styles["backgrounds"]):
        assert float(layer["opacity"]) == 1, "Active group opacity needs a separate compositing review."
        lower, upper = composite_bounds(lower, upper, [rgba(layer["color"])])
        image = layer["image"]
        if image != "none":
            # Fail closed for additional images, stacked gradients and modern color functions. Each reviewed
            # layer has one legacy-sRGB gradient; trailing `none` is emitted by Chromium for body backgrounds.
            simplified = COLORS.sub("COLOR", image)
            assert re.fullmatch(
                r"(?:linear|radial)-gradient\([^()]*\)(?:,\s*none)*", simplified
            ), f"Unreviewed background layers or color space: {image}"
            assert " in " not in image, f"Explicit interpolation needs a separate review: {image}"
            stops = [rgba(match.group()) for match in COLORS.finditer(image)]
            assert stops, f"No computed gradient stops: {image}"
            lower, upper = composite_bounds(lower, upper, stops)
    foreground = rgba(styles["color"])
    foreground_lower, foreground_upper = composite_bounds(lower, upper, [foreground])
    bg_low, bg_high = luminance(lower), luminance(upper)
    fg_low, fg_high = luminance(foreground_lower), luminance(foreground_upper)
    bound = (
        (fg_low + 0.05) / (bg_high + 0.05)
        if fg_low >= bg_high
        else ((bg_low + 0.05) / (fg_high + 0.05) if fg_high <= bg_low else 1.0)
    )
    large = float(styles["fontSize"].removesuffix("px")) >= 24 or (
        float(styles["fontSize"].removesuffix("px")) >= 18.666666 and int(styles["fontWeight"]) >= 700
    )
    return {
        "minimumRatio": bound,
        "requiredRatio": 3 if large else 4.5,
        "foreground": styles["color"],
        "backgroundRGBLower": lower,
        "backgroundRGBUpper": upper,
        "method": "Conservative RGB interval over computed gradient stops and alpha-composited ancestor backgrounds.",
    }


STYLE_REVIEW = """element => {
    const style = getComputedStyle(element);
    const backgrounds = [];
    for (let node = element; node; node = node.parentElement) {
        const item = getComputedStyle(node);
        backgrounds.push({tag: node.tagName, id: node.id, color: item.backgroundColor,
            image: item.backgroundImage, opacity: item.opacity});
    }
    return {color: style.color, fontSize: style.fontSize, fontWeight: style.fontWeight, backgrounds,
        decorative: Boolean(element.closest('[aria-hidden="true"]')),
        disabled: Boolean(element.closest(':disabled, [aria-disabled="true"]')),
        tag: element.tagName, type: element.type || null,
        label: element.labels ? [...element.labels].map(label => label.textContent.trim()).join(' ') : null,
        scrollWidth: element.scrollWidth, clientWidth: element.clientWidth,
        scrollHeight: element.scrollHeight, clientHeight: element.clientHeight};
}"""


def inspect(page: Page, name: str) -> dict[str, Any]:
    """Retain raw results and resolve each current incomplete rather than treating it as passing."""
    page.evaluate(AXE.read_text())
    audit: dict[str, Any] = page.evaluate(
        "async () => await axe.run(document, {runOnly: {type:'tag', values:"
        "['wcag2a','wcag2aa','wcag21aa','best-practice']}})"
    )
    (OUTPUT / f"axe-{name}.json").write_text(json.dumps(audit, indent=2))
    assert not audit["violations"], [(item["id"], item["nodes"]) for item in audit["violations"]]
    reviewed = []
    for result in audit["incomplete"]:
        assert result["id"] == "color-contrast", f"Unresolved semantic incomplete: {result['id']}"
        for node in result["nodes"]:
            assert len(node["target"]) == 1 and isinstance(node["target"][0], str)
            selector = node["target"][0]
            styles = page.locator(selector).evaluate(STYLE_REVIEW)
            reasons = [
                check.get("data", {}).get("messageKey") for group in ("any", "all", "none") for check in node[group]
            ]
            record = {"selector": selector, "reasons": reasons, "styles": styles}
            if styles["decorative"]:
                record[
                    "resolution"
                ] = "Decorative, aria-hidden symbol; an adjacent accessible label conveys its meaning."
            elif styles["disabled"]:
                record[
                    "resolution"
                ] = "Inactive native control is exempt from WCAG 1.4.3 contrast; its associated label remains checked."
            else:
                bound = contrast_bound(styles)
                record["contrast"] = bound
                assert bound["minimumRatio"] >= bound["requiredRatio"], (selector, bound)
                record["resolution"] = "Contrast verified over the full conservative background range."
                if "elmPartiallyObscured" in reasons:
                    assert styles["tag"] in ("INPUT", "TEXTAREA", "SELECT", "PRE"), (selector, styles)
                    if styles["tag"] == "PRE":
                        expect(page.locator(selector)).to_have_attribute("role", "group")
                        assert page.locator(selector).get_attribute("aria-label")
                        record["resolution"] += " Named report group is focusable and scrollable."
                    else:
                        assert styles["label"], f"Clipped native control needs an associated label: {selector}"
                        record["resolution"] += " Native control has a separate visible associated label."
            reviewed.append(record)
    for selector in (
        "#development-report",
        "#heldout-report",
        "#history-json",
        "#evolve-program",
        "#evolve-history-json",
    ):
        if page.locator(selector).count():
            expect(page.locator(selector)).to_have_attribute("role", "group")
    for report in page.locator("pre[aria-label]").all():
        expect(report).to_have_attribute("role", "group")
    if page.locator(".evolve-result").count():
        expect(page.locator(".evolve-result")).to_have_attribute("role", "group")
    (OUTPUT / f"review-{name}.json").write_text(json.dumps(reviewed, indent=2))
    ratios = [item["contrast"]["minimumRatio"] for item in reviewed if "contrast" in item]
    return {
        "state": name,
        "incompleteRules": [item["id"] for item in audit["incomplete"]],
        "reviewedNodes": len(reviewed),
        "minimumConservativeContrast": min(ratios) if ratios else None,
        "violations": len(audit["violations"]),
        "reviewedContrast": len(ratios),
    }


def main() -> None:
    """Check initial, generated report and mobile states, retaining the manual-review evidence."""
    assert abs(luminance([255, 255, 255]) - 1) < 1e-12
    assert luminance([0, 0, 0]) == 0
    assert (luminance([255, 255, 255]) + 0.05) / (luminance([0, 0, 0]) + 0.05) == 21
    OUTPUT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"http://127.0.0.1:{server.server_port}/docs/successor/capabilities/index.html")
            expect(page.locator("#witness-enabled")).to_be_enabled()
            page.keyboard.press("Tab")
            expect(page.locator(".skip")).to_be_focused()
            results.append(inspect(page, "initial"))
            page.locator(".hero").screenshot(path=str(OUTPUT / "initial-hero.png"))
            if page.locator("#evolve-construct").count():
                page.locator("#evolve-budget").fill("1")
                page.locator("#evolve-construct").click()
                expect(page.locator("#evolve-construct")).to_be_enabled(timeout=120000)
                expect(page.locator("#evolve-status")).to_contain_text("within budget")
                page.locator("#evolve-budget").fill("100000")
                page.locator("#evolve-construct").click()
                expect(page.locator("#evolve-construct")).to_be_enabled(timeout=120000)
                expect(page.locator("#evolve-status")).to_contain_text("Capability qualified.")
                page.locator("#evolve-reuse").click()
                expect(page.locator("#evolve-construct")).to_be_enabled(timeout=120000)
                expect(page.locator("#evolve-status")).to_contain_text("Frozen-package reuse: PASS")
                page.locator("#evolve-successor").click()
                expect(page.locator("#evolve-construct")).to_be_enabled(timeout=120000)
                expect(page.locator("#evolve-status")).to_contain_text("Scope-expanding successor: PASS")
                page.evaluate("document.querySelectorAll('details').forEach(item => { item.open = true; })")
                results.append(inspect(page, "out-evolve-successor-reports"))
                page.locator("#out-evolve").screenshot(path=str(OUTPUT / "out-evolve-successor-reports.png"))
            page.locator("#witness-enabled").check()
            page.locator("#public-confirmation").check()
            page.locator("#freeze").click()
            page.locator("#development").click()
            expect(page.locator("#development-state")).to_contain_text("Computed PASS")
            page.locator("#heldout").click()
            expect(page.locator("#heldout-state")).to_contain_text("Computed PASS")
            page.evaluate("document.querySelectorAll('details').forEach(item => { item.open = true; })")
            results.append(inspect(page, "all-reports-open"))
            page.get_by_role("group", name="Full development report", exact=True).focus()
            expect(page.locator("#development-report")).to_be_focused()
            page.keyboard.press("PageDown")
            scroll_script = """async element => {
                    for (let frame = 0; frame < 60 && element.scrollTop === 0; frame++) {
                        await new Promise(requestAnimationFrame);
                    }
                    return {scrollTop: element.scrollTop, scrollHeight: element.scrollHeight,
                        clientHeight: element.clientHeight, focused: element === document.activeElement};
                }"""
            scroll = page.locator("#development-report").evaluate(scroll_script)
            (OUTPUT / "keyboard-report-scroll.json").write_text(json.dumps(scroll, indent=2))
            assert scroll["scrollTop"] > 0, scroll
            page.locator(".evidence-panel").screenshot(path=str(OUTPUT / "named-report-keyboard-scroll.png"))
            page.locator("#brief-unmetNeed").focus()
            page.keyboard.press("Control+End")
            assert page.locator("#brief-unmetNeed").evaluate("element => element.selectionEnd === element.value.length")
            page.set_viewport_size({"width": 390, "height": 1000})
            page.evaluate("document.documentElement.style.fontSize='200%'")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            results.append(inspect(page, "mobile-200-text"))
            page.locator("#brief-form").screenshot(path=str(OUTPUT / "mobile-200-labelled-controls.png"))
            if page.locator("#out-evolve").count():
                page.locator("#out-evolve").screenshot(path=str(OUTPUT / "mobile-200-out-evolve.png"))
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    manifest = ROOT / "docs/successor/capabilities/sources.json"
    report = {
        "status": "PASS",
        "states": results,
        "source": json.loads(manifest.read_text()),
        "pageSHA256": hashlib.sha256((manifest.parent / "index.html").read_bytes()).hexdigest(),
        "harnessSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "Reviewed reported ARIA/contrast incompletes in these Chromium states; not full WCAG conformance.",
        "manualReviewRequired": "Inspect screenshots, contrast bounds, keyboard scrolling and named groups.",
    }
    (OUTPUT / "summary.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"status": report["status"], "states": results, "scope": report["scope"]}))


if __name__ == "__main__":
    main()
