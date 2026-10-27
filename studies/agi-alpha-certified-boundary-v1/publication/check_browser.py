# SPDX-License-Identifier: Apache-2.0
"""Read-only desktop/mobile browser QA of the self-contained local edition."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'qa_browser'
OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1360,'height':1000},device_scale_factor=1)
    errors=[];external=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('request',lambda request: external.append(request.url) if request.url.startswith(('http://','https://')) else None)
    page.goto((ROOT/'paper.html').as_uri(),wait_until='load')
    page.screenshot(path=str(OUT/'desktop_top.png'))
    title=page.title()
    body=page.locator('body').inner_text()
    math=page.locator('math').count()
    images=page.locator('img').evaluate_all('(els)=>els.map(e=>({loaded:e.complete&&e.naturalWidth>0,source:e.currentSrc.slice(0,30)}))')
    assert 'Certified Boundary Edition' in title
    assert '17902560' in body and '18258529' in body and math>50
    assert '$2,408' in body and '$6,573.20' in body and '19,968.80' in body
    assert 'conventional challenge' in body.lower() and 'actual revenue and receipts are zero' in body.lower()
    assert all(item['loaded'] for item in images) and len(images)==4
    assert not errors and not external
    page.get_by_role('heading',name='Complete profit, funding and adverse outcomes',exact=True).scroll_into_view_if_needed()
    page.screenshot(path=str(OUT/'desktop_economics.png'))
    page.get_by_role('heading',name='Appendix A. A universal piecewise-linear weight certificate',exact=True).scroll_into_view_if_needed()
    page.screenshot(path=str(OUT/'desktop_proof.png'))
    desktop_width=page.evaluate('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
    mobile=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
    mobile.goto((ROOT/'paper.html').as_uri(),wait_until='load')
    mobile.screenshot(path=str(OUT/'mobile_top.png'))
    mobile_width=mobile.evaluate('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
    assert mobile_width['document']<=mobile_width['viewport'], mobile_width
    result={'status':'PASS browser content, math, figures and offline-load assertions',
            'title':title,'mathml_elements':math,'loaded_figures':len(images),
            'outbound_http_requests':external,'javascript_errors':errors,
            'desktop_width':desktop_width,'mobile_width':mobile_width,
            'visual_inspection_required':['desktop_top.png','desktop_economics.png','desktop_proof.png','mobile_top.png']}
    (OUT/'browser_checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    browser.close()
