// SPDX-License-Identifier: Apache-2.0
import {pathToFileURL} from 'node:url';
import fs from 'node:fs';

function missionErrors(mission) {
  const errors=[];
  if (!mission || mission.horizon!==4) errors.push('unsupported-horizon');
  if (![1,2].includes(mission?.capacity)) errors.push('unsupported-capacity');
  if (![0,1].includes(mission?.calibrationDuration)) errors.push('unsupported-calibration-duration');
  if (!Array.isArray(mission?.jobs) || mission.jobs.length!==4) errors.push('expected-four-jobs');
  else {
    if (new Set(mission.jobs.map(j=>j?.id)).size!==4) errors.push('duplicate-job-id');
    for (const job of mission.jobs) {
      if (!job || typeof job.id!=='string' || !Number.isInteger(job.utility) || job.utility<0 || !Number.isInteger(job.ttl) || job.ttl<0 || !Number.isFinite(job.tolerance) || job.tolerance<0) errors.push('invalid-job');
    }
  }
  return errors;
}

function planningCheck(mission,plan,ideaOnly) {
  const errors=missionErrors(mission);
  if (!Array.isArray(plan?.calibrations) || plan.calibrations.length!==3 || plan.calibrations.some(x=>x!==0&&x!==1)) errors.push('invalid-calibration-flags');
  if (!Array.isArray(plan?.slots) || plan.slots.length!==4 || plan.slots.some(x=>!Number.isInteger(x)||x<0||x>3)) errors.push('invalid-job-slots');
  if (errors.length) return {valid:false,errors};
  const lastCalibration=[];
  for (let tick=1;tick<=3;tick++) {
    const jobs=plan.slots.flatMap((slot,i)=>slot===tick?[i]:[]);
    if (jobs.length>mission.capacity) errors.push(`capacity:${tick}`);
    if (jobs.length && mission.calibrationDuration===1 && plan.calibrations[tick]===1) errors.push(`calibration-overlap:${tick}`);
    let last=null;
    for (let c=0;c<3;c++) if (plan.calibrations[c]===1 && (c<tick || (c===tick && mission.calibrationDuration===0))) last=c;
    lastCalibration[tick]=last;
    if (jobs.length && last===null) errors.push(`uncalibrated:${tick}`);
    if (jobs.length && ideaOnly && plan.calibrations[tick-1]!==1) errors.push(`idea-refresh:${tick}`);
    for (const i of jobs) if (last!==null && tick-last>mission.jobs[i].ttl) errors.push(`expired:${mission.jobs[i].id}`);
  }
  return {valid:errors.length===0,errors,lastCalibration};
}

export function expertSchedule(publicMission,{ideaOnly=false,predictedBias=null}={}) {
  const errors=missionErrors(publicMission);
  if (predictedBias!==null && (!Array.isArray(predictedBias) || predictedBias.length!==4 || predictedBias.some(x=>!Number.isFinite(x)))) errors.push('invalid-predicted-bias');
  if (errors.length) throw new Error(errors.join(','));
  const total=publicMission.jobs.reduce((s,j)=>s+j.utility,0);
  const noiseMargin=publicMission.knownModel?.noiseBound??0.05;
  if (!Number.isFinite(noiseMargin) || noiseMargin<0) throw new Error('invalid-noise-bound');
  let best=null,assignmentsEvaluated=0,feasibleAssignments=0;
  for (let flags=0;flags<8;flags++) {
    const calibrations=[(flags>>2)&1,(flags>>1)&1,flags&1];
    const calibrationCount=calibrations.reduce((a,b)=>a+b,0);
    for (let index=0;index<256;index++) {
      assignmentsEvaluated++;
      const slots=[(index>>6)&3,(index>>4)&3,(index>>2)&3,index&3];
      const plan={calibrations,slots};
      const checked=planningCheck(publicMission,plan,ideaOnly);
      if (!checked.valid) continue;
      feasibleAssignments++;
      const plannedUtility=publicMission.jobs.reduce((sum,job,i)=>sum+(slots[i]===0?0:job.utility),0);
      const predictedUtility=publicMission.jobs.reduce((sum,job,i)=>{
        const tick=slots[i];
        if (tick===0) return sum;
        if (predictedBias!==null && Math.abs(predictedBias[tick]-predictedBias[checked.lastCalibration[tick]])+noiseMargin>job.tolerance) return sum;
        return sum+job.utility;
      },0);
      const objective=100*(total-predictedUtility)+calibrationCount;
      if (best===null || objective<best.objective) best={plan:{calibrations:[...calibrations],slots:[...slots]},objective,predictedUtility,plannedUtility,calibrationCount};
    }
  }
  return {...best,assignmentsEvaluated,feasibleAssignments,method:predictedBias===null?'independent-direct-enumeration':'independent-delayed-qc-enumeration',predictedBias:predictedBias===null?null:[...predictedBias]};
}

