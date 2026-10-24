// SPDX-License-Identifier: Apache-2.0
// Authored after the ece8f2aa compiler/reference freeze; no producer imports.
// Finite synthetic network tomography, not measurements of a deployed network.
export const HOLDOUT_ID='network-tomography-post-freeze-20261022';
export const FROZEN_COMPILER_COMMIT='ece8f2aa1480ec7b50f633b7893a11c3f22de894';
export const FROZEN_COMPILER_SHA256='746853fe817f7f98e4e41a6534c87f1949acc150e9742d935637d56b6e03f898';
export const FROZEN_REFERENCE_SHA256='ee44edad7224cdb58cc4aa0e132416efb2904d95eebd96af93fefcd0082a1812';
export const GRAPH=Object.freeze({
 nodes:Object.freeze(['source','north','south','target']),
 edges:Object.freeze([
  Object.freeze({id:'source-north',ends:['source','north'],baseDelay:5}),
  Object.freeze({id:'source-south',ends:['source','south'],baseDelay:5}),
  Object.freeze({id:'north-target',ends:['north','target'],baseDelay:5}),
  Object.freeze({id:'south-target',ends:['south','target'],baseDelay:5}),
  Object.freeze({id:'north-south',ends:['north','south'],baseDelay:5})
 ]),
 routes:Object.freeze([
  Object.freeze({id:'route-north',edges:[0,2]}),
  Object.freeze({id:'route-south',edges:[1,3]}),
  Object.freeze({id:'route-east-cross',edges:[0,4,3]}),
  Object.freeze({id:'route-west-cross',edges:[1,4,2]})
 ])
});
const states=()=>[{id:'healthy',edge:null,penalty:0},...GRAPH.edges.flatMap((e,i)=>[20,40].map(penalty=>({id:e.id+'-'+penalty,edge:i,penalty})))];
const latencies=state=>GRAPH.routes.map(route=>route.edges.reduce((sum,i)=>sum+GRAPH.edges[i].baseDelay+(state.edge===i?state.penalty:0),0));
function intended(state,requirement) {
 if(requirement==='repair')return state.edge===null?'no-repair':GRAPH.edges[state.edge].id+':'+state.penalty;
 const r=latencies(state);return r[0]<=r[1]?'retain-north':'divert-south';
}
export function networkProblem({requirement='route',clockOrder=1,extendedGrammar=false}={}) {
 if(!['route','repair'].includes(requirement)||![1,2].includes(clockOrder)||typeof extendedGrammar!=='boolean')throw new TypeError('heldout options');
 const channels=[{id:'clock-before',cost:1,noise:1},...GRAPH.routes.map(r=>({id:r.id,cost:1,noise:1})),{id:'clock-after',cost:1,noise:1}];
 return {schema:'discoverability.problem.v1',id:'network-'+requirement+'-clock'+clockOrder+(extendedGrammar?'-extended':''),
  channels,worlds:states().map(state=>({id:state.id,goal:intended(state,requirement),signal:[0,...latencies(state),0]})),
  nuisance:channels.map((_,i)=>Array.from({length:clockOrder+1},(_,j)=>i**j)),
  grammar:extendedGrammar?{maxSupport:4,weightLimit:3,maxL1:8}:{maxSupport:3,weightLimit:2,maxL1:4},
  missionBudget:12};
}
export function networkTruth(worldId,requirement='route') {
 const state=states().find(w=>w.id===worldId);if(!state)throw new TypeError('unknown heldout world');
 return {worldId,edge:state.edge===null?null:GRAPH.edges[state.edge].id,penalty:state.penalty,latencies:latencies(state),decision:intended(state,requirement)};
}
export function acquireNetwork(problem,program,worldId,{actualClockOrder=problem.nuisance[0].length-1}={}) {
 const state=states().find(w=>w.id===worldId);if(!state||![1,2].includes(actualClockOrder))throw new TypeError('heldout acquisition');
 const intrinsic=[0,...latencies(state),0],observations=[],raw=[];
 for(let k=0;k<program.experiments.length;k++) {
  const coeff=[17+3*k,-4+k,2],weights=program.experiments[k].weights;
  const readings=weights.map((w,i)=>{
   if(!w)return null;
   const drift=Array.from({length:actualClockOrder+1},(_,j)=>coeff[j]*i**j).reduce((a,b)=>a+b,0);
   // Every experiment makes fresh reads. Half-unit errors are within the declared unit interval.
   const numerator=2*(intrinsic[i]+drift)+((3*i+2*k)%5-2);
   return {channel:problem.channels[i].id,numerator,denominator:2};
  });
  const numerator=readings.reduce((s,r,i)=>s+(r?weights[i]*r.numerator:0),0);
  observations.push({numerator,denominator:2});raw.push({experiment:k,readings});
 }
 return {mode:'NEWLY_EXECUTED_SYNTHETIC',worldId,actualClockOrder,observations,raw,
  disclosure:'Forward graph and rational sensor calculation execute now; no physical network, external worker or market execution.'};
}

