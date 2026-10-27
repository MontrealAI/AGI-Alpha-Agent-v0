from playwright.sync_api import sync_playwright
from pathlib import Path
import hashlib,json,datetime
root=Path('/workspace/scratch/9738c9c6b885')
study=root/'alpha-research/studies/agi-alpha-evidence-construction-v2'
source=study/'web/demo.html';out=root/'connected-demo-qa'
report={'schema':'demo-browser-qa/v1','reviewed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'browser':'Playwright Chromium local file','views':[],'assertions':[],'page_errors':[],'console_errors':[],'request_failures':[],'screenshots':[]}
def check(name,passed):
 report['assertions'].append({'name':name,'passed':bool(passed)})
 if not passed:raise AssertionError(name)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
 page.on('pageerror',lambda error:report['page_errors'].append(str(error)))
 page.on('console',lambda msg:report['console_errors'].append(msg.text) if msg.type=='error' else None)
 page.on('requestfailed',lambda request:report['request_failures'].append({'url':request.url,'failure':request.failure}))
 page.emulate_media(reduced_motion='reduce')
 page.goto(source.as_uri(),wait_until='load')
 check('Four panels',page.locator('[role=tabpanel]').count()==4)
 check('All French translation keys present',page.evaluate('Object.keys(translations.en).every(k=>typeof translations.fr[k]==="string")'))
 for width in [390,768,1440]:
  page.set_viewport_size({'width':width,'height':900})
  for lang in ['en','fr']:
   page.locator('#'+lang).click()
   check(f'{width}/{lang}: HTML language follows choice',page.locator('html').get_attribute('lang')==lang)
   for panel in range(4):
    page.locator('#tab'+str(panel)).click()
    visible=page.locator('[role=tabpanel]:visible')
    overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth')
    check(f'{width}/{lang}/panel{panel}: one visible selected panel',visible.count()==1 and visible.get_attribute('id')=='panel'+str(panel) and page.locator('#tab'+str(panel)).get_attribute('aria-selected')=='true')
    check(f'{width}/{lang}/panel{panel}: no page overflow',not overflow)
    f=out/f'{width}-{lang}-panel{panel}.png'
    page.screenshot(path=str(f),full_page=True)
    report['screenshots'].append(str(f))
    report['views'].append({'width':width,'language':lang,'panel':panel,'overflow':overflow,'document_width':page.evaluate('document.documentElement.scrollWidth')})
 page.set_viewport_size({'width':1440,'height':1000})
 for lang in ['en','fr']:
  page.locator('#'+lang).click();page.locator('#tab1').click()
  text=page.locator('#recipientStatus').inner_text()
  check(f'{lang}: completed 20/20 adjudication no pending copy',text.count('20/20')==3 and 'pending' not in text.lower() and 'en cours' not in text.lower())
  page.locator('#branchB').click()
  check(f'{lang}: supplementary branch interval',page.locator('#intervalRange').inner_text()=='[7.5005852, 7.5205852]')
  check(f'{lang}: supplementary cell counts',page.locator('#branchCounts').inner_text()=='49 · 50 · 46 · 41')
  page.locator('#branchA').click()
  check(f'{lang}: main branch interval',page.locator('#intervalRange').inner_text()=='[7.6485684, 7.6678788]')
  page.locator('#tab2').click()
  expected={'success':568.35,'one-default':42.01,'withdrawal':161.34,'common-failure':-751.74,'partial-delivery':-39.24,'payment-delay':317.01,'support-overrun':129.51,'no-transfer-gain':192.03,'negative-transfer':129.51}
  for key,value in expected.items():
   page.locator('#scenario').select_option(key)
   text=page.locator('#cashProfit').inner_text()
   digits=''.join(c for c in text if c.isdigit() or c in '.,-').replace(',','.')
   check(f'{lang}: saved cash scenario {key}',abs(float(digits)-value)<0.001)
  page.locator('#scenario').select_option('success')
  check(f'{lang}: optional coordination distinction present','20' in page.locator('[data-i=coordinationScope]').inner_text())
  check(f'{lang}: v1 cash and v1.1 capacity distinction present','v1.1' in page.locator('[data-i=cashSource]').inner_text())
  page.locator('#tab3').click()
  check(f'{lang}: four-use and two-use thresholds distinct',all(v in page.locator('[data-i=retainText]').inner_text() for v in (['7.2','14.4'] if lang=='en' else ['7,2','14,4'])))
  page.locator('#saving').focus();page.keyboard.press('End')
  page.locator('#uses').focus();page.keyboard.press('Home')
  check(f'{lang}: keyboard slider endpoints',page.locator('#saving').input_value()=='40' and page.locator('#uses').input_value()=='1')
  check(f'{lang}: positive one-use retention result','23.33' in page.locator('#retentionNet').inner_text() if lang=='en' else '23,33' in page.locator('#retentionNet').inner_text())
  check(f'{lang}: urgent56 total includes support','56' in page.locator('#urgentStatus').inner_text())
  page.locator('#saving').focus();page.keyboard.press('Home')
  page.locator('#uses').focus();page.keyboard.press('End')
  check(f'{lang}: negative transfer slider remains negative',page.locator('#saving').input_value()=='-10' and 'bad' in page.locator('#retentionNet').get_attribute('class'))
  check(f'{lang}: negative transfer urgent106','106' in page.locator('#urgentStatus').inner_text())
  page.evaluate("document.getElementById('saving').value=20;document.getElementById('saving').dispatchEvent(new Event('input'));document.getElementById('uses').value=2;document.getElementById('uses').dispatchEvent(new Event('input'))")
  check(f'{lang}: two-use dynamic threshold',('14.40' if lang=='en' else '14,40') in page.locator('#retentionRule').inner_text())
  page.locator('#tab0').focus();page.keyboard.press('ArrowRight')
  check(f'{lang}: right arrow tab navigation',page.locator('#tab1').get_attribute('aria-selected')=='true')
  page.keyboard.press('End')
  check(f'{lang}: end key tab navigation',page.locator('#tab3').get_attribute('aria-selected')=='true')
  page.keyboard.press('Home')
  check(f'{lang}: home key tab navigation',page.locator('#tab0').get_attribute('aria-selected')=='true')
  page.locator('#next').click()
  check(f'{lang}: next navigation',page.locator('#tab1').get_attribute('aria-selected')=='true')
  page.locator('#previous').click()
  check(f'{lang}: previous navigation',page.locator('#tab0').get_attribute('aria-selected')=='true')
 check('No JavaScript errors',not report['page_errors'])
 check('No console errors',not report['console_errors'])
 check('No failed requests',not report['request_failures'])
 check('No remote subresources requested',page.evaluate('performance.getEntriesByType("resource").every(x=>!/^https?:/.test(x.name))'))
 report['local_links']=[{'href':a.get_attribute('href'),'exists':(source.parent/a.get_attribute('href')).exists()} for a in page.locator('a[href]').all() if a.get_attribute('href') and not a.get_attribute('href').startswith(('http','#'))]
 browser.close()
report['corrected_findings']=[{'finding':'390px panel2 money-card min-content overflow','correction':'Smaller narrow-screen amount font and padding, minmax(0,1fr) columns; all 24 views passed after correction','initial_screenshot':str(out/'overflow-initial.png')},{'finding':'Adjudication pending text stale','correction':'Both languages now show all three 20/20 outcomes, actual artifact invocation and unpriced timing'},{'finding':'Four forecast versus two modeled fresh uses','correction':'Both 7.2 and 14.4 thresholds are explicit; optional20dollar coordination and separate v1/v1.1 scopes disclosed'}]
report['screenshot_motion']='Reduced motion enabled for stable final-state visual inspection; normal interaction behavior checked.'
report['passed']=all(x['passed'] for x in report['assertions'])
report['assertion_count']=len(report['assertions'])
(study/'validation/demo-qa.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['screenshots','views','assertions']},ensure_ascii=False,indent=2))