export function evaluateSchedule(world,plan,{ideaOnly=false}={}) {
  const mission=world?.mission;
  const checked=planningCheck(mission,plan,ideaOnly);
  const errors=[...checked.errors];
  if (!Array.isArray(world?.truth)||world.truth.length!==4||world.truth.some(x=>!Number.isFinite(x))) errors.push('invalid-truth');
  if (!Array.isArray(world?.bias)||world.bias.length!==4||world.bias.some(x=>!Number.isFinite(x))) errors.push('invalid-bias');
  if (!Array.isArray(world?.noise)||world.noise.length!==4||world.noise.some(row=>!Array.isArray(row)||row.length!==4||row.some(x=>!Number.isFinite(x)))) errors.push('invalid-noise');
  if (!Array.isArray(world?.failedSlots)||world.failedSlots.length!==4||world.failedSlots.some(x=>typeof x!=='boolean')) errors.push('invalid-failed-slots');
  if (errors.length) return {valid:false,utility:0,completedJobs:0,failures:0,attemptedJobs:0,resourceTicks:0,calibrations:0,jobOutcomes:[],errors};
  const jobOutcomes=mission.jobs.map((job,i)=>{
    const tick=plan.slots[i];
    if (tick===0) return {id:job.id,scheduled:false,useful:false,utility:0,reason:'not-scheduled'};
    const calibrationTick=checked.lastCalibration[tick];
    const observed=world.truth[i]+world.bias[tick]+world.noise[i][tick];
    const corrected=observed-world.bias[calibrationTick];
    const error=Math.abs(corrected-world.truth[i]);
    const failedSlot=world.failedSlots[tick];
    const useful=!failedSlot && error<=job.tolerance;
    return {id:job.id,scheduled:true,tick,calibrationTick,observed,corrected,truth:world.truth[i],error,tolerance:job.tolerance,failedSlot,useful,utility:useful?job.utility:0,reason:failedSlot?'slot-failure':error>job.tolerance?'measurement-error':'useful'};
  });
  const attemptedJobs=jobOutcomes.filter(j=>j.scheduled).length;
  const completedJobs=jobOutcomes.filter(j=>j.useful).length;
  const calibrations=plan.calibrations.reduce((a,b)=>a+b,0);
  const occupiedSampleTicks=new Set(plan.slots.filter(t=>t>0)).size;
  return {valid:true,utility:jobOutcomes.reduce((s,j)=>s+j.utility,0),completedJobs,failures:attemptedJobs-completedJobs,attemptedJobs,resourceTicks:occupiedSampleTicks+mission.calibrationDuration*calibrations,calibrations,jobOutcomes,errors:[]};
}

function selfCheck() {
  const mission={horizon:4,capacity:1,calibrationDuration:1,jobs:[5,10,15,7].map((utility,i)=>({id:`j${i}`,utility,ttl:3,tolerance:.25}))};
  const world={mission,truth:[1,2,3,4],bias:[.2,.2,.2,.2],noise:Array.from({length:4},()=>[0,0,0,0]),failedSlots:[false,false,false,false]};
  const expert=expertSchedule(mission);
  if(expert.predictedUtility!==32 || expert.calibrationCount!==1 || expert.assignmentsEvaluated!==2048) throw new Error('base optimum mismatch');
  if(evaluateSchedule(world,expert.plan).utility!==32) throw new Error('base replay mismatch');
  const idea=expertSchedule(mission,{ideaOnly:true});
  if(idea.predictedUtility!==25 || idea.calibrationCount!==2) throw new Error('idea optimum mismatch');
  const drift={...world,bias:[.2,.2,.8,.8]};
  if(evaluateSchedule(drift,expert.plan).utility>=32) throw new Error('drift not detected');
  if(evaluateSchedule(drift,idea.plan,{ideaOnly:true}).utility!==25) throw new Error('refresh did not survive drift');
  const adaptive=expertSchedule(mission,{predictedBias:[0,0,.8,.8]});
  if(adaptive.predictedUtility!==25 || adaptive.calibrationCount!==2 || evaluateSchedule(drift,adaptive.plan).utility!==25) throw new Error('delayed-QC optimum mismatch');
  const adaptiveConstant=expertSchedule(mission,{predictedBias:[3,3,3,3]});
  if(adaptiveConstant.predictedUtility!==32 || adaptiveConstant.calibrationCount!==1) throw new Error('constant delayed-QC optimum mismatch');
  if(evaluateSchedule(world,{calibrations:[1,0,0],slots:[1,1,0,0]}).valid) throw new Error('overcapacity accepted');
  if(evaluateSchedule(world,{calibrations:[1,1,0],slots:[1,0,0,0]}).valid) throw new Error('overlap accepted');
  if(evaluateSchedule(world,{calibrations:[0,0,0],slots:[1,0,0,0]}).valid) throw new Error('uncalibrated accepted');
  const tight={...mission,jobs:mission.jobs.map(j=>({...j,ttl:1}))};
  if(evaluateSchedule({...world,mission:tight},{calibrations:[1,0,0],slots:[0,0,2,0]}).valid) throw new Error('expiry accepted');
  const expanded={...mission,capacity:2};
  if(expertSchedule(expanded).predictedUtility!==37) throw new Error('expanded optimum mismatch');
  const freecal={...mission,calibrationDuration:0};
  if(!evaluateSchedule({...world,mission:freecal},{calibrations:[0,1,0],slots:[1,2,3,0]}).valid) throw new Error('zero-duration simultaneous calibration rejected');
  const failed={...world,failedSlots:[false,true,false,false]};
  if(evaluateSchedule(failed,{calibrations:[1,0,0],slots:[1,0,0,0]}).completedJobs!==0) throw new Error('failed slot accepted');
  return {passed:14,scope:'independent analytic examples; not population evidence'};
}

if (process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  if(process.argv[2]==='--self-check') process.stdout.write(JSON.stringify(selfCheck(),null,2)+'\n');
  else {
    const input=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
    const result=input.world?evaluateSchedule(input.world,input.plan,input.options):expertSchedule(input.mission,input.options);
    process.stdout.write(JSON.stringify(result,null,2)+'\n');
  }
}
