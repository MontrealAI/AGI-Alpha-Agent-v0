// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {reference,stable,sha256} from './checker.mjs';

const here=path.dirname(fileURLToPath(import.meta.url));
const scopes={graph:['protocol.mjs','representation.mjs'],arithmetic:['protocol.mjs','representation.mjs','kernel-weighted.mjs'],boolean:['protocol.mjs','representation.mjs','kernel-boolean.mjs'],flat:['protocol.mjs','normalizer.mjs']};
const fail=message=>{throw Error(message);};

export async function createQualifier(candidateRoot,{criteria=path.join(here,'criteria.json'),bank=path.join(here,'qualification-bank.json'),mode='sliced',specialist=false}={}){
  const modules={};for(const name of ['representation','kernel-weighted','kernel-boolean','normalizer','direct-specialist'])modules[name]=await import(pathToFileURL(path.join(candidateRoot,name+'.mjs')).href);
  const loadedSource=Object.fromEntries([...new Set(Object.values(scopes).flat().concat('direct-specialist.mjs'))].map(name=>[name,sha256(fs.readFileSync(path.join(candidateRoot,name)))]));
  const bankBytes=fs.readFileSync(bank),bankData=JSON.parse(bankBytes),criteriaBytes=fs.readFileSync(criteria);
  const context={bankSha256:sha256(bankBytes),criteriaSha256:sha256(criteriaBytes),checkerSha256:sha256(fs.readFileSync(path.join(here,'checker.mjs'))),qualifierSha256:sha256(fs.readFileSync(fileURLToPath(import.meta.url))),nodeVersion:process.version};
  const cache=new Map();let totals={qualificationCases:0,qualificationAssertions:0,referenceSteps:0,inputFacts:0,hashBytes:0,cacheHits:0,cacheMisses:0,elapsedMs:0};
  function snapshot(){return {...totals};}
  async function qualify(kind,{contextOverride=null}={}){
    const start=performance.now(),before=snapshot(),receipts=[];
    const needed=kind==='flat-reduction'?['flat']:['graph',kind==='bom-demand'?'arithmetic':'boolean','flat'];
    for(const scope of needed){
      const names=[...scopes[scope]];if(specialist&&['arithmetic','boolean'].includes(scope))names.splice(names.length-1,1,'direct-specialist.mjs','normalizer.mjs');
      const source=names.map(name=>{const bytes=fs.readFileSync(path.join(candidateRoot,name));totals.hashBytes+=bytes.length;const digest=sha256(bytes);if(digest!==loadedSource[name])fail('LOADED_SOURCE_CHANGED');return {name,bytes:bytes.length,sha256:digest};});
      const keyText=stable({scope,source,context:contextOverride??context,specialist});totals.hashBytes+=Buffer.byteLength(keyText);const key=sha256(keyText);
      if(mode==='sliced'&&cache.has(key)){totals.cacheHits++;receipts.push({scope,key,reused:true,original:cache.get(key)});continue;}
      totals.cacheMisses++;let assertions=0;
      for(const mission of bankData[scope]){
        totals.qualificationCases++;const expected=reference(mission);totals.referenceSteps+=expected.counts.referenceSteps;totals.inputFacts+=expected.counts.inputFacts;
        if(!expected.accepted)fail('INVALID_QUALIFICATION_FIXTURE');
        if(scope==='graph'){
          const rep=modules.representation.buildRepresentation(mission.graph);const positions=new Map(rep.order.map((n,i)=>[n,i]));
          if(rep.order.length!==mission.graph.nodes.length||positions.size!==mission.graph.nodes.length||!mission.graph.nodes.every(n=>positions.has(n)))fail('ORDER_NODE_MISMATCH');assertions++;
          if(!mission.graph.edges.every(e=>positions.get(e.from)<positions.get(e.to)))fail('ORDER_EDGE_MISMATCH');assertions+=mission.graph.edges.length;
          const edges=x=>x.map(e=>stable(e)).sort();if(stable(edges(rep.edges))!==stable(edges(mission.graph.edges)))fail('EDGE_MULTIPLICITY_CHANGED');assertions++;
        }else{
          let rows;if(scope==='flat')rows=modules.normalizer.flatReduce(mission.rows);
          else if(specialist)rows=modules['direct-specialist'].directReduce(mission).rows;
          else {const rep=modules.representation.buildRepresentation(mission.graph),query={seeds:mission.seeds,targets:mission.targets};rows=scope==='arithmetic'?modules['kernel-weighted'].weightedReduce(rep,query):modules['kernel-boolean'].booleanReduce(rep,query);}
          const got={groups:rows.map(r=>({group:r.group,total:Number(r.amount)})).sort((a,b)=>a.group<b.group?-1:a.group>b.group?1:0),total:rows.reduce((sum,r)=>sum+Number(r.amount),0)};
          if(stable(got)!==stable(expected.output))fail('MODULE_OUTPUT_MISMATCH:'+scope);assertions+=rows.length+1;
          if(scope==='flat'){const normalized=modules.normalizer.normalizeRows(rows);if(normalized.delivery.status!=='ready'||normalized.rows.length!==rows.length)fail('NORMALIZATION_MISMATCH');assertions++;}
        }
      }
      totals.qualificationAssertions+=assertions;const receipt={scope,key,source,context,cases:bankData[scope].length,assertions,qualification:'finite evaluator-owned checks; not a formal program theorem'};cache.set(key,receipt);receipts.push({scope,key,reused:false,original:receipt});
    }
    totals.elapsedMs+=performance.now()-start;const after=snapshot();return {receipts,counts:Object.fromEntries(Object.keys(after).map(k=>[k,after[k]-before[k]]))};
  }
  return {qualify,snapshot,context,clear:()=>cache.clear(),exportHistory:()=>[...cache.values()]};
}
