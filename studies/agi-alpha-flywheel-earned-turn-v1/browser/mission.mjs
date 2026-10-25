import {createWorkbench} from '../runtime/vendor/examples/successor-workbench/engine.mjs';
import {digest} from '../runtime/vendor/docs/assets/successor/engine.mjs';
import {Meter,network,demand,matrix,factor,triangular,selectedEdges,updated,makeUpdate,solveUpdate,inspectParent,validateConfig} from './core.mjs';
import {checkResponse,compareResponses} from './checker.mjs';
export const TITLES=['Map the response','Meet a new demand','Build the successor','Use the new capability'];
export const accountFor=i=>i===2?'improvement':'service';
export const reserveFor=i=>i===2?40000:i===0?120000:20000;
export async function hash(value){return digest('earned-turn-local',JSON.stringify(value));}
export const manifest={id:'earned-turn-browser',version:1,en:'Build a reusable network response instrument',fr:'Construire un instrument réutilisable de réponse de réseau',scope:'Four finite synthetic grounded-network missions in this browser; distinct from the native SciPy experiment.',artifact:'network-result.json'};
function validate(input){if(!input||!Number.isSafeInteger(input.phase)||input.phase<0||input.phase>3||typeof input.run_id!=='string'||typeof input.before_hash!=='string')throw Error('MISSION_SCOPE');if(typeof input.config_json!=='string')throw Error('CONFIG_JSON');validateConfig(JSON.parse(input.config_json));}
export async function inspectPack(pack){return createWorkbench([{manifest,validate,execute:async()=>{throw Error('INSPECTION_ONLY');}}]).inspectPack(pack);}
export async function executeMission(state,phase,{sourceHash,signal,onProgress=()=>{},onCheckpoint=async()=>{}}){
 if(phase!==state.stage||phase<0||phase>3)throw Error('CURSOR_MISMATCH');
 validateConfig(state.config);
 const beforeHash=await hash({run_id:state.run_id,stage:state.stage,config:state.config,accepted:state.accepted.map(r=>r.result_hash),parent:state.parent?.id||null,successor:state.successor?.id||null});
 const next=structuredClone(state);let record=null;
 const adapter={manifest,validate,async execute(input,checkpoint){
  if(input.before_hash!==beforeHash)throw Error('START_STATE_BINDING');
  await checkpoint('Identify');
  const net=network(),netHash=await hash(net),m=new Meter(reserveFor(phase)),rm=new Meter(200000);
  const started=performance.now();let x,b,workNet=net,parentUsage=[],constructionCalls=0,executionCalls=0,retained=null;
  if(phase===0){
   await checkpoint('Out-Design');b=demand('A',state.config.load);
   const L=await factor(matrix(net,m),m,checkpoint);x=triangular(L,b,m);
   const payload={network_hash:netHash,source_hash:sourceHash,status:'VALID_LOCAL',L};
   payload.id=await hash(payload);next.parent=payload;retained={id:payload.id,kind:'factorization',purpose:'Answer new loads on this exact network',scope:'64 nodes; positive grounded conductances; unchanged network hash',authority:[],admission:'Correctness only in this finite browser demonstration'};
  }else{
   inspectParent(state.parent,netHash,sourceHash);
   const {id,...p}=state.parent;if(id!==await hash(p))throw Error('PARENT_INTEGRITY');
   m.add('retrieval-block64',Math.ceil(JSON.stringify(state.parent).length/64));
   await checkpoint('Out-Learn');
   if(phase===1){
    b=demand('B',state.config.load);x=triangular(state.parent.L,b,m,true);executionCalls=1;
    parentUsage.push({asset:state.parent.id,operation:'solve fresh B demand',calls:1});
   }else{
    const priorB=state.accepted.find(r=>r.phase===1);
    if(!priorB?.valid||priorB.result_hash!==await hash({network:priorB.network,b:priorB.b,x:priorB.x}))throw Error('PRIOR_ACCEPTED_RESPONSE_BINDING');
    if(phase===2){
     b=priorB.b;const changes=selectedEdges(net,priorB.x,state.config.strength);workNet=updated(net,changes);
     await checkpoint('Out-Think');
     const asset=await makeUpdate(net,state.parent.L,changes,m,checkpoint);constructionCalls=m.parent_calls;
     asset.parent_id=state.parent.id;asset.parent_network_hash=netHash;asset.network_hash=await hash(workNet);asset.source_response_hash=priorB.result_hash;asset.source_hash=sourceHash;asset.status='VALID_LOCAL';asset.id=await hash(asset);
     next.successor=asset;
     x=solveUpdate(state.parent.L,asset,b,m);executionCalls=m.parent_calls-constructionCalls;
     parentUsage.push({asset:state.parent.id,operation:'construct two response columns for the successor',calls:constructionCalls},{asset:state.parent.id,operation:'qualify updated response instrument',calls:executionCalls});
     retained={id:asset.id,kind:'positive-rank2-update',parent_id:state.parent.id,source_response_hash:priorB.result_hash,changes,scope:'The exact two positive conductance updates derived from accepted Mission B',authority:[],admission:'Correctness only in this finite browser demonstration'};
    }else{
     const asset=state.successor;
     if(!asset||asset.parent_id!==state.parent.id||asset.source_hash!==sourceHash||asset.source_response_hash!==priorB.result_hash||asset.status!=='VALID_LOCAL')throw Error('STALE_SUCCESSOR');
     const {id,...payload}=asset;if(id!==await hash(payload))throw Error('SUCCESSOR_INTEGRITY');
     workNet=updated(net,asset.changes);if(await hash(workNet)!==asset.network_hash)throw Error('UPDATED_NETWORK_BINDING');
     m.add('retrieval-block64',Math.ceil(JSON.stringify(asset).length/64));b=demand('D',state.config.load);x=solveUpdate(state.parent.L,asset,b,m);executionCalls=1;
     parentUsage.push({asset:state.parent.id,operation:'solve fresh D demand through the successor',calls:1},{asset:asset.id,operation:'apply retained network update',calls:1});
    }
   }
  }
  await checkpoint('Out-Execute');
  const verified=checkResponse(workNet,b,x);m.add('independent-edge-check',verified.operations);if(!verified.valid)throw Error('INDEPENDENT_CHECK_REFUSED');
  const candidateMs=performance.now()-started;
  await checkpoint('Out-Strategise');
  const refStart=performance.now();let referenceL=next.reference_factor;
  if(phase===0||phase===2)referenceL=await factor(matrix(workNet,rm),rm,checkpoint);
  if(!referenceL)throw Error('REFERENCE_STATE');
  if(phase===1||phase===3)rm.add('retrieval-block64',Math.ceil(JSON.stringify(referenceL).length/64));
  const refX=triangular(referenceL,b,rm),refCheck=checkResponse(workNet,b,refX);rm.add('independent-edge-check',refCheck.operations);
  if(!refCheck.valid||!compareResponses(x,refX))throw Error('REFERENCE_DISAGREEMENT');
  next.reference_factor=referenceL;
  const referenceMs=performance.now()-refStart;
  const resultHash=await hash({network:workNet,b,x});
  record={phase,mission:['A','B','C','D'][phase],title:TITLES[phase],valid:true,network:workNet,b,x,result_hash:resultHash,checker:verified,retained,
   parent_usage:parentUsage,parent_construction_calls:constructionCalls,parent_execution_calls:executionCalls,
   costs:{account:accountFor(phase),operations:m.operations,counts:m.counts,browser_elapsed_ms:candidateMs,
    reference_operations:rm.operations,reference_elapsed_ms:referenceMs,reference_kind:'Conventional direct Cholesky, reused on unchanged network; refactor only after network change',
    accounting:'Declared scalar arithmetic plus retrieval/checking units; timings include JavaScript and workbench checkpoints, not CPU cycles, cash or research-investment recovery.'},
   admission:{correctness:'PASS',product:'NOT_ESTABLISHED_BY_THIS_DEMO',investment:'UNMEASURED_FULL_RESEARCH_COST',authority:[]}};
  await checkpoint('Out-Evolve');
  return {decision:'VERIFIED_LOCAL_RESULT',summary:{mission:record.mission,valid:true,parent_used:parentUsage.length>0,retained:retained?.kind||null},
   evidence:{result_hash:resultHash,before_hash:beforeHash,parent_usage:parentUsage,checker_json:JSON.stringify(verified),admission:record.admission},
   artifacts:[{name:'network-result.json',type:'application/json',content:JSON.stringify(record,null,2)+'\n'}],
   limits:['Fresh browser-local arithmetic, separate from native SciPy confirmation.','The graph is synthetic: computed response is not physical infrastructure.','Independent checker implementation shares this authoring context; no external certification.','Conventional factorization and Woodbury methods are available to every comparator.','No new production authority, authenticated executor, payment or live settlement.']};
 }};
 const wb=createWorkbench([adapter]);
 const spec={schema:'successor-workbench/v1',family:manifest.id,name:'AGI ALPHA · Earned Turn',language:'en',owner:'local-demo-owner',rights:{dataClass:'synthetic',source:'Bundled 8 by 8 grounded grid and bounded editable load',license:'Apache-2.0'},reviewMinutes:10,inputs:{phase,run_id:state.run_id,before_hash:beforeHash,config_json:JSON.stringify(state.config)}};
 const pack=await wb.run(spec,{sourceHash,signal,onProgress,onCheckpoint});
 await wb.inspectPack(pack);record.pack=pack;
 next.accepted.push(record);next.stage=phase+1;return {next,record};
}
