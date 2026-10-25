// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import * as automatedCosts from './automated-costs.mjs';
import * as transport from '../../docs/assets/successor/engine.mjs';

const source=readFileSync(new URL('../../scripts/templates/successor-alpha/automation-app.js',import.meta.url),'utf8');
const example=JSON.parse(readFileSync(new URL('./fixtures/automated-costs-example.json',import.meta.url),'utf8'));
const unknown=JSON.parse(readFileSync(new URL('./fixtures/automated-costs-unknown.json',import.meta.url),'utf8'));
function element(){return {value:'',checked:false,hidden:false,disabled:false,textContent:'',children:[],files:[],events:new Map(),
    addEventListener(name,callback){this.events.set(name,callback);},focus(){this.focused=true;},click(){return this.events.get('click')?.();},
    replaceChildren(){this.children=[];}};}
function load(dossier=null){
    const elements=new Map(),downloads=[];
    const $=id=>{if(!elements.has(id))elements.set(id,element());return elements.get(id);};
    $('automation-scenario').value='base';$('shadow-acceptance').value='unknown';$('shadow-currency').value='USD';
    const box={dossier,$,fr:{},JSON,TextEncoder,TextDecoder,automatedCosts,transport,
        AUTOMATED_COST_EXAMPLE:structuredClone(example),AUTOMATED_COST_UNKNOWN:structuredClone(unknown),
        language:'en',say:(en,_fr)=>en,number:value=>String(value),status(){},
        download:(...args)=>downloads.push(args),node:(tag,parent,value)=>{const child=element();child.tag=tag;
            child.textContent=value;parent.children.push(child);return child;}};
    vm.createContext(box);vm.runInContext(source,box,{filename:'scripts/templates/successor-alpha/automation-app.js'});
    return {box,$,downloads,read:expression=>vm.runInContext(expression,box),render:()=>vm.runInContext('renderAutomatedCosts()',box)};
}

test('actual automated-cost UI starts with the shared unknown record and no computed or cash claim',()=>{
    const view=load();assert.doesNotThrow(view.render);
    assert.deepEqual(JSON.parse(view.$('automation-record').value),unknown);
    assert.equal(view.read('automationRecord'),null);assert.equal(view.read('automationSummary'),null);
    assert.equal(view.$('automation-download').disabled,true);assert.equal(view.$('automation-apply').disabled,true);
    assert.equal(view.read('serializeAutomatedCosts()'),'null');
});

test('actual JSON calculator preserves unknown three-tier results and rejects duplicate input fields',()=>{
    const view=load();view.$('automation-calculate').click();
    const summary=view.read('automationSummary');
    assert.equal(summary.scenarios.length,3);
    assert(summary.scenarios.every(row=>row.costs.marginalMicrosPerAccepted===null
        && row.costs.recurringMicrosPerAccepted===null && row.costs.fullyLoadedMicrosPerAccepted===null));
    assert.equal(view.$('automation-apply').disabled,true);
    view.$('automation-record').value='{"schema":1,"schema":2}';view.$('automation-record').events.get('input')();
    view.$('automation-calculate').click();
    assert.equal(view.$('automation-error').hidden,false);
    assert.match(view.$('automation-error').textContent,/Duplicate JSON key/);
    assert.equal(view.read('automationRecord'),null);
});

test('modeled example exposes every cost tier and retains stress losses',()=>{
    const view=load();view.$('automation-example').click();const summary=view.read('automationSummary');
    assert(summary.scenarios.every(row=>row.costs.marginalMicrosPerAccepted!==null
        && row.costs.recurringMicrosPerAccepted!==null && row.costs.fullyLoadedMicrosPerAccepted!==null));
    assert.equal(summary.scenarios.find(row=>row.name==='stress').comparison.fullyLoaded.outcome,'loss');
    assert.equal(view.$('automation-result').hidden,false);
    view.$('automation-download').click();
    assert.equal(view.downloads.length,1);assert.deepEqual(JSON.parse(view.downloads[0][1]),example);
});

test('copying recurring allocation leaves investment cash and complete mission cost unknown',()=>{
    const view=load({id:'project-1',cycles:[{id:'cycle-1'}]});view.$('automation-example').click();
    const expected=view.read('automationSummary').scenarios.find(row=>row.name==='base').costs.recurringMicrosPerAccepted;
    view.$('shadow-cost-complete').checked=true;view.$('shadow-construction').value='200';
    view.$('automation-apply').click();
    assert.equal(view.$('shadow-cost').value,String(Math.ceil(expected/10000)/100));
    assert.equal(view.$('shadow-currency').value,example.currency);
    assert.equal(view.$('shadow-cost-complete').checked,false);assert.equal(view.$('shadow-construction').value,'');
    assert.equal(view.$('shadow-acceptance').value,'unknown');assert.equal(view.$('shadow-reserve').value,'');
    assert.equal(view.$('shadow-result').hidden,true);
    const saved=JSON.parse(view.read('serializeAutomatedCosts()'));
    assert.equal(saved.projectId,'project-1');assert.deepEqual(saved.record,example);
    assert.equal(Object.hasOwn(saved,'availableCash'),false);
});

test('an older asynchronous JSON import cannot replace a newer manual edit',async()=>{
    const view=load(),bytes=new TextEncoder().encode(JSON.stringify(example));let release;
    const pending=new Promise(resolve=>{release=resolve;});
    view.$('automation-file').files=[{size:bytes.length,arrayBuffer:()=>pending}];
    const importing=view.$('automation-file').events.get('change')();
    const edited='{"unfinished":"newer user edit"}';view.$('automation-record').value=edited;
    view.$('automation-record').events.get('input')();release(bytes.buffer);await importing;
    assert.equal(view.$('automation-record').value===edited,true,'A stale import overwrote the newer editor text.');
    assert.equal(view.read('automationSummary'),null);
    assert.equal(view.$('automation-error').hidden,false);
    assert.match(view.$('automation-error').textContent,/changed during import/);
});

test('a foreign-currency allocation refuses without relabeling or changing any mission amounts',()=>{
    const view=load({id:'project-1',cycles:[{id:'cycle-1'}]});
    const record=structuredClone(example);record.currency='CAD';
    view.$('automation-record').value=JSON.stringify(record);view.$('automation-calculate').click();
    const amounts={'shadow-cost':'8.50','shadow-price':'100','shadow-collected':'25','shadow-reserve':'20',
        'shadow-obligation':'5','shadow-hourly':'35.96','shadow-construction':'10'};
    for(const [id,value]of Object.entries(amounts))view.$(id).value=value;
    view.$('shadow-cost-complete').checked=true;view.$('shadow-result').hidden=false;
    view.$('automation-apply').click();
    assert.match(view.$('automation-error').textContent,/currency differs/);
    assert.equal(view.$('shadow-currency').value,'USD');
    for(const [id,value]of Object.entries(amounts))assert.equal(view.$(id).value,value,id);
    assert.equal(view.$('shadow-cost-complete').checked,true);
    assert.equal(view.$('shadow-result').hidden,false);
    assert.equal(view.$('shadow-cost').focused,undefined);
});
