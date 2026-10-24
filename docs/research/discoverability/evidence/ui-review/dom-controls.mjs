import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {boot} from '/workspace/scratch/dbacb361adf2/discoverability/examples/successor-discoverability/browser.mjs';
const source=await readFile('/workspace/scratch/dbacb361adf2/discoverability/examples/successor-discoverability/browser.mjs','utf8');
const nodes=new Map();
function node(id=''){return {id,disabled:false,hidden:false,value:'',textContent:'',listeners:{},children:[],addEventListener(type,fn){this.listeners[type]=fn;},replaceChildren(...x){this.children=x;},append(x){this.children.push(x);},click(){this.listeners.click?.();}};}
globalThis.document={getElementById(id){if(!nodes.has(id))nodes.set(id,node(id));return nodes.get(id);},createElement(){return node();}};
const get=id=>document.getElementById(id);get('mission').value='digital';get('condition').value='normal';
let exported;URL.createObjectURL=blob=>{exported=blob;return 'blob:review';};URL.revokeObjectURL=()=>{};
await boot({sourceHash:'a'.repeat(64),sourceManifest:{}});
await get('construct').listeners.click();await get('export').listeners.click();
const text=await exported.text();const realTimeout=globalThis.setTimeout;let pending=[];
globalThis.setTimeout=(fn,ms)=>{pending.push(fn);return pending.length;};
const acquisition=get('acquire').listeners.click();
const importEvent={target:{files:[{size:text.length,text:async()=>text}],value:'chosen'}};
await get('restore-file').listeners.change(importEvent);
const restoreDuringAcquire={pendingAcquisitionCheckpoints:pending.length,stopDisabled:get('stop').disabled,constructDisabled:get('construct').disabled,missionDisabled:get('mission').disabled,restoreDisabled:get('restore').disabled,status:get('status').textContent};
get('stop').listeners.click();while(pending.length){pending.shift()();await Promise.resolve();await Promise.resolve();}
await acquisition;globalThis.setTimeout=realTimeout;
await get('construct').listeners.click();pending=[];globalThis.setTimeout=(fn,ms)=>{pending.push(fn);return pending.length;};
const second=get('acquire').listeners.click();
for(let i=0;i<5;i++){if(!pending.length)throw Error('Missing checkpoint '+i);pending.shift()();await Promise.resolve();await Promise.resolve();}
get('stop').listeners.click();const requested=get('status').textContent;pending.shift()();await second;
const finalStop={requested,mode:get('mode').textContent,status:get('status').textContent,quality:get('metric-quality').textContent};
globalThis.setTimeout=realTimeout;
await get('construct').listeners.click();await get('acquire').listeners.click();await get('export').listeners.click();
const session=JSON.parse(await exported.text());
console.log(JSON.stringify({scope:'Real browser module and compiler executed under minimal DOM test double; not actual-browser acceptance',sourceSha256:createHash('sha256').update(source).digest('hex'),restoreDuringAcquire,finalStop,exportKeys:Object.keys(session),usage:session.usage,validationSummary:{keys:Object.keys(session.validation||{}),checks:session.validation?.checks?.length,acquisitions:session.validation?.acquisitions?.length},currentMetric:get('metric-cost').textContent},null,2));