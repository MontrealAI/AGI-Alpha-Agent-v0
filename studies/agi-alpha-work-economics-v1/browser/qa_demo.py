#!/usr/bin/env python3
"""Focused offline validation of the deliverable, downloads, and responsive UI."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / 'qa'
OUT.mkdir(exist_ok=True)
(OUT / 'downloads').mkdir(exist_ok=True)
checks = []
errors = []
requests = []

def check(name, condition, actual=None):
    checks.append({'name': name, 'passed': bool(condition), 'actual': actual})

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

with sync_playwright() as p:
    executable = os.environ.get('WORK_ECONOMICS_CHROMIUM')
    options = {'executable_path': executable} if executable else {}
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'], **options)
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True, offline=True)
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: requests.append(request.url) if request.url.startswith(('http://', 'https://')) else None)
    page.goto((HERE / 'AGI_ALPHA_Work_Economics_Demo.html').as_uri())
    page.get_by_text('Prepare the store catalog exception package', exact=True).wait_for()
    check('Standalone file loads with browser networking offline', True)
    page.screenshot(path=str(OUT / 'desktop-opening.png'), full_page=True)
    page.locator('#compare').click()
    page.wait_for_selector('#local-results:not([hidden])')
    metrics = page.evaluate('window.__workEconomicsDemo.active.result.metrics')
    check('Store catalog exact result', metrics['matchedPairs'] == 4 and metrics['unmatchedRows'] == 2 and metrics['fieldDifferences'] == 2, metrics)
    page.locator('#local-results').scroll_into_view_if_needed()
    page.screenshot(path=str(OUT / 'desktop-result.png'))
    with page.expect_download() as promise:
        page.locator('[data-download=workspace]').click()
    workspace_path = OUT / 'downloads/store-workspace.json'
    promise.value.save_as(workspace_path)
    workspace = json.loads(workspace_path.read_text())
    check('Exact workspace preserves input and zero authority', workspace['input']['leftKey'] == 'sku' and workspace['authority'] == 'none')
    with page.expect_download() as promise:
        page.locator('[data-download=differences]').click()
    csv_path = OUT / 'downloads/store-differences.csv'
    promise.value.save_as(csv_path)
    rows = list(csv.DictReader(io.StringIO(csv_path.read_text())))
    check('Full difference export covers all four evidence rows', len(rows) == 4, len(rows))
    with page.expect_download() as promise:
        page.locator('#download-tool').click()
    tool_path = OUT / 'downloads/successor-tool.mjs'
    promise.value.save_as(tool_path)
    expected_tool = page.evaluate('window.__workEconomicsDemo.toolSha256')
    check('Retained tool download exactly matches recorded artifact', digest(tool_path) == expected_tool, digest(tool_path))
    page.locator('[data-sample=inventory]').click()
    page.locator('#compare').click()
    page.wait_for_selector('#local-results:not([hidden])')
    metrics = page.evaluate('window.__workEconomicsDemo.active.result.metrics')
    check('Changed inventory schema, duplicate pairs and exact identifiers', metrics['matchedPairs'] == 3 and metrics['unmatchedRows'] == 4 and metrics['fieldDifferences'] == 2 and metrics['leftDuplicates']['extraRows'] == 1, metrics)
    page.locator('#left-key').fill('sku')
    page.locator('#compare').click()
    page.wait_for_selector('#run-error:not([hidden])')
    check('Invalid retained key refuses with no current artifact', 'Choose a key column present' in page.locator('#run-error').inner_text() and page.evaluate('window.__workEconomicsDemo.active === null'))
    page.locator('[data-sample=public]').click()
    page.locator('#compare').click()
    page.wait_for_selector('#local-results:not([hidden])')
    metrics = page.evaluate('window.__workEconomicsDemo.active.result.metrics')
    check('Public recorded inputs actually recompute', metrics['leftRows'] == 135 and metrics['rightRows'] == 135 and metrics['matchedPairs'] == 135 and metrics['fieldDifferences'] == 16 and metrics['unmatchedRows'] == 0, metrics)
    with page.expect_download() as promise:
        page.locator('[data-download=summary]').click()
    summary_path = OUT / 'downloads/public-summary.html'
    promise.value.save_as(summary_path)
    check('Readable summary contains full evidence and source commitments', '<table>' in summary_path.read_text() and 'SHA-256' in summary_path.read_text())
    page.locator('#workspace-upload').set_input_files(str(workspace_path))
    page.get_by_text('HISTORICAL WORKSPACE · RECOMPUTED', exact=True).wait_for()
    check('Saved workspace recomputes and is labeled historical', 'HISTORICAL' in page.locator('#local-status-tag').inner_text() and page.evaluate('window.__workEconomicsDemo.active.result.metrics.matchedPairs') == 4)
    corrupt = json.loads(json.dumps(workspace))
    corrupt['result']['metrics']['matchedPairs'] += 1
    corrupt_path = OUT / 'downloads/corrupt-workspace.json'
    corrupt_path.write_text(json.dumps(corrupt))
    page.locator('#workspace-upload').set_input_files(str(corrupt_path))
    page.wait_for_selector('#run-error:not([hidden])')
    check('Corrupt saved workspace refuses recomputation', 'saved results differ' in page.locator('#run-error').inner_text() and page.evaluate('window.__workEconomicsDemo.active === null'))
    page.locator('#tab-local').focus()
    page.keyboard.press('ArrowRight')
    check('Keyboard arrow selects recorded-study tab', page.locator('#tab-study').get_attribute('aria-selected') == 'true')
    check('Study shows measured acceptance and three scale rows', '36 / 36' in page.locator('#study-metrics').inner_text() and page.locator('#scale-table tr').count() == 3)
    page.evaluate('window.scrollTo(0, 0)')
    page.screenshot(path=str(OUT / 'desktop-study.png'), full_page=True)
    with page.expect_download() as promise:
        page.locator('#recorded-delivery').click()
    delivery_path = OUT / 'downloads/recorded-delivery.zip'
    promise.value.save_as(delivery_path)
    check('Recorded delivery download preserves exact archive', digest(delivery_path) == digest(HERE.parent / 'raw/showcase/delivery.zip'))
    page.locator('#tab-economics').click()
    check('Default scenario arithmetic is transparent and correct', page.locator('#human-cost').inner_text() == '$26.32' and page.locator('#system-cost').inner_text() == '$6.49' and page.locator('#break-even').inner_text() == '7.4 min', {'human': page.locator('#human-cost').inner_text(), 'system': page.locator('#system-cost').inner_text(), 'break_even': page.locator('#break-even').inner_text()})
    page.locator('#human-acceptance').fill('0')
    check('Zero acceptance assumption is rejected', page.locator('#economics-error').is_visible() and page.locator('#human-cost').inner_text() == 'Check assumptions')
    page.locator('#human-acceptance').fill('95')
    page.evaluate('window.scrollTo(0, 0)')
    page.screenshot(path=str(OUT / 'desktop-economics.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    for mode in ['local', 'study', 'economics']:
        page.locator('#tab-' + mode).click()
        if mode == 'local':
            page.locator('[data-sample=catalog]').click()
            page.locator('#compare').click()
            page.wait_for_selector('#local-results:not([hidden])')
        dimensions = page.evaluate('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
        check('No page-wide horizontal overflow at 390 px: ' + mode, dimensions['document'] <= dimensions['viewport'], dimensions)
        page.evaluate('window.scrollTo(0, 0)')
        page.screenshot(path=str(OUT / ('mobile-' + mode + '.png')), full_page=True)
    check('No JavaScript page errors', len(errors) == 0, errors)
    check('No external network requests', len(requests) == 0, requests)
    browser.close()

report = {'status': 'PASS' if all(c['passed'] for c in checks) else 'FAIL', 'checks': checks,
          'passed': sum(c['passed'] for c in checks), 'total': len(checks),
          'pageErrors': errors, 'externalRequests': requests,
          'htmlSha256': digest(HERE / 'AGI_ALPHA_Work_Economics_Demo.html'),
          'scope': 'Offline Chromium, source computations, downloaded bytes, keyboard tab interaction, arithmetic, corruption refusal, and 1440/390-pixel layout. This is product QA, not a business-job experiment.'}
(OUT / 'QA_REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'passed': report['passed'], 'total': report['total']}, indent=2))
raise SystemExit(0 if report['status'] == 'PASS' else 1)
