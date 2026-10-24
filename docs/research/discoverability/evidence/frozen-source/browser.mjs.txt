// SPDX-License-Identifier: Apache-2.0
// Public local UI: actual workbench construction; synthetic observations; inert imports.
import { createCompiler, inspectProgram, executeProgram, canonical } from './compiler.mjs';
import { digitalFault, mixtureAssay, acquireSynthetic } from './domains.mjs';
import { networkProblem, acquireNetwork } from './heldout.mjs';
import { createDiscoverabilityWorkbench, discoverabilityMission } from './workbench-adapter.mjs';
import { executeObservations } from './execution.mjs';
import { digest } from '../../docs/assets/successor/engine.mjs';

export async function boot({sourceHash,sourceManifest}) {
  const $ = id => document.getElementById(id);
  const compiler = createCompiler({strategy:'cached'});
  const runtime = createDiscoverabilityWorkbench({compiler});
  let active = null, pack = null, report = null, problem = null, acquisition = null, receipt = null, successor = false;
  let validation=null,totalAcquisitionUnits=0,totalCompilerWork=0,acquisitionCount=0;
  const details = value => { $('details').textContent=JSON.stringify(value,null,2); };
  const status = text => { $('status').textContent=text; };
  const setBusy = busy => {
    $('construct').disabled=busy; $('stop').disabled=!busy; $('restore').disabled=busy;
    $('mission').disabled=busy; $('condition').disabled=busy;
    $('acquire').disabled=busy || report?.status!=='COMPILED';
    $('invalidate').disabled=busy || report?.status!=='COMPILED';
    $('next').disabled=busy; $('export').disabled=busy || !pack;
  };
  const descriptions = {
    digital:'Construct a probe program that distinguishes six digital-module conditions despite shared offset and drift.',
    mixture:'Build a spectral contrast that separates nine mixture compositions or their release decisions despite offset and drift.',
    successor:'Inspect the held-out network: infer which degraded edge needs repair from routed measurements with shared clock nuisance.'
  };
  const renderProblem = () => {
    $('mission-description').textContent=descriptions[$('mission').value];
    successor=false; report=null; pack=null; acquisition=null; receipt=null; validation=null;
    $('program-table').hidden=true; $('empty').hidden=false;
    $('empty').textContent='Ready to construct a new program from primitive channels.';
    $('result-title').textContent='A capability you can inspect.';
    $('mode').textContent='Ready for a new execution';
    ['metric-experiments','metric-cost','metric-quality'].forEach(id=>$(id).textContent='—');
    details({state:'READY',sourceHash});setBusy(false);
  };
  const selectedProblem = () => {
    const family=$('mission').value,noise=$('condition').value==='noisy'?5:1;
    let value = family==='digital'?digitalFault({noise,goal:successor?'health':'repair'}):
      family==='mixture'?mixtureAssay({noise,goal:successor?'quantify':'disposition'}):
      networkProblem({requirement:'repair',clockOrder:successor?2:1,extendedGrammar:successor});
    value=JSON.parse(JSON.stringify(value));
    if(family==='successor'&&noise>1)value.channels.forEach(c=>c.noise=noise);
    if($('condition').value==='budget')value.missionBudget=1;
    return value;
  };
  const showReport = () => {
    $('empty').hidden=report?.status==='COMPILED';
    $('mode').textContent='Newly executed · finite synthetic model';
    $('result-title').textContent=report.status==='COMPILED'?'The missing distinction is measurable.':
      report.status==='UNIDENTIFIABLE_WITHIN_GRAMMAR'?'The permitted observations cannot decide.':
      report.status==='OVER_MISSION_BUDGET'?'A valid method exceeds the mission budget.':'Search stopped without a certificate.';
    $('empty').textContent=report.status==='UNIDENTIFIABLE_WITHIN_GRAMMAR'?
      'At least one pair of incompatible decisions has overlapping observations for every legal contrast. Expand the permitted construction or change the measurement conditions.':
      report.status==='OVER_MISSION_BUDGET'?'The least-cost permitted program costs more than the declared acquisition allowance. No execution is admitted.':
      'Incomplete search is inconclusive. Increase the declared work allowance to try again.';
    const program=report.program;
    $('metric-experiments').textContent=program?.experiments.length??'—';
    $('metric-cost').textContent=program?.totalCost??'—';
    $('metric-quality').textContent='—';
    $('program-table').hidden=!program;
    $('program-body').replaceChildren();
    for(const [i,e] of (program?.experiments||[]).entries()) {
      const row=document.createElement('tr');
      const vals=[String(i+1),e.weights.map((w,j)=>w?String(w)+' × '+problem.channels[j].id:null).filter(Boolean).join(' + '),'±'+e.radius,String(e.cost)];
      for(const val of vals){const cell=document.createElement('td');cell.textContent=val;row.append(cell);}
      $('program-body').append(row);
    }
    details({construction:report,sourceHash,workbench:{integrityDigest:pack.integrityDigest,evaluation:pack.evaluation,
      economics:pack.economics},limits:pack.result.limits});
    status(report.status+' · '+report.work.used.toLocaleString()+' logical work units · '+(report.libraryHit?'structural cache reused':'constructed a structural library')+'. Independent admission remains HOLD.');
    setBusy(false);
  };
  async function construct() {
    if(active)return;
    pack=null;report=null;acquisition=null;receipt=null;validation=null;
    problem=selectedProblem();active=new AbortController();setBusy(true);
    status('Constructing legal contrasts and checking decision separation…');
    $('mode').textContent='Executing now · bounded local work';
    try {
      pack=await runtime.run(discoverabilityMission(problem,{budget:2000000,name:'Discoverability Ω',language:'en'}),
        {sourceHash,signal:active.signal,onProgress:phase=>status('Running: '+phase+'…')});
      report=pack.result.evidence.construction;
      totalCompilerWork+=report.work.used;
      showReport();
    } catch(error) {
      status(error.message==='CANCELLED'?'Stopped. No capability was admitted. You can start a fresh bounded run.':'Run failed: '+error.message);
      $('mode').textContent=error.message==='CANCELLED'?'Stopped by operator':'Execution failed';
      details({status:'FAILED',error:String(error.message),admission:'HOLD',sourceHash});
    } finally {active=null;setBusy(false);}
  }
  async function acquire() {
    if(report?.status!=='COMPILED'||active)return;
    acquisition=null;receipt=null;validation=null;
    $('metric-quality').textContent='—';$('mode').textContent='Executing now · synthetic acquisitions';
    active=new AbortController();setBusy(true);
    try {
      const program=report.program;inspectProgram(problem,program);
      let passed=0,checks=[],acquisitions=[];
      if(acquisitionCount+problem.worlds.length>128)throw Error('SESSION_ACQUISITION_LIMIT: export this evidence, then reload for a new session');
      for(const [i,world] of problem.worlds.entries()) {
        if(active.signal.aborted)throw Error('CANCELLED');
        const sample=$('mission').value==='successor'?acquireNetwork(problem,program,world.id):
          acquireSynthetic(problem,program,world.id,{nuisanceScale:13+i,errorSign:i%3-1});
        acquisitions.push(sample);totalAcquisitionUnits+=program.totalCost;acquisitionCount++;
        const decision=executeProgram(problem,program,sample.observations);
        const correct=decision.status==='DECIDED'&&decision.decision===world.goal;
        checks.push({world:world.id,expected:world.goal,actual:decision.decision,status:decision.status,correct});
        validation={acquisitions,checks,perDecisionAcquisitionUnits:program.totalCost,performedAcquisitionUnits:acquisitions.length*program.totalCost,state:'IN_PROGRESS'};
        if(correct)passed++;if(i===problem.worlds.length-1)acquisition=sample;
        await new Promise(resolve=>setTimeout(resolve,0));
      }
      if(active.signal.aborted)throw Error('CANCELLED');
      const delivered=await executeObservations(pack,acquisition.observations);
      if(active.signal.aborted)throw Error('CANCELLED');
      receipt=delivered;
      validation={acquisitions,checks,perDecisionAcquisitionUnits:program.totalCost,performedAcquisitionUnits:acquisitions.length*program.totalCost,state:'COMPLETE'};
      $('metric-quality').textContent=passed+'/'+problem.worlds.length;
      $('result-title').textContent=passed===problem.worlds.length?'The constructed program answers the mission.':'An execution failed its original acceptance test.';
      $('mode').textContent='Newly executed · synthetic acquisitions';
      status(passed+' of '+problem.worlds.length+' world decisions passed. This check performed '+validation.performedAcquisitionUnits+' acquisition units; the displayed '+program.totalCost+' is per decision. Session total: '+totalAcquisitionUnits+'. Synthetic checks do not validate a physical sensor.');
      details({validation,latestAcquisition:acquisition,delivery:receipt,construction:report,usage:{compilerLogicalUnits:totalCompilerWork,performedAcquisitionUnits:totalAcquisitionUnits},
        admission:'HOLD',settlement:'NOT_CONNECTED',sourceHash});
    } catch(error){if(validation)validation.state='STOPPED';$('mode').textContent='Acquisition stopped';status('Acquisition stopped: '+error.message);details({error:error.message,validation,performedAcquisitionUnits:totalAcquisitionUnits,acquisitionCount,admission:'HOLD'});}
    finally {active=null;setBusy(false);}
  }
  $('construct').addEventListener('click',construct);
  $('acquire').addEventListener('click',acquire);
  $('stop').addEventListener('click',()=>{active?.abort();status('Stop requested. The next bounded checkpoint will cancel work.');});
  $('mission').addEventListener('change',renderProblem);
  $('condition').addEventListener('change',renderProblem);
  $('invalidate').addEventListener('click',()=>{
    const changed=JSON.parse(JSON.stringify(problem));changed.nuisance=changed.nuisance.map((row,i)=>[...row,i*i]);
    try{inspectProgram(changed,report.program);status('Unexpected stale-scope acceptance. This run must not be promoted.');}
    catch(error){status('Stale inheritance rejected: the uncertainty model changed. Reuse the construction method; qualify a new program.');
      details({test:'CHANGED_NUISANCE_SCOPE',expected:'REJECT',observed:error.message,inheritedCapability:'bounded contrast construction',admission:'HOLD'});}
  });
  $('next').addEventListener('click',()=>{successor=!successor;construct();});
  $('export').addEventListener('click',async ()=>{
    if(!pack)return;
    const savedPack=pack;
    const body={schema:'discoverability.browser-session.v1',mode:'RECORDED_EXPORT',pack,acquisition,execution:receipt,validation,usage:{compilerLogicalUnits:totalCompilerWork,performedAcquisitionUnits:totalAcquisitionUnits,acquisitionCount},sourceHash};
    const envelope={...body,integrityDigest:await digest('discoverability-browser-session',body)};
    const blob=new Blob([JSON.stringify(envelope,null,2)+'\n'],{type:'application/json'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='discoverability-'+savedPack.frozen.missionDigest.slice(0,12)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    status('Exported an integrity-bound workbench pack. It carries no operator authority or settlement authorization.');
  });
  $('restore').addEventListener('click',()=>{if(!active)$('restore-file').click();});
  $('restore-file').addEventListener('change',async event=>{
    const file=event.target.files?.[0];if(!file)return;
    if(active){status('Finish or stop current work before restoring evidence.');event.target.value='';return;}
    active=new AbortController();setBusy(true);
    try{
      if(file.size>2000000)throw Error('PACK_SIZE_LIMIT');
      const value=JSON.parse(await file.text());
      let original=value,recordedExecution=null;
      if(value.schema==='discoverability.browser-session.v1') {
        const {integrityDigest,...body}=value;
        if(integrityDigest!==await digest('discoverability-browser-session',body))throw Error('SESSION_INTEGRITY');
        original=value.pack;recordedExecution=value.execution;
        if(value.sourceHash!==original.frozen.sourceHash)throw Error('SESSION_SOURCE_BINDING');
        if(recordedExecution) {
          const {integrityDigest:executionHash,...executionBody}=recordedExecution;
          if(executionHash!==await digest('discoverability-execution',executionBody))throw Error('EXECUTION_INTEGRITY');
          if(recordedExecution.workbenchPackDigest!==original.integrityDigest||recordedExecution.sourceHash!==original.frozen.sourceHash)throw Error('EXECUTION_BINDING');
          const program=original.result.evidence.construction.program;
          if(recordedExecution.programDigest!==await digest('discoverability-program',program))throw Error('PROGRAM_BINDING');
          const replay=executeProgram(original.spec.inputs.problem,program,recordedExecution.observations);
          if(canonical(replay)!==canonical(recordedExecution.result))throw Error('RECORDED_DECISION');
        }
      }
      const history=await runtime.inspectPack(original);
      if(active.signal.aborted)throw Error('CANCELLED');
      pack=null;report=null;acquisition=null;receipt=null;setBusy(false);
      $('mode').textContent='Recorded import · inert historical evidence';
      $('result-title').textContent='Integrity checked. Authority not inherited.';
      $('program-table').hidden=true;$('empty').hidden=false;
      $('empty').textContent='This imported record is available for inspection only. Construct a new instrument to execute current source.';
      ['metric-experiments','metric-cost','metric-quality'].forEach(id=>$(id).textContent='—');
      details({history,importedRecord:value,recordedExecution});status('Imported history is unauthenticated. Active proofs and authority are empty.');
    }catch(error){status('Import rejected: '+error.message);}
    finally{active=null;setBusy(false);event.target.value='';}
  });
  $('source-identity').textContent='Run discoverability-20261022-v1 · source closure SHA-256 '+sourceHash+' · frozen compiler ece8f2aa1480';
  details({sourceHash,sourceManifest,admission:'HOLD',settlement:'NOT_CONNECTED'});
  status('Ready. The next click runs the compiler on this device.');setBusy(false);
}
