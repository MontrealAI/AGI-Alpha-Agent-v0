"""Replay mechanical acceptance. This is not a human study or autonomous-model trial."""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import json, re, hashlib, time, argparse, random, os, shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'03_Evidence'; DOWNLOADS=OUT/'browser_downloads'

def expected(config, service, n):
    s=next(x for x in config['catalog'] if x['id']==service)
    gross=Decimal(s['priceCents'])*n
    discount=(gross*Decimal(config['discountBps'])/10000).quantize(Decimal('1'),rounding=ROUND_HALF_UP) if n>=config['threshold'] else Decimal(0)
    return int(gross-discount)

def cents(text):
    return int(Decimal(re.sub(r'[^0-9.]','',text))*100)

def load(browser, html, width=1280):
    ctx=browser.new_context(viewport={'width':width,'height':900},accept_downloads=True)
    requests=[]
    ctx.route('http**/*',lambda r:(requests.append(r.request.url),r.abort())[1])
    page=ctx.new_page();page.set_default_timeout(1000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(html)
    return ctx,page,requests,errors

def run_task(browser, task, variant):
    cfg=json.loads((ROOT/f'02_Work_Products/Task_{task}/brief.json').read_text())
    source=ROOT/f'02_Work_Products/Task_{task}/{variant}/index.html'
    html=source.read_text();ctx,page,requests,errors=load(browser,html);results=[]
    def check(name,fn):
        start=time.perf_counter()
        try:
            data=fn();ok=bool(data[0]) if isinstance(data,tuple) else bool(data);detail=data[1] if isinstance(data,tuple) else data
        except Exception as e:ok=False;detail=f'{type(e).__name__}: {e}'.split('Call log:')[0][:500]
        results.append({'test':name,'passed':ok,'detail':detail,'elapsedMs':round((time.perf_counter()-start)*1000,2)})
    def exists(sel):return page.locator(sel).count()>0
    def quote(service,n):
        page.locator('#service').select_option(service);page.locator('#seats').fill(str(n));page.locator('#calculate').click()
        return cents(page.locator('#total').inner_text())
    def invalid(value, service=None):
        page.locator('#service').select_option(service or cfg['catalog'][0]['id']);page.locator('#seats').fill(str(value));page.locator('#calculate').click()
        return exists('#error') and bool(page.locator('#error').inner_text()) and page.locator('#quote').is_hidden()
    for width in [320,390,1440]:
        page.set_viewport_size({'width':width,'height':900})
        check(f'No horizontal overflow at {width}px',lambda:(page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),page.evaluate('({document:document.documentElement.scrollWidth,viewport:innerWidth})')))
    check('Header text does not overlap',lambda: page.evaluate("""()=>{const a=document.querySelector('h1').getBoundingClientRect(),p=document.querySelector('#intro')||document.querySelector('header p');const b=p.getBoundingClientRect();return a.bottom<=b.top||b.bottom<=a.top||a.right<=b.left||b.right<=a.left;}"""))
    check('Every supplied offering preserved',lambda:all(x['name']['en'] in page.locator('body').inner_text() for x in cfg['catalog']))
    check('Explicit language metadata',lambda:page.locator('html').get_attribute('lang')=='en')
    check('Both estimate inputs have labels',lambda:page.locator('label[for=service]').count()==1 and page.locator('label[for=seats]').count()==1)
    normal=next(x for x in cfg['catalog'] if x['priceCents']>0 and x['capacity']>=cfg['threshold'])
    for n,label in [(1,'One participant'),(cfg['threshold'],'Exact discount threshold'),(cfg['threshold']+1,'Above discount threshold'),(min(normal['capacity'],cfg['maximum']),'Maximum valid capacity')]:
        check(label+' exact total',lambda n=n:(quote(normal['id'],n)==expected(cfg,normal['id'],n),{'expectedCents':expected(cfg,normal['id'],n),'displayed':page.locator('#total').inner_text()}))
    for value,label in [('', 'empty'),('0','zero'),('-1','negative'),('1.5','fractional'),(str(cfg['maximum']+1),'over capacity')]:check('Reject '+label+' participants',lambda v=value:invalid(v))
    def language_test(width):
        if not exists('#language'):return False
        if page.locator('html').get_attribute('lang')!='fr':page.locator('#language').click()
        page.set_viewport_size({'width':width,'height':900})
        return page.locator('html').get_attribute('lang')=='fr' and cfg['title']['fr'] in page.locator('body').inner_text() and page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    check('French translation and 320px layout',lambda:language_test(320))
    check('French translation and 390px layout',lambda:language_test(390))
    if exists('#language') and page.locator('html').get_attribute('lang')=='fr':page.locator('#language').click()
    def enter():
        page.locator('#service').select_option(normal['id']);page.locator('#seats').fill('2');page.locator('#seats').press('Enter');return cents(page.locator('#total').inner_text())==expected(cfg,normal['id'],2)
    check('Keyboard Enter calculates',enter)
    def gate():
        quote(normal['id'],2);return exists('#download') and page.locator('#download').is_disabled()
    check('Download requires explicit review',gate)
    def stale():
        if not exists('#accept'):return False
        page.locator('#accept').check();page.locator('#seats').fill('3');return page.locator('#download').is_disabled() and not page.locator('#accept').is_checked()
    check('Input edit invalidates prior acceptance',stale)
    quote_path=DOWNLOADS/f'{task}_{variant}_quote.json'
    def download_quote():
        if not exists('#accept'):return False
        quote(normal['id'],cfg['threshold']);page.locator('#accept').check()
        with page.expect_download(timeout=3000) as d:page.locator('#download').click()
        d.value.save_as(quote_path);q=json.loads(quote_path.read_text());return q['totalCents']==expected(cfg,normal['id'],cfg['threshold']) and q['booking'] is False and q['externalAction'] is False
    check('Real downloaded quote matches independent oracle',download_quote)
    recovery_path=DOWNLOADS/f'{task}_{variant}_recovery.json'
    def save():
        if not exists('#save-draft'):return False
        with page.expect_download(timeout=3000) as d:page.locator('#save-draft').click()
        d.value.save_as(recovery_path);v=json.loads(recovery_path.read_text());return 'approval' not in v['state'] and v['state']['taskId']==cfg['taskId']
    check('Real recovery download excludes approval',save)
    def restore():
        if not recovery_path.exists():return False
        c,p,_,_=load(browser,html)
        try:
            p.locator('#restore').set_input_files(recovery_path);p.wait_for_function("document.querySelector('#status').textContent.includes('restored')")
            correct=p.locator('#seats').input_value()==str(cfg['threshold']) and p.locator('#service').input_value()==normal['id'] and not p.locator('#accept').is_checked() and p.locator('#download').is_disabled()
            p.locator('#calculate').click();correct &= cents(p.locator('#total').inner_text())==expected(cfg,normal['id'],cfg['threshold'])
            return correct
        finally:c.close()
    check('Fresh-browser draft recovery and revalidation',restore)
    def corrupted(kind):
        if not recovery_path.exists():return False
        x=json.loads(recovery_path.read_text())
        if kind=='tampered':x['state']['participants']=1
        elif kind=='task':x['state']['taskId']='other-task'
        elif kind=='authority':x['state']['approval']=True
        data=json.dumps(x).encode() if kind!='oversized' else b' '*9000
        page.locator('#restore').set_input_files({'name':kind+'.json','mimeType':'application/json','buffer':data})
        page.wait_for_function("document.querySelector('#status').textContent.includes('refused')")
        return page.locator('#quote').is_hidden() and page.locator('#download').is_disabled()
    for k in ['tampered','task','authority','oversized']:check('Refuse '+k+' recovery input',lambda k=k:corrupted(k))
    check('No runtime page errors',lambda:(not errors,errors))
    check('No network requests attempted',lambda:(not requests,requests))
    check('No personal-data fields',lambda:page.locator('input[type=email],input[type=password]').count()==0)
    if task=='B':
        check('Zero-price offering remains exactly zero',lambda:quote('orientation',8)==0)
        check('Sold-out offering cannot be estimated',lambda:invalid('1','advanced'))
        check('Per-offering capacity overrides global maximum',lambda:invalid('7','systems'))
        check('Half-cent discount rounds half-up',lambda:(quote('design',10)==expected(cfg,'design',10),{'expectedCents':expected(cfg,'design',10)}))
    if variant=='after':
        quote(normal['id'],cfg['threshold']);page.set_viewport_size({'width':1280,'height':900});page.screenshot(path=str(OUT/f'screenshots/{task}_after_desktop.png'),full_page=True)
        page.locator('#language').click();page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(OUT/f'screenshots/{task}_after_mobile_fr.png'),full_page=True)
    else:
        page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(OUT/f'screenshots/{task}_before_mobile.png'),full_page=True)
    ctx.close();report={'task':task,'variant':variant,'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'tests':results,'passed':sum(x['passed'] for x in results),'total':len(results),'browser':'Chromium '+browser.version,'mode':'Offline supplied HTML; real browser events and downloads; automated mechanical tests'}
    (OUT/f'acceptance/{task}_{variant}.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');print(task,variant,report['passed'],report['total'],flush=True)
    for x in results:
        if not x['passed'] and variant=='after':print('FAIL',x['test'],x['detail'],flush=True)
    return report

def hashes(browser):
    html=(ROOT/'02_Work_Products/Task_A/after/index.html').read_text();c,p,_,_=load(browser,html);vectors=['','abc','école','Ω\n\"','a'*1000]+['sample-'+str(i)+'é'*i for i in range(100)];observed=p.evaluate('(xs)=>xs.map(x=>sha256(new TextEncoder().encode(x)))',vectors);checks=[{'inputSha256':hashlib.sha256(x.encode()).hexdigest(),'passed':o==hashlib.sha256(x.encode()).hexdigest(),'length':len(x.encode())}for x,o in zip(vectors,observed)];c.close();(OUT/'acceptance/sha256_vectors.json').write_text(json.dumps({'count':len(checks),'passed':sum(x['passed'] for x in checks),'tests':checks},indent=2));print('Hash vectors',sum(x['passed'] for x in checks),len(checks))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--tasks',nargs='+',default=['A','B']);parser.add_argument('--variants',nargs='+',default=['before','after']);a=parser.parse_args()
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('BROWSER_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome'),headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        for task in a.tasks:
            for variant in a.variants:run_task(browser,task,variant)
        hashes(browser);browser.close()
