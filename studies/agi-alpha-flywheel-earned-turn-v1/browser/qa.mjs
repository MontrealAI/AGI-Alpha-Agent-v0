import {chromium,executablePath} from './qa-tools.mjs';
import {writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const out=new URL('./qa/',import.meta.url);await mkdir(out,{recursive:true});
const url=new URL('./index.html',import.meta.url).href;
const browser=await chromium.launch({headless:true,executablePath,args:['--no-sandbox']});
const results=[],errors=[],requests=[];
async function open(size={width:1440,height:1100}){const context=await browser.newContext({viewport:size});await context.route('http**/*',route=>{requests.push(route.request().url());route.abort();});const page=await context.newPage();page.on('pageerror',e=>errors.push(String(e)));await page.goto(url);await page.waitForFunction(()=>globalThis.__earnedTurnReady);return{context,page};}
function check(name,value,detail){results.push({name,passed:Boolean(value),detail});if(!value)throw Error(name);}
try{
 const {context,page}=await open();
 await page.screenshot({path:fileURLToPath(new URL('desktop-start.png',out)),fullPage:true});
 check('one_obvious_start',await page.locator('#start-button').isEnabled());
 await page.click('#start-button');await page.waitForFunction(()=>globalThis.__earnedTurnState?.stage===4,{timeout:30000});
 const s=await page.evaluate(()=>globalThis.__earnedTurnState);
 check('four_fresh_outputs',s.accepted.length===4&&s.accepted.every(r=>r.valid));
 check('actual_prior_B_lineage',s.successor.source_response_hash===s.accepted[1].result_hash);
 check('construction_parent_used',s.accepted[2].parent_construction_calls===2);
 check('fresh_successor_parent_used',s.accepted[3].parent_execution_calls===1);
 check('strong_direct_reference_retains_factors',s.accepted[1].costs.reference_operations<20000&&s.accepted[3].costs.reference_operations<20000);
 check('negative_execution_transfer_preserved',s.accepted[3].costs.operations>s.accepted[3].costs.reference_operations);
 check('whole_stream_accounts',s.accounts.service.spent===s.accepted.filter(r=>r.phase!==2).reduce((n,r)=>n+r.costs.operations,0)&&s.accounts.improvement.spent===s.accepted[2].costs.operations);
 check('no_production_authority',s.accepted.every(r=>r.pack.evaluation.admission==='HOLD'&&r.pack.evaluation.authority.length===0));
 check('no_horizontal_overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.screenshot({path:fileURLToPath(new URL('desktop-complete.png',out)),fullPage:true});
 await writeFile(new URL('fresh-evidence.json',out),JSON.stringify(s,null,2));
 const downloadPromise=page.waitForEvent('download');await page.click('#download-button');const download=await downloadPromise;await download.saveAs(fileURLToPath(new URL('downloaded-evidence.json',out)));check('evidence_download',download.suggestedFilename().endsWith('.json'));
 await page.reload();await page.waitForFunction(()=>globalThis.__earnedTurnReady);check('restart_preserves_success_without_duplication',(await page.evaluate(()=>globalThis.__earnedTurnState.accepted.length))===4);
 await page.click('#stale-button');check('stale_evidence_refusal',(await page.locator('#control-result').textContent()).startsWith('Refused:'));
 await page.click('#shift-button');check('unsupported_update_refusal',(await page.locator('#control-result').textContent()).startsWith('Refused:'));
 await page.click('#rollback-button');check('rollback_retains_history',await page.evaluate(()=>globalThis.__earnedTurnState.status==='ROLLED_BACK'&&globalThis.__earnedTurnState.accepted.length===4));
 await context.close();
 const mobile=await open({width:390,height:844});await mobile.page.click('#start-button');await mobile.page.waitForFunction(()=>globalThis.__earnedTurnState?.stage===4);check('mobile_no_overflow',await mobile.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await mobile.page.screenshot({path:fileURLToPath(new URL('mobile-complete.png',out)),fullPage:true});await mobile.context.close();
 const stop=await open();await stop.page.evaluate(()=>{const poll=setInterval(()=>{const button=document.querySelector('#stop-button');if(!button.disabled&&globalThis.__earnedTurnState?.pending){clearInterval(poll);button.click();}},1);document.querySelector('#start-button').click();});await stop.page.waitForFunction(()=>globalThis.__earnedTurnState?.status==='STOPPED'||globalThis.__earnedTurnState?.status==='COMPLETE');const ss=await stop.page.evaluate(()=>globalThis.__earnedTurnState);check('stop_is_recorded',ss.events.some(e=>e.kind==='HUMAN_STOP_REQUEST'));
 await stop.page.reload();await stop.page.waitForFunction(()=>globalThis.__earnedTurnReady);await stop.page.click('#start-button');await stop.page.waitForFunction(()=>globalThis.__earnedTurnState?.stage===4||globalThis.__earnedTurnState?.status==='BUDGET_STOP');const resumed=await stop.page.evaluate(()=>globalThis.__earnedTurnState);check('resume_respects_budget',resumed.accounts.service.spent<=220000&&resumed.accounts.improvement.spent<=80000);check('no_duplicate_acceptance',new Set(resumed.accepted.map(r=>r.phase)).size===resumed.accepted.length);await stop.context.close();
 check('no_network_requests',requests.length===0,requests);check('no_browser_errors',errors.length===0,errors);
}catch(e){results.push({name:'unexpected_exception',passed:false,detail:String(e)});}
finally{await browser.close();await writeFile(new URL('BROWSER_QA.json',out),JSON.stringify({at:new Date().toISOString(),results,errors,requests,pass:results.every(r=>r.passed)},null,2));console.log(JSON.stringify(results));}
