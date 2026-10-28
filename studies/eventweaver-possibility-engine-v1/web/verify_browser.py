import json
import pathlib
import random
import sys

from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import eventweaver

def main():
    target=ROOT/'web/index.html'
    build=json.loads((ROOT/'results/browser_build.json').read_text())
    snapshots=ROOT/'.cache/browser_qa';snapshots.mkdir(parents=True,exist_ok=True)
    expected=json.loads((ROOT/'data/demo/expected.json').read_text())['outputs']
    spec=json.loads((ROOT/'data/demo/spec.json').read_text())
    traces=[]
    rng=random.Random(5491)
    for _ in range(12):
        trace=[{'events':rng.randrange(256),'rst':rng.random()<.02} for _ in range(128)]
        trace[0]['rst']=True
        traces.append(trace)
    errors=[];network=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('request',lambda request:network.append(request.url) if request.url.startswith(('http://','https://')) else None)
        page.goto(target.as_uri())
        page.wait_for_function('window.EventWeaverDemo !== undefined')
        assert page.evaluate('window.EventWeaverDemo.currentOutputs')==expected
        page.screenshot(path=str(snapshots/'desktop_cover.png'))
        page.locator('#demonstration').scroll_into_view_if_needed()
        page.screenshot(path=str(snapshots/'desktop_demo.png'))
        page.click('#late-veto')
        changed=page.evaluate('window.EventWeaverDemo.currentOutputs')
        assert changed[8]==0 and changed[9]==2 and changed[20]==2
        page.click('#restore-demo')
        page.click('#add-reset')
        reset=page.evaluate('window.EventWeaverDemo.currentOutputs')
        assert reset[8]==0 and reset[9]==0 and reset[20]==2
        page.click('#clear-demo')
        assert not any(page.evaluate('window.EventWeaverDemo.currentOutputs'))
        page.click('#restore-demo')
        page.locator('#cell-0-1').focus()
        page.keyboard.press('Enter')
        assert page.locator('#cell-0-1').get_attribute('aria-pressed')=='false'
        page.keyboard.press('Enter')
        assert page.evaluate('window.EventWeaverDemo.currentOutputs')==expected
        for i,trace in enumerate(traces):
            actual=page.evaluate('(rows)=>window.EventWeaverDemo.simulate(rows)',trace)
            assert actual==eventweaver.run(spec,trace),f'Browser parity trace {i}'
        page.click('#focus-mode')
        assert page.locator('body').get_attribute('class')=='reading-focus'
        page.click('#focus-mode')
        internal=page.eval_on_selector_all('a[href^="#"]','links=>links.map(a=>a.getAttribute("href")).filter(h=>h.length>1&&!document.getElementById(h.slice(1)))')
        assert not internal,internal
        broken_images=page.eval_on_selector_all('img','images=>images.filter(x=>!x.complete||x.naturalWidth===0).map(x=>x.src.slice(0,80))')
        assert not broken_images,broken_images
        content_counts={'tables':page.locator('.paper-body table').count(),'figures':page.locator('.paper-body figure').count(),'references':page.locator('.paper-body [id^="ref-"]').count()}
        if not build['draft']:
            assert content_counts==build['content_counts'],content_counts
            assert content_counts['references']==38
            assert page.locator('#paper-what-is-necessary-for-the-outcome').count()==1
            assert page.locator('#paper-the-failed-candidate-did-not-retain-the-flagship').count()==1
            assert page.locator('.citation a[href^="#ref-"]').count()>0
            assert page.locator('.paper-body embed,.paper-body object,.draft-banner').count()==0
            assert page.locator('.paper-body math').count()>0
            for name,selector in [('desktop_semantics','#paper-a-precise-acceptance-semantics'),('desktop_kernel','#paper-what-is-necessary-for-the-outcome'),('desktop_economics','#paper-what-the-complete-bill-contains'),('desktop_references','#paper-references')]:
                page.locator(selector).evaluate('(element)=>window.scrollTo({top:element.getBoundingClientRect().top+window.scrollY-90,behavior:"instant"})')
                page.screenshot(path=str(snapshots/(name+'.png')))
        assert page.evaluate('document.documentElement.scrollWidth')<=1440
        page.set_viewport_size({'width':390,'height':844})
        page.goto(target.as_uri())
        page.wait_for_function('window.EventWeaverDemo !== undefined')
        assert page.evaluate('document.documentElement.scrollWidth')<=390
        page.screenshot(path=str(snapshots/'mobile_cover.png'))
        page.click('#toc-toggle')
        assert page.locator('#toc-toggle').get_attribute('aria-expanded')=='true'
        page.click('#toc-toggle')
        page.locator('#demonstration').scroll_into_view_if_needed()
        page.screenshot(path=str(snapshots/'mobile_demo.png'))
        if not build['draft']:
            for name,selector in [('mobile_semantics','#paper-a-precise-acceptance-semantics'),('mobile_kernel','#paper-what-is-necessary-for-the-outcome'),('mobile_references','#paper-references')]:
                page.locator(selector).evaluate('(element)=>window.scrollTo({top:element.getBoundingClientRect().top+window.scrollY-85,behavior:"instant"})')
                page.screenshot(path=str(snapshots/(name+'.png')))
            assert page.evaluate('document.documentElement.scrollWidth')<=390
        assert not errors,errors
        assert not network,network
        report={'status':'PASS','title':page.title(),'desktop_viewport':[1440,1000],'mobile_viewport':[390,844],'demo_expected_outputs':'PASS','late_veto_and_group_isolation':'PASS','reset':'PASS','clear_and_restore':'PASS','keyboard_toggle':'PASS','mobile_navigation':'PASS','focus_reading':'PASS','browser_oracle_vs_python_engine':{'traces':12,'ticks_per_trace':128,'total_ticks':1536,'status':'PASS','interpretation':'Browser implementation parity check, separate from scientific confirmation'},'content_counts':content_counts,'paper_word_count':build['paper_word_count'],'mathml_expressions':page.locator('.paper-body math').count(),'internal_citation_links':page.locator('.citation a[href^="#ref-"]').count(),'missing_internal_anchors':internal,'broken_embedded_images':broken_images,'external_requests':network,'javascript_errors':errors,'draft':build['draft'],'html_sha256':build['html_sha256'],'screenshots':'Internal QA only, .cache/browser_qa/'}
        (ROOT/'results/browser_qa.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
        browser.close()

if __name__=='__main__':main()
