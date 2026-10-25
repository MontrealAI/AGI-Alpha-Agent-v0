// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync} from 'node:fs';
import {runProject,retainedParent,constructChild,childImpact} from './capability.mjs';
const p=JSON.parse(readFileSync(process.argv[2],'utf8')),output=process.argv[3];
const start=performance.now(),cpu=process.cpuUsage();const initial=await runProject(p,{arm:'flywheel'});let changed=JSON.parse(JSON.stringify(p));changed.cycle=2;changed.components[0].content+='\n// synthetic changed evidence\n';
const fresh=await retainedParent(changed,initial.state),child=await constructChild(fresh.parent),impact=await childImpact(changed,fresh.parent,initial.state,child);
const directOnly=[...fresh.parent.changed],qualifiedDirect=JSON.stringify(directOnly.sort())===JSON.stringify([...impact.invalidated].sort());
const cases=[{case:'failed-direct-only-invalidator',candidate:'direct-only-v0',accepted:qualifiedDirect,observed_direct:directOnly,required_transitive:impact.invalidated,decision:qualifiedDirect?'UNEXPECTED_PASS':'REJECT',reason:'Changed descendants would retain stale dependency evidence.'}];
for(const field of ['source_url','source_sha256']){const x=JSON.parse(JSON.stringify(p));x.cycle=2;x.components[0][field]=field==='source_url'?x.components[0][field]+'?provenance=changed':'f'.repeat(64);const parent=await retainedParent(x,initial.state);const evidence=await childImpact(x,parent.parent,initial.state,child);cases.push({case:'provenance-only-'+field,accepted:parent.parent.changed.includes(x.components[0].id)&&evidence.invalidated.length>1,affected:evidence.invalidated});}
const corrupted=JSON.parse(JSON.stringify(initial.state));corrupted.index.C01.hash='f'.repeat(64);let refused=false;try{await retainedParent(p,corrupted);}catch{refused=true;}cases.push({case:'corrupted-parent',accepted:refused});
const end=process.cpuUsage(cpu);const result={stage:'DEVELOPMENT_ONLY_BEFORE_FREEZE',cases,qualified:!qualifiedDirect&&cases.slice(1).every(c=>c.accepted),construction_wall_ms:performance.now()-start,construction_cpu_ms:(end.user+end.system)/1000,failed_candidate:'direct-only-v0',cost_scope:'Observed deterministic development/qualification process only. Program design and model/tool interaction cost unknown.'};
writeFileSync(output,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
