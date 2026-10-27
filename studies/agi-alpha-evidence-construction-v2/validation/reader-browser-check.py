from pathlib import Path
from playwright.sync_api import sync_playwright
from datetime import datetime,timezone
import hashlib,json
root=Path('/workspace/scratch/9738c9c6b885')
study=root/'alpha-research/studies/agi-alpha-evidence-construction-v2'
source=study/'web/index.html';out=root/'connected-reader-qa'
report={'schema':'full-reader-qa/v1','utc':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'views':[],'errors':[],'checks':[]}
def check(name,ok):
 report['checks'].append({'name':name,'passed':bool(ok)})
 if not ok:raise AssertionError(name)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 for js in [True,False]:
  page=browser.new_page(viewport={'width':1440,'height':1000},java_script_enabled=js)
  page.on('pageerror',lambda e:report['errors'].append(str(e)))
  page.emulate_media(reduced_motion='reduce')
  page.goto(source.as_uri(),wait_until='load')
  for width in [390,768,1440]:
   page.set_viewport_size({'width':width,'height':1000})
   check(f'{width}/{js}: no document overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
   check(f'{width}/{js}: six actual tables',page.locator('table').count()==6)
   check(f'{width}/{js}: three figures loaded',page.locator('figure img').count()==3 and page.locator('figure img').evaluate_all('(xs)=>xs.every(x=>x.complete&&x.naturalWidth>0)'))
   check(f'{width}/{js}: equations rendered MathML',page.locator('math').count()==8 and page.locator('math[display=block]').count()==2)
   check(f'{width}/{js}: complete adjudication text',all(x in page.locator('body').inner_text() for x in ['175.698','236.061','235.150','14.4','v1.1','8.68']))
   page.evaluate('window.scrollTo(0,0)')
   page.screenshot(path=str(out/f'{width}-js{int(js)}-top.png'))
   if width in [390,1440]:
    page.locator('table').nth(4).scroll_into_view_if_needed()
    page.screenshot(path=str(out/f'{width}-js{int(js)}-assay.png'))
   report['views'].append({'width':width,'javascript':js,'tables':page.locator('table').count(),'math_elements':page.locator('math').count()})
  anchors=page.locator('a[href]').evaluate_all('(xs)=>xs.map(x=>x.getAttribute("href"))')
  local=[h for h in anchors if not h.startswith(('http:','https:','mailto:','#','data:'))]
  check(f'{js}: local resources exist',all((source.parent/h.split('#')[0]).exists() for h in local))
  ids=page.locator('[id]').evaluate_all('(xs)=>xs.map(x=>x.id)')
  check(f'{js}: internal anchors resolve',all(h[1:] in ids for h in anchors if h.startswith('#')))
  check(f'{js}: no external subresources',page.evaluate('performance.getEntriesByType("resource").every(x=>!/^https?:/.test(x.name))'))
  page.close()
 browser.close()
check('no browser errors',not report['errors'])
report['passed']=all(x['passed'] for x in report['checks'])
report['visual_inspection']='Screenshots generated; human/agent visual review recorded separately after inspection.'
(study/'validation/reader-qa.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'checks':len(report['checks']),'views':len(report['views'])}))
