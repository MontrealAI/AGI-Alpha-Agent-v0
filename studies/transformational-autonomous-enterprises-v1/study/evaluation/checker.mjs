// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

export const sha256=value=>createHash('sha256').update(value).digest('hex');
export const stable=value=>JSON.stringify(value,(_k,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
const need=(v,code)=>{if(!v)throw Error(code);};
const integer=v=>Number.isSafeInteger(v);
const label=v=>typeof v==='string'&&/^[A-Za-z0-9_-]{1,48}$/.test(v);

export function reference(mission){
  const counts={inputFacts:0,referenceSteps:0};
  try {
    need(mission&&mission.schema==='tae/mission-v1'&&label(mission.missionId),'INVALID_SCHEMA');
    let answer;
    if(mission.kind==='flat-reduction'){
      need(Array.isArray(mission.rows)&&mission.rows.length>0&&mission.rows.length<=2000,'INVALID_ROWS');
      const sums=new Map();
      for(const row of mission.rows){counts.inputFacts+=2;need(label(row.group)&&integer(row.amount)&&Math.abs(row.amount)<=1000000,'INVALID_ROW');sums.set(row.group,(sums.get(row.group)||0n)+BigInt(row.amount));counts.referenceSteps++;}
      answer=[...sums].map(([group,total])=>({group,total}));
    } else {
      need(['bom-demand','remediation-impact'].includes(mission.kind),'UNSUPPORTED_SCOPE');
      const graph=mission.graph;
      need(graph&&Array.isArray(graph.nodes)&&graph.nodes.length>0&&graph.nodes.length<=64&&Array.isArray(graph.edges)&&graph.edges.length<=256,'INVALID_GRAPH');
      const nodes=new Set(graph.nodes);counts.inputFacts+=graph.nodes.length;
      need(nodes.size===graph.nodes.length&&graph.nodes.every(label),'INVALID_NODES');
      const forward=new Map(graph.nodes.map(n=>[n,[]]));
      for(const e of graph.edges){counts.inputFacts+=3;need(nodes.has(e.from)&&nodes.has(e.to)&&integer(e.weight)&&e.weight>0,'INVALID_EDGE');forward.get(e.from).push(e);}
      const done=new Set(),active=new Set();
      function acyclic(n){counts.referenceSteps++;need(!active.has(n),'CYCLE');if(done.has(n))return;active.add(n);for(const e of forward.get(n))acyclic(e.to);active.delete(n);done.add(n);}
      for(const n of graph.nodes)acyclic(n);
      need(Array.isArray(mission.seeds)&&mission.seeds.length>0&&mission.seeds.length<=64,'INVALID_SEEDS');
      for(const s of mission.seeds){counts.inputFacts+=2;need(nodes.has(s.node)&&integer(s.amount)&&s.amount>=0,'INVALID_SEED');}
      need(Array.isArray(mission.targets)&&mission.targets.length>0&&mission.targets.length<=64&&new Set(mission.targets).size===mission.targets.length&&mission.targets.every(n=>nodes.has(n)),'INVALID_TARGETS');counts.inputFacts+=mission.targets.length;
      if(mission.kind==='bom-demand'){
        const sums=new Map(mission.targets.map(n=>[n,0n]));let traversals=0;
        function paths(node,weight){counts.referenceSteps++;need(++traversals<=2000000,'REFERENCE_RESOURCE_CEILING');if(sums.has(node))sums.set(node,sums.get(node)+weight);for(const edge of forward.get(node))paths(edge.to,weight*BigInt(edge.weight));}
        for(const seed of mission.seeds)paths(seed.node,BigInt(seed.amount));
        answer=[...sums].map(([group,total])=>({group,total}));
      }else{
        const reached=new Set(),queue=mission.seeds.filter(s=>s.amount>0).map(s=>s.node);
        for(let i=0;i<queue.length;i++){const n=queue[i];counts.referenceSteps++;if(reached.has(n))continue;reached.add(n);for(const e of forward.get(n))queue.push(e.to);}
        answer=mission.targets.map(group=>({group,total:reached.has(group)?1n:0n}));
      }
    }
    answer.sort((a,b)=>a.group<b.group?-1:a.group>b.group?1:0);
    need(answer.every(r=>r.total>=-1000000n&&r.total<=1000000n),'DELIVERY_RESOURCE_CEILING');
    const total=answer.reduce((s,r)=>s+r.total,0n);need(total>=-1000000n&&total<=1000000n,'DELIVERY_RESOURCE_CEILING');
    return {accepted:true,output:{groups:answer.map(r=>({group:r.group,total:Number(r.total)})),total:Number(total)},counts};
  }catch(error){return {accepted:false,reason:error.message,counts};}
}

export function checkArtifact(artifactBytes,inputBytes,criteriaBytes){
  let artifact,mission,expected;const failures=[];
  try{artifact=JSON.parse(artifactBytes);mission=JSON.parse(inputBytes);JSON.parse(criteriaBytes);}catch{failures.push('INVALID_JSON');}
  if(!failures.length&&(!artifact||typeof artifact!=='object'||Array.isArray(artifact)||!mission||typeof mission!=='object'||Array.isArray(mission)))failures.push('INVALID_OBJECT');
  if(!failures.length){
    expected=reference(mission);
    if(artifact.schema!=='tae.artifact.v1')failures.push('ARTIFACT_SCHEMA');
    if(artifact.missionId!==mission.missionId)failures.push('MISSION_ID');
    if(artifact.inputHash!==sha256(inputBytes))failures.push('INPUT_HASH');
    if(!/^[a-f0-9]{64}$/.test(artifact.capabilityHash||''))failures.push('CAPABILITY_IDENTITY');
    if(artifact.currentProof!==null||!Array.isArray(artifact.authority)||artifact.authority.length)failures.push('INHERITED_PROOF_OR_AUTHORITY');
    if(!expected.accepted)failures.push('REFERENCE_REFUSED:'+expected.reason);
    if(expected.accepted&&stable(artifact.output)!==stable(expected.output))failures.push('SEMANTIC_OUTPUT_MISMATCH');
  }
  return {schema:'tae.proof.v1',missionId:mission?.missionId??null,artifactSha256:sha256(artifactBytes),inputSha256:sha256(inputBytes),capabilityHash:artifact?.capabilityHash??null,accepted:failures.length===0,scope:'finite synthetic DAG mission',criteriaSha256:sha256(criteriaBytes),checkerSha256:sha256(fs.readFileSync(fileURLToPath(import.meta.url))),failures,counts:expected?.counts??null,authority:[],independence:'separate checker implementation; same controller, not external institutional review'};
}

if(process.argv[1]===fileURLToPath(import.meta.url)){
  const args=Object.fromEntries(process.argv.slice(2).reduce((a,x,i,v)=>i%2?a:[...a,[x,v[i+1]]],[]));
  const proof=checkArtifact(fs.readFileSync(args['--artifact']),fs.readFileSync(args['--input']),fs.readFileSync(args['--criteria']));
  if(args['--verify-proof']){const previous=JSON.parse(fs.readFileSync(args['--verify-proof']));if(stable(previous)!==stable(proof))throw Error('PROOF_BYTES_OR_CONTEXT_CHANGED');}
  if(args['--output'])fs.writeFileSync(args['--output'],JSON.stringify(proof,null,2)+'\n');
  console.log(JSON.stringify(proof));if(!proof.accepted)process.exitCode=1;
}
