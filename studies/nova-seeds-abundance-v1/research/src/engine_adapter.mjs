// SPDX-License-Identifier: Apache-2.0
import {execute, inspectCompletion} from '../vendor/alpha/examples/successor-capability/out-execute/engine.mjs';
import {installedSource} from '../vendor/alpha/examples/successor-capability/out-execute/source-manifest.mjs';
import {createHash, randomUUID} from 'node:crypto';

export const GEOMETRY = Object.freeze({ticks:4,jobs:4,calibrationTicks:[0,1,2],sampleSlots:[1,2,3],candidateAssignments:2048,utilityScale:100,ttlInclusive:true});
export const SCENARIOS = Object.freeze(['ordinary','capacity-doubled','tight-validity','measurement-drift','demand-drift','reliability-failure','cheap-calibration','expensive-evidence']);
export const hash = value => createHash('sha256').update(typeof value==='string'?value:JSON.stringify(value)).digest('hex');
const clone=value=>structuredClone(value);
const sourcePromise=installedSource();

export function validateMission(mission) {
  if(mission?.schema!=='nova-seeds-mission/v1'||mission.horizon!==4||![1,2].includes(mission.capacity)||![0,1].includes(mission.calibrationDuration)||mission.jobs?.length!==4)throw Error('Unsupported finite mission');
  mission.jobs.forEach((job,i)=>{if(job.id!==`j${i}`||!Number.isSafeInteger(job.utility)||job.utility<1||job.utility>50||![1,2,3].includes(job.ttl)||job.tolerance!==0.25)throw Error('Invalid job');});
  const authority=mission.authority;
  if(authority?.mode!=='fixture'||authority.missionId!==mission.id||JSON.stringify(authority.scope)!==JSON.stringify(['local-synthetic-allocation'])||authority.expiresAfterEpoch!==true||authority.currencyCaps?.USDC!=='0'||authority.currencyCaps?.AGIALPHA!=='0')throw Error('Fresh scoped fixture authority is required');
  return mission;
}

export function planningFeasible(mission,calibrations,slots,{ideaOnly=false}={}) {
  for(let t=1;t<=3;t++){
    const n=slots.filter(s=>s===t).length;
    if(n>mission.capacity || (n&&mission.calibrationDuration&&calibrations[t]))return false;
    if(n&&ideaOnly&&!calibrations[t-1])return false;
  }
  for(let j=0;j<4;j++)if(slots[j]){
    const tick=slots[j];let latest=-10;
    for(let t=0;t<3;t++)if(calibrations[t]&&(t<tick||(!mission.calibrationDuration&&t===tick)))latest=t;
    if(latest<0||tick-latest>mission.jobs[j].ttl)return false;
  }
  return true;
}

export function compileAllocation(missionInput,{ideaOnly=false}={}) {
  const mission=clone(validateMission(missionInput)),ids=['c0','c1','c2','j0','j1','j2','j3'];
  const variables=ids.map(id=>({id,domain:id[0]==='c'?[0,1]:[0,1,2,3]})),costs=[];
  for(let c0=0;c0<2;c0++)for(let c1=0;c1<2;c1++)for(let c2=0;c2<2;c2++)
    for(let j0=0;j0<4;j0++)for(let j1=0;j1<4;j1++)for(let j2=0;j2<4;j2++)for(let j3=0;j3<4;j3++)
      costs.push(planningFeasible(mission,[c0,c1,c2],[j0,j1,j2,j3],{ideaOnly})?0:null);
  return {schema:'out-execute-finite-model/v1',semantics:'finite-nonnegative-integer-min-sum/v1',variables,
    factors:[{id:'physical_schedule',scope:ids,costs},...mission.jobs.map((job,i)=>({id:`unserved_${i}`,scope:[`j${i}`],costs:[100*job.utility,0,0,0]})),...[0,1,2].map(t=>({id:`calibration_${t}`,scope:[`c${t}`],costs:[0,1]}))]};
}

