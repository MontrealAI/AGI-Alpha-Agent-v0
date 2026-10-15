# SPDX-License-Identifier: Apache-2.0
"""Exercise local-only discovery, evidence boundaries, recovery and EN/FR continuity."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import threading

from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def watch_page(page: Page, origin: str, errors: list[str], external: list[str]) -> None:
    """Capture failures and unexpected requests in every fresh browser context."""
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: external.append(request.url) if not request.url.startswith(origin) else None)


def assert_accessible(page: Page, state: str) -> None:
    """Run the CI-provided axe bundle against each visible journey state."""
    axe = os.environ.get("AXE_SCRIPT")
    if not axe:
        return
    # Production intentionally has a hash-only CSP, so inject the trusted test bundle via evaluate.
    if not page.evaluate("typeof window.axe !== 'undefined'"):
        page.evaluate(Path(axe).read_text())
    violations = page.evaluate(
        "async () => (await axe.run(document, "
        "{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations"
    )
    assert not violations, f"{state}: {json.dumps(violations)}"


def form_snapshot(page: Page) -> list[dict]:
    """Include hidden steps and exact raw values, without depending on translated labels."""
    return page.locator("#editor input, #editor textarea, #editor select").evaluate_all(
        "elements => elements.map(el => ({id: el.id, value: el.value, "
        "...(el.type === 'checkbox' ? {checked: el.checked} : {})}))"
    )


def assert_step(page: Page, step: int) -> None:
    """Only the current beginner step is exposed; the summary remains available."""
    assert page.locator("#journey-summary").is_visible()
    for index, selector in enumerate(("#mission", "#baseline", "#metrics", "#analyze")):
        assert page.locator(selector).is_visible() == (index == step), (step, selector)
    assert page.locator("#changed").is_visible() == (step == 0)
    assert page.locator("#add-evidence").is_visible() == (step == 0)
    assert page.locator("#constraints").is_visible() == (step == 1)
    assert page.locator("#show-all").get_attribute("aria-pressed") == "false"


def record_state(page: Page, screenshots: Path, name: str) -> None:
    """Retain responsive screenshots and check accessibility at the same state."""
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), name
    assert_accessible(page, name)
    page.screenshot(path=str(screenshots / f"{name}.png"), full_page=True)


def download_draft(page: Page) -> tuple[bytes, dict]:
    """Drafts can be saved before an analyzable proposal exists."""
    with page.expect_download() as download:
        page.locator("#save-draft").click()
    raw = Path(download.value.path()).read_bytes()
    draft = json.loads(raw)
    assert draft["schema"] == "alpha-discovery-draft/v1"
    assert draft["state"] == "partial-unvalidated"
    assert draft["authority"] == "none"
    assert "analysis" not in draft
    assert "handoff" not in draft
    assert page.locator("#result").is_hidden()
    assert page.locator("#export").is_disabled()
    return raw, draft


def restore_file(page: Page, raw: bytes, name: str = "draft.json") -> None:
    page.locator("#restore").set_input_files({"name": name, "mimeType": "application/json", "buffer": raw})


def exercise_beginner_journey(
    browser: Browser, origin: str, screenshots: Path, errors: list[str], external: list[str]
) -> None:
    """Cover partial recovery, keyboard editing, progression and EN/FR without the example shortcut."""
    for language in ("en", "fr"):
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        watch_page(page, origin, errors, external)
        page.goto(f"{origin}successor/discover/")
        if language == "fr":
            page.locator("#language").click()
        assert page.locator("html").get_attribute("lang") == language
        assert_step(page, 0)
        assert page.locator("#ledger > fieldset").count() == 0
        record_state(page, screenshots, f"beginner-{language}-empty")
        initial_height = page.locator("#mission").evaluate("el => el.clientHeight")
        mission = "Partial mission / Mission inachevée\n" + "A visible line of context.\n" * 12
        page.locator("#mission").fill(mission)
        page.locator("#changed").fill("A new observation, with uncertainty / Une observation encore incertaine")
        assert page.locator("#mission").evaluate("el => el.clientHeight") > initial_height
        assert page.locator("#mission").evaluate("el => el.scrollHeight <= el.clientHeight + 2")
        page.locator("#add-evidence").click()
        page.locator("#e-0-claim").fill("A lesson worth retaining / Une leçon à conserver")
        page.locator("#e-0-reference").fill("Public source; conditions and date still to be checked.")
        support = page.locator("fieldset#e-0-supports")
        assert support.locator('input[type="checkbox"]').count() == 4
        candidate = support.locator('input[value="candidate"]')
        assert not candidate.is_checked()
        # Real keyboard interaction must support multiple options without Ctrl/Command selection.
        candidate.focus()
        page.keyboard.press("Space")
        assert candidate.is_checked()
        page.keyboard.press("Space")
        assert not candidate.is_checked()
        for option in ("baseline", "alternative", "change"):
            page.keyboard.press("Tab")
            checkbox = support.locator(f'input[value="{option}"]')
            assert checkbox.evaluate("el => el === document.activeElement")
            page.keyboard.press("Space")
            assert checkbox.is_checked()
        assert support.locator("input:checked").evaluate_all("els => els.map(el => el.value)") == [
            "baseline",
            "alternative",
            "change",
        ]
        starting_values = form_snapshot(page)
        # Language changes translate the UI without replacing values, checkbox choices, or the active step.
        page.locator("#language").click()
        assert form_snapshot(page) == starting_values
        assert_step(page, 0)
        page.locator("#language").click()
        assert page.locator("html").get_attribute("lang") == language
        assert form_snapshot(page) == starting_values
        raw_start, start = download_draft(page)
        assert start["language"] == language and start["step"] == 0
        assert start["input"]["mission"] == mission
        assert start["input"]["baseline"] == ""
        assert start["input"]["constraints"][0]["name"] == ""
        assert start["input"]["metrics"][0]["candidate"]["value"] == ""
        record_state(page, screenshots, f"beginner-{language}-step-1")

        page.locator("#journey-next").click()
        assert_step(page, 1)
        for field, value in (
            ("baseline", "Keep the current method / Conserver la méthode actuelle"),
            ("alternative", "A credible existing option / Une alternative crédible"),
            ("candidate", "A hypothesis to investigate / Une hypothèse à explorer"),
        ):
            page.locator(f"#{field}").fill(value)
        record_state(page, screenshots, f"beginner-{language}-step-2")
        page.locator("#journey-next").click()
        assert_step(page, 2)
        record_state(page, screenshots, f"beginner-{language}-step-3-collapsed")
        for summary in page.locator("#metrics details > summary").all():
            summary.click()
        page.locator("#m-0-unit").fill("cycles, conditions pending / conditions à définir")
        # Preserve half-entered and invalid numbers verbatim in drafts, without treating them as a proposal.
        page.locator("#m-0-minimumGain").fill("")
        page.locator("#m-0-candidate-value").fill("1.5")
        page.locator("#m-0-candidate-reference").fill("An unfinished source note.\n" * 10)
        assert page.locator("#m-0-candidate-reference").evaluate("el => el.scrollHeight <= el.clientHeight + 2")
        record_state(page, screenshots, f"beginner-{language}-step-3-expanded")
        page.evaluate("document.documentElement.style.zoom = 2")
        record_state(page, screenshots, f"beginner-{language}-expanded-200-percent")
        page.evaluate("document.documentElement.style.zoom = 1")
        unfinished_values = form_snapshot(page)
        raw, draft = download_draft(page)
        assert draft["step"] == 2 and draft["language"] == language
        assert draft["input"]["metrics"][0]["minimumGain"] == ""
        assert draft["input"]["metrics"][0]["candidate"]["value"] == "1.5"

        page.locator("#journey-next").click()
        assert_step(page, 3)
        assert form_snapshot(page) == unfinished_values
        record_state(page, screenshots, f"beginner-{language}-step-4")
        for step in (2, 1, 0):
            page.locator("#journey-back").click()
            assert_step(page, step)
            assert form_snapshot(page) == unfinished_values
        # Summary edit links provide a second route back without clearing the retained answers.
        for step in (2, 1, 3, 0):
            page.locator(f"#edit-step-{step}").click()
            assert_step(page, step)
            assert form_snapshot(page) == unfinished_values
        page.locator("#show-all").click()
        assert page.locator("#show-all").get_attribute("aria-pressed") == "true"
        for selector in ("#mission", "#baseline", "#metrics", "#analyze", "#journey-summary"):
            assert page.locator(selector).is_visible()
        assert form_snapshot(page) == unfinished_values
        record_state(page, screenshots, f"beginner-{language}-show-all")
        page.locator("#show-all").click()
        assert_step(page, 0)
        assert form_snapshot(page) == unfinished_values

        # Restore the earliest partial draft in an entirely fresh context, with no local storage history.
        recovery = browser.new_context(viewport={"width": 375, "height": 812})
        phone = recovery.new_page()
        watch_page(phone, origin, errors, external)
        phone.goto(page.url)
        restore_file(phone, raw_start)
        phone.wait_for_function("value => document.querySelector('#mission').value === value", arg=mission)
        assert phone.locator("html").get_attribute("lang") == language
        assert_step(phone, 0)
        assert form_snapshot(phone) == starting_values
        assert phone.locator("#result").is_hidden()
        assert phone.locator("#export").is_disabled()
        record_state(phone, screenshots, f"beginner-mobile-{language}-restored-step-1")
        restore_file(phone, raw, "unfinished-metric.json")
        phone.wait_for_function("document.querySelector('#m-0-candidate-value').value === '1.5'")
        assert_step(phone, 2)
        assert form_snapshot(phone) == unfinished_values
        assert phone.locator("html").get_attribute("lang") == language
        for summary in phone.locator("#metrics details > summary").all():
            summary.click()
        record_state(phone, screenshots, f"beginner-mobile-{language}-expanded-metrics")
        phone.evaluate("document.documentElement.style.zoom = 2")
        record_state(phone, screenshots, f"beginner-mobile-{language}-expanded-200-percent")
        phone.evaluate("document.documentElement.style.zoom = 1")
        for step in (1, 0):
            phone.locator("#journey-back").click()
            assert_step(phone, step)
            assert form_snapshot(phone) == unfinished_values
            record_state(phone, screenshots, f"beginner-mobile-{language}-step-{step + 1}")
        for step in (1, 2, 3):
            phone.locator("#journey-next").click()
            assert_step(phone, step)
            assert form_snapshot(phone) == unfinished_values
        record_state(phone, screenshots, f"beginner-mobile-{language}-step-4")
        phone.locator("#analyze").click()
        assert phone.locator("#error").is_visible()
        assert_step(phone, 1)
        assert phone.locator("#rights").evaluate("el => el === document.activeElement")
        assert phone.locator("#result").is_hidden()
        assert phone.locator("#export").is_disabled()
        phone.locator("#edit-step-0").click()

        # Draft import shares the strict parser and fatal UTF-8 boundary used by completed proposals.
        duplicate = raw.replace(b"{", b'{"schema":"alpha-discovery-draft/v1",', 1)
        malformed = raw.replace(b"Partial mission", b"Partial \xffission", 1)
        assert malformed != raw
        for name, invalid in (("duplicate-key.json", duplicate), ("invalid-utf8.json", malformed)):
            phone.locator("#changed").fill(name)  # Clear the earlier validation error before the import.
            preserved = form_snapshot(phone)
            restore_file(phone, invalid, name)
            phone.wait_for_function("!document.querySelector('#error').hidden")
            assert form_snapshot(phone) == preserved
            assert phone.locator("html").get_attribute("lang") == language
            assert_step(phone, 0)

        # A delayed partial draft must not overwrite a newer edit, including language and journey position.
        phone.evaluate(
            """() => { const original = File.prototype.arrayBuffer; window.pendingImports = [];
              File.prototype.arrayBuffer = function() { const file = this;
                return new Promise(resolve => {
                  window.pendingImports.push(async () => resolve(await original.call(file)));
                });
              };
            }"""
        )
        restore_file(phone, raw, "interrupted-draft.json")
        phone.wait_for_function("window.pendingImports.length === 1")
        phone.locator("#changed").fill("Newer partial edit must survive / Modification plus récente")
        preserved = form_snapshot(phone)
        phone.evaluate("window.pendingImports[0]()")
        phone.wait_for_function("!document.querySelector('#error').hidden")
        assert form_snapshot(phone) == preserved
        assert phone.locator("html").get_attribute("lang") == language
        assert_step(phone, 0)

        # Language-only and navigation-only changes are also newer user intent, even without a field edit.
        phone.locator("#changed").fill("Language switch must survive / Le choix de langue doit rester")
        restore_file(phone, raw, "language-interrupted-draft.json")
        phone.wait_for_function("window.pendingImports.length === 2")
        phone.locator("#language").click()
        switched_language = "fr" if language == "en" else "en"
        preserved = form_snapshot(phone)
        phone.evaluate("window.pendingImports[1]()")
        phone.wait_for_function("!document.querySelector('#error').hidden")
        assert phone.locator("html").get_attribute("lang") == switched_language
        assert form_snapshot(phone) == preserved
        assert_step(phone, 0)
        phone.locator("#language").click()
        phone.locator("#changed").fill("Newer navigation must survive / La navigation récente doit rester")
        restore_file(phone, raw, "navigation-interrupted-draft.json")
        phone.wait_for_function("window.pendingImports.length === 3")
        phone.locator("#journey-next").click()
        preserved = form_snapshot(phone)
        phone.evaluate("window.pendingImports[2]()")
        phone.wait_for_function("!document.querySelector('#error').hidden")
        assert_step(phone, 1)
        assert phone.locator("html").get_attribute("lang") == language
        assert form_snapshot(phone) == preserved

        # The import epoch also rejects an older file finishing after a newer draft has been restored.
        newer = json.loads(raw_start)
        newer["input"]["mission"] = "Newest file wins / Le dernier fichier prévaut"
        newer["language"] = "fr" if language == "en" else "en"
        newer["step"] = 1
        restore_file(phone, raw, "older-draft.json")
        phone.wait_for_function("window.pendingImports.length === 4")
        restore_file(phone, json.dumps(newer).encode(), "newer-draft.json")
        phone.wait_for_function("window.pendingImports.length === 5")
        phone.evaluate("window.pendingImports[4]()")
        phone.wait_for_function(
            "value => document.querySelector('#mission').value === value", arg=newer["input"]["mission"]
        )
        imported_values = form_snapshot(phone)
        assert_step(phone, 1)
        assert phone.locator("html").get_attribute("lang") == newer["language"]
        phone.evaluate("window.pendingImports[3]()")
        assert form_snapshot(phone) == imported_values
        assert_step(phone, 1)
        assert phone.locator("html").get_attribute("lang") == newer["language"]
        assert phone.locator("#error").is_hidden()
        assert phone.locator("#result").is_hidden()
        assert phone.locator("#export").is_disabled()
        recovery.close()
        context.close()


def exercise_completed_transitions(browser: Browser, origin: str, errors: list[str], external: list[str]) -> None:
    """Preserve valid proposals across UI-only changes and reveal collapsed invalid fields for correction."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    watch_page(page, origin, errors, external)
    page.goto(f"{origin}successor/discover/")
    for control in ("#language", "#language", "#edit-step-0", "#show-all"):
        page.locator("#example").click()
        page.locator("#analyze").click()
        page.locator("#result").wait_for(state="visible")
        assert page.locator("#export").is_enabled()
        preserved = form_snapshot(page)
        preserved_brief = page.locator("#inspection").text_content()
        previous_language = page.locator("html").get_attribute("lang")
        page.locator(control).click()
        assert page.locator("#result").is_visible(), control
        assert page.locator("#export").is_enabled(), control
        assert form_snapshot(page) == preserved, control
        assert page.locator("#inspection").text_content() == preserved_brief, control
        if control == "#language":
            translated = "fr" if previous_language == "en" else "en"
            assert page.locator("html").get_attribute("lang") == translated
            assert ("pas encore" if translated == "fr" else "not yet") in page.locator("#decision").text_content()
        if control == "#show-all":
            page.locator(control).click()
            assert page.locator("#show-all").get_attribute("aria-pressed") == "true"
            assert page.locator("#result").is_visible()
            assert page.locator("#export").is_enabled()
            assert form_snapshot(page) == preserved
            assert page.locator("#inspection").text_content() == preserved_brief

    # Back and Continue change presentation only; unchanged inputs retain the valid computed proposal.
    page.locator("#example").click()
    page.locator("#show-all").click()
    page.locator("#edit-step-3").click()
    assert_step(page, 3)
    page.locator("#analyze").click()
    page.locator("#result").wait_for(state="visible")
    assert page.locator("#export").is_enabled()
    preserved = form_snapshot(page)
    preserved_brief = page.locator("#inspection").text_content()
    for control, step in (("#journey-back", 2), ("#journey-next", 3)):
        page.locator(control).click()
        assert_step(page, step)
        assert page.locator("#result").is_visible(), control
        assert page.locator("#export").is_enabled(), control
        assert form_snapshot(page) == preserved, control
        assert page.locator("#inspection").text_content() == preserved_brief, control

    # Missing fields inside closed comparison details must become visible before focus moves to them.
    for field, progressive in (("unit", False), ("minimumGain", True)):
        page.locator("#example").click()
        metric = page.locator("#metrics details").first
        assert not metric.evaluate("el => el.open")
        metric.locator("summary").click()
        missing = page.locator(f"#m-0-{field}")
        missing.fill("")
        metric.locator("summary").click()
        assert not metric.evaluate("el => el.open")
        if progressive:
            page.locator("#show-all").click()
            page.locator("#edit-step-3").click()
            assert_step(page, 3)
        preserved = form_snapshot(page)
        page.locator("#analyze").click()
        assert page.locator("#error").is_visible()
        assert metric.evaluate("el => el.open")
        assert missing.is_visible()
        assert missing.evaluate("el => el === document.activeElement")
        assert page.locator("#result").is_hidden()
        assert page.locator("#export").is_disabled()
        assert form_snapshot(page) == preserved
        if progressive:
            assert_step(page, 2)
        assert_accessible(page, f"missing-collapsed-metric-{field}")
    context.close()


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / "docs")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            executable = os.environ.get("CHROMIUM_EXECUTABLE")
            browser = p.chromium.launch(**({"executable_path": executable} if executable else {}))
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors, external = [], []
            screenshots = Path(os.environ.get("DISCOVERY_SCREENSHOTS", "/tmp/alpha-discovery-screenshots"))
            screenshots.mkdir(parents=True, exist_ok=True)
            origin = f"http://127.0.0.1:{server.server_port}/"
            exercise_beginner_journey(browser, origin, screenshots, errors, external)
            exercise_completed_transitions(browser, origin, errors, external)
            watch_page(page, origin, errors, external)
            page.goto(f"{origin}successor/discover/")
            page.locator("#example").click()
            assert page.locator("#show-all").get_attribute("aria-pressed") == "true"
            page.locator("#analyze").click()
            page.locator("#result").wait_for(state="visible")
            assert "not yet" in page.locator("#decision").text_content()
            assert "qualified reviewer" in page.locator("#experiment").text_content()
            assert page.locator("#hypotheses article").count() == 3
            page.screenshot(path=str(screenshots / "desktop-en.png"), full_page=True)
            with page.expect_download() as download:
                page.locator("#export").click()
            original = Path(download.value.path()).read_bytes()
            brief = json.loads(original)
            assert brief["analysis"]["independentProof"] is False
            assert brief["handoff"]["authority"] == "none"
            assert "not physical validation" in brief["handoff"]["gym"]["simulationLimits"]
            page.locator("#changed").fill("Changed input <script>alert(1)</script>")
            assert page.locator("#result").is_hidden()
            assert page.locator("#export").is_disabled()
            page.locator("#language").click()
            assert page.locator("#changed").input_value() == "Changed input <script>alert(1)</script>"
            assert page.locator("html").get_attribute("lang") == "fr"
            page.locator("#analyze").click()
            page.locator("#result").wait_for(state="visible")
            assert "pas encore" in page.locator("#decision").text_content()
            page.screenshot(path=str(screenshots / "desktop-fr.png"), full_page=True)
            page.evaluate("document.documentElement.style.zoom = 2")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(screenshots / "desktop-fr-200-percent.png"), full_page=True)
            page.evaluate("document.documentElement.style.zoom = 1")
            assert page.locator("#hypotheses script").count() == 0
            # Fresh context imports only inputs, never a claimed result or authority.
            brief["analysis"]["decision"] = "certified"
            brief["handoff"]["authority"] = "execute"
            context = browser.new_context(viewport={"width": 375, "height": 812})
            phone = context.new_page()
            watch_page(phone, origin, errors, external)
            phone.goto(page.url)
            phone.locator("#restore").set_input_files(
                {"name": "brief.json", "mimeType": "application/json", "buffer": json.dumps(brief).encode()}
            )
            phone.wait_for_function("document.querySelector('#mission').value.includes('battery')")
            assert phone.locator("#show-all").get_attribute("aria-pressed") == "true"
            assert phone.locator("#result").is_hidden()
            phone.locator("#analyze").click()
            phone.locator("#result").wait_for(state="visible")
            assert '"authority": "none"' in phone.locator("#inspection").text_content()
            assert phone.evaluate("document.documentElement.scrollWidth <= innerWidth")
            phone.screenshot(path=str(screenshots / "mobile-en.png"), full_page=True)
            phone.locator("#metrics details").first.locator("summary").click()
            phone.locator("#m-0-candidate-value").fill("1.5")
            phone.locator("#analyze").click()
            assert phone.locator("#error").is_visible()
            assert phone.locator("#result").is_hidden()
            phone.locator("#example").click()
            phone.locator("#c-0-status").select_option("reported-fail")
            phone.locator("#analyze").click()
            phone.locator("#result").wait_for(state="visible")
            assert "Keep the incumbent" in phone.locator("#decision").text_content()
            # Invalid UTF-8 is rejected rather than silently rewritten into replacement characters.
            malformed = original.replace(b"A longer-lasting", b"A \xffonger-lasting", 1)
            assert malformed != original
            preserved = phone.locator("#mission").input_value()
            phone.locator("#restore").set_input_files(
                {"name": "malformed.json", "mimeType": "application/json", "buffer": malformed}
            )
            phone.wait_for_function("!document.querySelector('#error').hidden")
            assert phone.locator("#mission").input_value() == preserved
            # Interrupted file reading cannot overwrite newer user input.
            phone.evaluate(
                """() => { const original = File.prototype.arrayBuffer;
              File.prototype.arrayBuffer = function() { const file = this;
                return new Promise(resolve => {
                  window.finishImport = async () => resolve(await original.call(file));
                }); };
            }"""
            )
            phone.locator("#restore").set_input_files(
                {"name": "slow.json", "mimeType": "application/json", "buffer": original}
            )
            phone.wait_for_function("typeof window.finishImport === 'function'")
            phone.locator("#changed").fill("Newer edit must survive")
            phone.evaluate("window.finishImport()")
            phone.wait_for_function("!document.querySelector('#error').hidden")
            assert phone.locator("#changed").input_value() == "Newer edit must survive"
            assert phone.locator("#result").is_hidden()
            phone.locator("#example").click()
            phone.locator("#language").click()
            phone.locator("#analyze").click()
            phone.locator("#result").wait_for(state="visible")
            phone.screenshot(path=str(screenshots / "mobile-fr.png"), full_page=True)
            assert_accessible(phone, "completed-proposal-mobile-fr")
            screenshot = os.environ.get("DISCOVERY_SCREENSHOT")
            if screenshot:
                page.locator("#language").click()
                page.locator("#analyze").click()
                page.locator("#result").wait_for(state="visible")
                page.screenshot(path=screenshot, full_page=True)
            assert errors == [], errors
            assert external == [], external
            browser.close()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
