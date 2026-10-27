"""Render and exercise the local bilingual research demonstration."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path('/workspace/scratch/a54a233bfad9/alpha/studies/agi-alpha-microscopy-transfer-v1')
output = Path('/workspace/scratch/a54a233bfad9/browser_qa')
output.mkdir(exist_ok=True)
report = {'page': 'browser/index.html', 'external_requests': [], 'console_errors': [], 'checks': []}

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
    page.on('pageerror', lambda error: report['console_errors'].append(str(error)))
    page.on('request', lambda request: report['external_requests'].append(request.url) if request.url.startswith(('http:', 'https:')) else None)
    page.goto((root / 'browser/index.html').as_uri())
    page.screenshot(path=str(output / 'desktop-en.png'), full_page=True)
    assert page.locator('#region option').count() == 61
    native = page.locator('#nativeVolume').inner_text()
    page.locator('#scale').fill('1.5')
    page.locator('#scale').dispatch_event('input')
    assert page.locator('#nativeVolume').inner_text() == native
    assert abs(float(page.locator('#mappedVolume').inner_text().replace(',', '')) / float(native.replace(',', '')) - 3.375) < .001
    report['checks'].append('Scenario changes mapped volume by scale cubed while native volume remains constant.')
    assert page.locator('#decision').inner_text().startswith('Justified stop')
    page.locator('#saved').fill('30')
    page.locator('#saved').dispatch_event('input')
    assert page.locator('#decision').inner_text().startswith('Candidate for retention')
    report['checks'].append('Retention scenario switches from justified stop to conditional candidate at positive assumed savings.')
    page.locator('#reset').click()
    assert page.locator('#scale').input_value() == '1'
    page.locator('#fr').click()
    assert page.locator('html').get_attribute('lang') == 'fr'
    assert 'Conserver la mesure' in page.locator('h1').inner_text()
    page.screenshot(path=str(output / 'desktop-fr.png'), full_page=True)
    for width, language in [(390, 'fr'), (390, 'en'), (768, 'en')]:
        page.set_viewport_size({'width': width, 'height': 844})
        page.locator('#' + language).click()
        page.screenshot(path=str(output / f'width-{width}-{language}.png'), full_page=True)
        overflow = page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
        
        if overflow:
            print(page.evaluate("({doc:document.documentElement.scrollWidth,body:document.body.scrollWidth,inner:innerWidth})"))
            print(page.evaluate("Array.from(document.querySelectorAll('body *')).filter(e => e.getBoundingClientRect().right>innerWidth).map(e=>({tag:e.tagName,cls:e.className,id:e.id,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right})).slice(0,30)"))
        assert not overflow, f'Horizontal overflow at {width}px in {language}'
        report['checks'].append(f'No horizontal overflow at {width}px in {language}.')
    assert not report['console_errors'], report['console_errors']
    assert not report['external_requests'], report['external_requests']
    report['checks'].append('No script errors or external network requests.')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.goto((root / 'browser/paper.html').as_uri())
    assert page.title() == 'AGI ALPHA FLYWHEEL — When Capability Creates Opportunity'
    assert page.locator('main').count() == 1
    assert page.locator('math').count() >= 10
    assert page.locator('img').count() == 4
    assert page.locator('img').evaluate_all('(items) => items.every(x => x.complete && x.naturalWidth > 0)')
    page.screenshot(path=str(output / 'reader-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    page.screenshot(path=str(output / 'reader-mobile.png'))
    report['reader'] = {'mathml_elements': page.locator('math').count(), 'embedded_figures': 4, 'desktop_and_mobile_rendered': True, 'horizontal_overflow': False}
    assert not report['console_errors']
    assert not report['external_requests']
    browser.close()

report['status'] = 'passed'
(output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
