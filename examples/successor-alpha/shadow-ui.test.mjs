// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import * as shadow from './shadow-plan.mjs';
import * as transport from '../../docs/assets/successor/engine.mjs';

const source = readFileSync(new URL('../../scripts/templates/successor-alpha/shadow-app.js',import.meta.url),'utf8');
const project = {id:'project-1',cycles:[{id:'cycle-1',sourceHash:'a'.repeat(64)}]};
const inputs = {currency:'CAD',acceptance:'accepted',totalCollectedCents:null,priceAssumptionCents:10000,
    totalOperatingCostCents:50,operatingCostsComplete:true,capabilityCostCents:1000,reserveCents:2000,
    obligationCents:500,costBasis:'assumed',reinvestmentBps:5000,humanMinutes:5,humanHourlyCents:4000,traditionalMinutes:300};

function element() {
    return {value:'',checked:false,hidden:false,disabled:false,textContent:'',children:[],
        addEventListener(){},removeAttribute(){},setAttribute(){},focus(){},click(){},
        querySelectorAll(){return [];},replaceChildren(){this.children=[];}};
}
function load(dossier=null,shadowArchive=null) {
    const elements=new Map();
    const $=id=>{if(!elements.has(id))elements.set(id,element());return elements.get(id);};
    const box={dossier,shadowArchive,shadowCurrent:null,shadowFormCycleId:null,shadowImportVersion:0,
        language:'en',$,shadow,transport,TextDecoder,TextEncoder,say:(en,_fr)=>en,download(){},
        node:(tag,parent,value)=>{const child=element();child.tag=tag;child.textContent=value;parent.children.push(child);return child;}};
    vm.createContext(box);
    vm.runInContext(source,box,{filename:'scripts/templates/successor-alpha/shadow-app.js'});
    return {box,$,render:()=>vm.runInContext('renderShadow()',box),restore:()=>vm.runInContext('restoreShadow()',box)};
}

test('actual shadow UI initializes without a project or archive and leaves unknown inputs empty',()=>{
    const view=load();
    assert.doesNotThrow(view.render);
    assert.equal(view.$('shadow-calculate').disabled,true);
    assert.equal(view.$('shadow-download').disabled,true);
    assert.equal(view.$('shadow-result').hidden,true);
    assert.equal(view.$('shadow-cost').value,'');
    assert.equal(view.$('shadow-acceptance').value,'unknown');
    assert.equal(view.$('shadow-reinvestment').value,'0');
    assert.equal(view.box.shadowCurrent,null);
});

test('first actual mission initializes its form without a planning archive',()=>{
    const view=load(structuredClone(project));
    assert.doesNotThrow(view.render);
    assert.equal(view.$('shadow-calculate').disabled,false);
    assert.equal(view.$('shadow-download').disabled,true);
    assert.equal(view.$('shadow-cost').value,'');
    assert.equal(view.$('shadow-price').value,'');
    assert.equal(view.box.shadowFormCycleId,'cycle-1');
    assert.equal(view.box.shadowArchive,null);
});

test('actual restoration consumes retained inputs and recomputes the current accounting snapshot',()=>{
    const archive=shadow.recordPlan(shadow.createPlans(project),project,inputs);
    const view=load(structuredClone(project));
    view.$('saved-shadow-ledger').textContent=JSON.stringify(archive);
    assert.doesNotThrow(view.restore);
    assert.equal(view.$('shadow-currency').value,'CAD');
    assert.equal(view.$('shadow-cost').value,'0.5');
    assert.equal(view.$('shadow-price').value,'100');
    assert.equal(view.$('shadow-reinvestment').value,'50');
    assert.equal(view.$('shadow-result').hidden,false);
    assert.equal(view.box.shadowCurrent.summary.scenario.fullCost,1050);
    assert.equal(view.box.shadowCurrent.summary.scenario.eligibleInvestment,3225);
    assert.equal(view.box.shadowCurrent.summary.observed.availableSurplus,null);
    assert.equal(transport.canonical(view.box.shadowArchive),transport.canonical(archive));
});

test('fresh cycle clears inherited assumptions while preserving earlier mission plans',()=>{
    const archive=shadow.recordPlan(shadow.createPlans(project),project,inputs), before=transport.canonical(archive);
    const view=load(structuredClone(project),archive);
    view.render();
    assert.equal(view.$('shadow-price').value,'100');
    view.box.dossier.cycles.push({id:'cycle-2',sourceHash:'b'.repeat(64)});
    view.render();
    assert.equal(view.$('shadow-cost').value,'');
    assert.equal(view.$('shadow-price').value,'');
    assert.equal(view.$('shadow-collected').value,'');
    assert.equal(view.$('shadow-acceptance').value,'unknown');
    assert.equal(view.$('shadow-reinvestment').value,'0');
    assert.equal(view.box.shadowCurrent,null);
    assert.equal(view.$('shadow-download').disabled,false);
    assert.equal(transport.canonical(view.box.shadowArchive),before);
    assert.match(view.$('shadow-result').children.at(-1).textContent,/Earlier planning records are retained/);
});
