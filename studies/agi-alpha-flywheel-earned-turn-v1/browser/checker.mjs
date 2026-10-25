export function checkResponse(net,b,x){
 const errors=[];
 if(!net||!Number.isSafeInteger(net.nodes)||net.nodes!==64||!(net.ground>0)||!Array.isArray(net.edges)||!Array.isArray(b)||b.length!==net.nodes||!Array.isArray(x)||x.length!==net.nodes)return {valid:false,errors:['SHAPE'],operations:0};
 if([...b,...x].some(v=>!Number.isFinite(v)))return {valid:false,errors:['NON_FINITE'],operations:0};
 const balance=x.map(v=>v*net.ground);let operations=net.nodes;
 for(const e of net.edges){
  if(!Number.isSafeInteger(e.u)||!Number.isSafeInteger(e.v)||e.u<0||e.v<0||e.u>=net.nodes||e.v>=net.nodes||!(e.g>0)||!Number.isFinite(e.g)){errors.push('EDGE_SCOPE');continue;}
  const flow=e.g*(x[e.u]-x[e.v]);balance[e.u]+=flow;balance[e.v]-=flow;operations+=4;
 }
 let residual=0,scale=1;
 for(let i=0;i<net.nodes;i++){residual=Math.max(residual,Math.abs(balance[i]-b[i]));scale=Math.max(scale,Math.abs(b[i]));operations+=4;}
 const relative=residual/scale;operations++;
 if(relative>1e-9)errors.push('BALANCE_RESIDUAL');
 const injected=b.reduce((s,v)=>s+v,0),grounded=x.reduce((s,v)=>s+v*net.ground,0);operations+=3*net.nodes;
 if(Math.abs(injected-grounded)>1e-8*Math.max(1,Math.abs(injected)))errors.push('GLOBAL_CONSERVATION');
 if(x.some(v=>v< -1e-10))errors.push('NEGATIVE_RESPONSE');
 return {valid:errors.length===0,errors,max_absolute_residual:residual,relative_residual:relative,injected,grounded,operations,scope:'Synthetic grounded conductance grid; balance and conservation, not physical validation or general forward-error proof.'};
}
export function compareResponses(a,b){return Math.max(...a.map((v,i)=>Math.abs(v-b[i])))<=1e-9;}