export async function planAllocation(mission,{ideaOnly=false,evidenceRepeats=1,retainProof=false}={}) {
  const started=performance.now(),cpuBefore=process.cpuUsage(),compiled=compileAllocation(mission,{ideaOnly}),compileMs=performance.now()-started;
  const provenance=await sourcePromise,solveStarted=performance.now();
  const state=await execute(compiled,{source:provenance.source,selection:{maxBoundary:0,shortlist:null,horizon:1},budget:1000000});
  const solveMs=performance.now()-solveStarted;
  if(state.status!=='COMPLETE'||state.completion.selection.status!=='OPTIMAL')return {status:state.status,plan:null,reason:state.reason,wallMs:performance.now()-started,cpuMicros:process.cpuUsage(cpuBefore),work:state.work};
  const witness=state.completion.artifact,plan={calibrations:[witness.c0,witness.c1,witness.c2],slots:[witness.j0,witness.j1,witness.j2,witness.j3]};
  const proofStarted=performance.now();
  for(let repetition=0;repetition<evidenceRepeats;repetition++){
    const checked=await inspectCompletion(state.completion);
    if(checked?.completion?.selection?.status!=='OPTIMAL'||checked.completion.digest!==state.completion.digest||!Number.isSafeInteger(checked.acceptance?.factorLookups))throw Error('Independent completion inspection did not return the exact optimal witness');
  }
  const inspectionMs=performance.now()-proofStarted;
  const completionHash=hash(state.completion);
  return {status:'COMPLETE',plan,objective:state.completion.selection.cost,modelDigest:hash(compiled),completionHash,
    completion:retainProof?state.completion:null,compilerSource:provenance.source,countedWork:state.completion.countedWork,
    logicalWork:state.completion.work,compileMs,solveMs,inspectionMs,evidenceRepeats,wallMs:performance.now()-started,cpuMicros:process.cpuUsage(cpuBefore),
    modelBytes:Buffer.byteLength(JSON.stringify(compiled)),proofBytes:Buffer.byteLength(JSON.stringify(state.completion)),authority:'fixture-only-local-synthetic-allocation',physicalTruthEstablished:false};
}

export function conventionalGreedy(mission) {
  validateMission(mission);const slots=[0,0,0,0],calibrations=[1,0,0],remaining=mission.jobs.map((j,i)=>({i,...j})).sort((a,b)=>b.utility-a.utility||a.i-b.i);
  for(let t=1;t<=3;t++){
    let latest=calibrations.map((x,i)=>x?i:-10).filter(i=>i<t||(!mission.calibrationDuration&&i===t)).reduce((a,b)=>Math.max(a,b),-10);
    if(!remaining.some(j=>t-latest<=j.ttl)&&t<3){calibrations[t]=1;latest=t;if(mission.calibrationDuration)continue;}
    let used=0;
    for(let i=0;i<remaining.length&&used<mission.capacity;){if(t-latest<=remaining[i].ttl){slots[remaining[i].i]=t;remaining.splice(i,1);used++;}else i++;}
  }
  return {plan:{calibrations,slots},objective:100*mission.jobs.reduce((s,j,i)=>s+(slots[i]?0:j.utility),0)+calibrations.reduce((a,b)=>a+b,0),assignmentsEvaluated:0};
}

export function scenarioWorld(seed,epoch,scenario) {
  if(!Number.isSafeInteger(seed)||seed<1||!Number.isSafeInteger(epoch)||epoch<0||epoch>=12||!SCENARIOS.includes(scenario))throw Error('Invalid world identity');
  let state=(Math.imul(seed,2654435761)+Math.imul(epoch+1,2246822519))>>>0;
  const rng=()=>{state^=state<<13;state^=state>>>17;state^=state<<5;return (state>>>0)/4294967296;};
  let valueState=Math.imul(seed,1597334677)>>>0;
  const valueRng=()=>{valueState^=valueState<<13;valueState^=valueState>>>17;valueState^=valueState<<5;return (valueState>>>0)/4294967296;};
  const baseUtilities=Array.from({length:4},()=>5+Math.floor(valueRng()*11));
  const jobs=baseUtilities.map((utility,i)=>({id:`j${i}`,utility:scenario==='demand-drift'&&epoch>=6?20-utility:utility,ttl:scenario==='tight-validity'?1:3,tolerance:0.25}));
  const id=`nova-${randomUUID()}`;
  const mission={schema:'nova-seeds-mission/v1',id,horizon:4,capacity:scenario==='capacity-doubled'?2:1,calibrationDuration:scenario==='cheap-calibration'?0:1,jobs,knownModel:{biasConstant:true,calibrationExact:true,noiseBound:0.05},authority:{mode:'fixture',missionId:id,scope:['local-synthetic-allocation'],expiresAfterEpoch:true,currencyCaps:{USDC:'0',AGIALPHA:'0'}}};
  const truth=Array.from({length:4},()=>10+Math.floor(rng()*90)),initialBias=Math.round((rng()*4-2)*100)/100;
  const bias=Array.from({length:4},(_,t)=>initialBias+(scenario==='measurement-drift'&&t>=2?0.8:0));
  const noise=Array.from({length:4},()=>Array.from({length:4},()=>Math.round((rng()-0.5)*0.1*10000)/10000));
  const failedSlots=Array.from({length:4},(_,t)=>scenario==='reliability-failure'&&t>0&&rng()<0.2);
  return {mission,truth,bias,noise,failedSlots,metadata:{seed,epoch,scenario}};
}
