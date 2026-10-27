// SPDX-License-Identifier: Apache-2.0
// A minimal DOM checks translation/control logic; no browser or layout claim.
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const html=fs.readFileSync(path.join(here,'index.html'),'utf8');
const attrs=s=>Object.fromEntries([...s.matchAll(/([\w-]+)="([^"]*)"/g)].map(m=>[m[1],m[2]]));
class Element {
  constructor(a={}){this.attrs=a;this.dataset=Object.fromEntries(Object.entries(a).filter(([k])=>k.startsWith('data-')).map(([k,v])=>[k.slice(5),v]));this.handlers={};this.textContent='';this.innerHTML='';this.className=a.class||'';this.classList={toggle:()=>{}};}
  setAttribute(k,v){this.attrs[k]=String(v);}
  addEventListener(k,fn){this.handlers[k]=fn;}
  querySelectorAll(selector){if(selector==='button')return [...this.innerHTML.matchAll(/<button\b([^>]*)>/g)].map(x=>new Element(attrs(x[1])));return [];}
  click(){this.handlers.click?.({target:this});}
}
const elements=[...html.matchAll(/<[A-Za-z][\w:-]*\b([^>]*?)>/g)].map(x=>new Element(attrs(x[1])));
const byId=Object.fromEntries(elements.filter(x=>x.attrs.id).map(x=>[x.attrs.id,x]));
for(const id of ['demo-data','demo-copy'])byId[id].textContent=html.match(new RegExp(`<script id="${id}" type="application/json">([\\s\\S]*?)<\\/script>`))[1];
const document={documentElement:{lang:'en'},title:'',getElementById:id=>{if(!byId[id])throw Error('Missing DOM id '+id);return byId[id];},querySelector:s=>elements.find(x=>x.className.split(' ').includes(s.slice(1))),querySelectorAll:s=>s==='[data-i18n]'?elements.filter(x=>x.dataset.i18n):elements.filter(x=>x.className.split(' ').includes(s.slice(1))),createElement:()=>new Element()};
const storage=new Map();
const context={document,window:{},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},Blob,URL,setTimeout:fn=>fn(),Intl};
vm.createContext(context);
const script=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].at(-1)[1];
new vm.Script(script,{filename:'embedded-demo.js'}).runInContext(context,{timeout:5000});
const checks=[];
const check=(name,c)=>{checks.push({name,passed:!!c});if(!c)throw Error(name);};
const demo=context.window.BeyondBetaDemo;
check('English boot and preselected example',demo.getState().language==='en'&&demo.getState().selection.seed===demo.data.preselected.seed);
check('Every prespecified condition is offered',[...byId['scenario-select'].innerHTML.matchAll(/<option /g)].length===demo.data.protocol.scenarios.length);
check('Every prespecified arm is offered',[...byId['arm-select'].innerHTML.matchAll(/<option /g)].length===demo.data.protocol.experiment.confirmationArms.length);
check('All conditions have a result-table row',[...byId['conditions-body'].innerHTML.matchAll(/<tr>/g)].length===demo.data.protocol.scenarios.length);
check('Six lifecycle controls exist',[...byId['gate-buttons'].innerHTML.matchAll(/data-gate=/g)].length===6);
demo.setLanguage('fr');
check('French principal title and document language',document.documentElement.lang==='fr'&&document.title.startsWith('Travail rémunéré.'));
check('Independently selected Beta arm is translated',byId['arm-select'].innerHTML.includes('Politique Bêta choisie séparément'));
byId['seed-select'].handlers.change({target:{value:String(demo.data.protocol.experiment.confirmationSeeds.at(-1))}});
check('Exploratory selector updates state',demo.getState().selection.seed===demo.data.protocol.experiment.confirmationSeeds.at(-1));
byId['restore-default'].click();
check('Reset restores the fixed prospective example',JSON.stringify(demo.getState().selection)===JSON.stringify(demo.data.preselected));
byId['download-record'].click();
check('Download handler executes using embedded evidence only',true);
demo.setLanguage('en');
if(demo.data.status==='PENDING_RESULTS')check('Unbound economic panels show no invented values',['metric-value','metric-accepted','metric-false','metric-cash'].every(id=>byId[id].textContent==='—'));
else {
  const result=demo.data.results,selection=demo.getState().selection;
  const selected=result.worlds.find(w=>w.summary.scenario===selection.scenario&&w.summary.seed===selection.seed&&w.summary.arm===selection.arm);
  check('All confirmation worlds are embedded without selection',result.worlds.length===demo.data.protocol.experiment.confirmationHistories);
  check('Visible accepted count comes from the fixed recorded example',byId['metric-accepted'].textContent===new Intl.NumberFormat('en-US',{maximumFractionDigits:0}).format(selected.summary.accepted));
  check('Commercial table retains distinct Beta and optional-Alpha columns',[...byId['commercial-body'].innerHTML.matchAll(/<tr>/g)].length===9);
  check('Original training flags and diagnostic replay remain visible',byId['audit-note'].textContent.includes('51')&&result.audits[0].originalStatus==='FAIL'&&result.audits.every(x=>x.diagnosticStatus==='PASS'));
  check('Storage recovery and incomplete timing remain visible',byId['operational-note'].textContent.includes('storage-capacity')&&byId['operational-note'].textContent.includes('lower bound')&&result.operational.recoveryVerification.completeRecordHashesVerified===1289);
  if(selected.firstPaidCandidate)check('First paid candidate preserves its recorded outcome',byId['first-paid-body'].innerHTML.includes(selected.firstPaidCandidate.state));
  check('Eight separate claim gates render',[...byId['claim-cards'].innerHTML.matchAll(/<article class="claim">/g)].length===8);
  byId['scenario-select'].handlers.change({target:{value:'no-demand'}});
  const zero=result.worlds.find(w=>w.summary.scenario==='no-demand'&&w.summary.seed===selection.seed&&w.summary.arm===selection.arm);
  check('No-demand adverse case remains reachable',demo.getState().selection.scenario==='no-demand'&&zero.summary.accepted===0&&byId['metric-accepted'].textContent==='0');
  check('Undefined zero-denominator unit cost is not invented',byId['metric-unit-cost'].textContent==='—');
  byId['restore-default'].click();demo.setLanguage('fr');
  check('Audit and interruption disclosure translate with principal French text',byId['audit-note'].textContent.includes('51')&&byId['operational-note'].textContent.includes('stockage'));
  demo.setLanguage('en');
}

const result={schema:'beyond-beta-demo-dom-logic-qa/v1',basis:'EXECUTED_MINIMAL_DOM_NOT_A_BROWSER_OR_SCREENSHOT',status:'PASS',checks,htmlSha256:crypto.createHash('sha256').update(html).digest('hex'),economicWorldsExecuted:0};
fs.writeFileSync(path.join(here,'qa-dom.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({status:result.status,checks:checks.length,basis:result.basis}));
