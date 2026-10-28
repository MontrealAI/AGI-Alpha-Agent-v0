// SPDX-License-Identifier: Apache-2.0
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require('/root/.local/lib/python3.12/site-packages/playwright/driver/package');
(async () => {
  const qa = __dirname, pub = path.dirname(qa);
  const htmlFile = path.join(pub, 'Browser_Edition.html');
  const pdfFile = path.join(pub, 'AGI_ALPHA_Discovery_Means_v1.pdf');
  const digest = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
  const htmlBefore = digest(htmlFile), pdfBefore = digest(pdfFile);
  const old = path.join(qa, 'browser-qa.json');
  if (fs.existsSync(old)) {
    const prior = JSON.parse(fs.readFileSync(old));
    const priorFile = path.join(qa, 'browser-qa-prior-' + prior.html_sha256.slice(0, 12) + '.json');
    if (!fs.existsSync(priorFile)) fs.copyFileSync(old, priorFile);
  }
  const browser = await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--disk-cache-size=1','--media-cache-size=1','--disable-background-networking']});
  const results = [];
  try {
    for (const [name,width,height] of [['desktop',1440,1000],['mobile',390,844]]) {
      const context = await browser.newContext({viewport:{width,height}, deviceScaleFactor:1});
      await context.route('**/*', route => route.request().url().startsWith('file:') ? route.continue() : route.abort());
      const page = await context.newPage(), errors=[];
      page.on('pageerror', error => errors.push(String(error)));
      await page.goto('file://' + htmlFile, {waitUntil:'load',timeout:30000});
      await page.screenshot({path:path.join(qa,name+'.png'),fullPage:false});
      const metrics = await page.evaluate(() => {
        const scrollers = [...document.querySelectorAll('.math-scroll,pre,table')].map((el,i) => {
          const before=el.scrollLeft, max=Math.max(0,el.scrollWidth-el.clientWidth);
          el.scrollLeft=el.scrollWidth; const end=el.scrollLeft; el.scrollLeft=before;
          const style=getComputedStyle(el);
          return {i,tag:el.tagName,class:el.className,client:el.clientWidth,scroll:el.scrollWidth,max,end,reachable:max<=1||Math.abs(end-max)<=1,overflowX:style.overflowX};
        });
        const broken=[...document.querySelectorAll('a[href^="#"]')].map(a=>a.getAttribute('href')).filter(h=>!document.getElementById(decodeURIComponent(h.slice(1))));
        const overflowBlocks=[...document.querySelectorAll('main > p,main > h1,main > h2,main > h3,header,nav,figure')].filter(el=>{const r=el.getBoundingClientRect();return r.right>innerWidth+1||r.left< -1;}).map(el=>({tag:el.tagName,id:el.id,right:el.getBoundingClientRect().right}));
        return {width:innerWidth,scroll:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,h1color:getComputedStyle(document.querySelector('header h1')).color,broken_anchors:broken,nested_scrollers:scrollers,overflow_blocks:overflowBlocks,main_overflow_x:getComputedStyle(document.querySelector('main')).overflowX};
      });
      const links = await page.locator('a').evaluateAll(as=>as.map(a=>a.getAttribute('href')).filter(h=>h&&!h.startsWith('#')&&!/^[a-z]+:/i.test(h)));
      const missing = links.filter(h=>!fs.existsSync(path.resolve(pub,h)));
      await page.locator('nav a[href="#the-instrument-and-its-native-boundary"]').click();
      const navigated = await page.evaluate(()=>scrollY>0&&location.hash==='#the-instrument-and-its-native-boundary');
      if (name==='mobile') {
        const lastMath=page.locator('.math-scroll').last();
        await lastMath.scrollIntoViewIfNeeded();
        await lastMath.evaluate(el=>{el.scrollLeft=el.scrollWidth;});
        await page.screenshot({path:path.join(qa,'mobile-equation-end.png'),fullPage:false});
      }
      results.push({viewport:name,metrics,horizontal_overflow:metrics.scroll>width,broken_anchors:metrics.broken_anchors,missing_local_links:missing,page_errors:errors,navigation_scrolled:navigated,pdf_and_tex_links_exist:fs.existsSync(pdfFile)&&fs.existsSync(path.join(pub,'AGI_ALPHA_Discovery_Means_v1.tex')),nested_scroll_ends_reachable:metrics.nested_scrollers.every(x=>x.reachable),ordinary_blocks_within_viewport:metrics.overflow_blocks.length===0});
      await context.close();
    }
  } finally { await browser.close(); }
  const result={html_sha256:htmlBefore,pdf_sha256:pdfBefore,scope:'Sequential local desktop/mobile rendering, viewport overflow, reachable nested equation/code/table scrolling, anchors and local links; no public deployment acceptance.',results,files_unchanged:digest(htmlFile)===htmlBefore&&digest(pdfFile)===pdfBefore,screenshots:['desktop.png','mobile.png','mobile-equation-end.png'],prior_attempts:['Prior stale QA receipt retained under its own HTML hash; it tested the earlier da44ff source with mobile overflow.']};
  result.status=results.every(x=>!x.horizontal_overflow&&!x.broken_anchors.length&&!x.missing_local_links.length&&!x.page_errors.length&&x.navigation_scrolled&&x.nested_scroll_ends_reachable&&x.ordinary_blocks_within_viewport)&&result.files_unchanged?'PASS':'FAIL';
  fs.writeFileSync(old,JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify({status:result.status,html_sha256:htmlBefore,pdf_sha256:pdfBefore,results:results.map(x=>({viewport:x.viewport,width:x.metrics.width,scroll:x.metrics.scroll,nested_reachable:x.nested_scroll_ends_reachable,ordinary_blocks_within_viewport:x.ordinary_blocks_within_viewport,missing_links:x.missing_local_links,page_errors:x.page_errors}))},null,2));
  if(result.status!=='PASS')process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
