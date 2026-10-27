export const SIDE=8, NODE_COUNT=64, VERSION='earned-turn-browser/1';
export class Meter {
  constructor(limit=250000){this.limit=limit;this.operations=0;this.counts={};this.parent_calls=0;}
  add(kind,n=1){this.operations+=n;this.counts[kind]=(this.counts[kind]||0)+n;if(this.operations>this.limit)throw Error('OPERATION_BUDGET_EXHAUSTED');}
}
export function validateConfig(c){if(!c||!Number.isFinite(c.load)||c.load<0.1||c.load>5||!Number.isFinite(c.strength)||c.strength<0.05||c.strength>3)throw Error('OUTSIDE_DECLARED_SCOPE');}
export function network(){
 const edges=[];
 for(let r=0;r<SIDE;r++)for(let c=0;c<SIDE;c++){
  const u=r*SIDE+c;
  if(c+1<SIDE)edges.push({u,v:u+1,g:1+((u*7)%5)/10});
  if(r+1<SIDE)edges.push({u,v:u+SIDE,g:1+((u*3)%5)/10});
 }
 return {schema:'grounded-grid/v1',nodes:NODE_COUNT,side:SIDE,ground:0.25,edges};
}
export function demand(kind,scale){
 const b=Array(NODE_COUNT).fill(0);
 const map=kind==='A'?[[18,1],[45,.8],[35,.4]]:kind==='B'?[[20,1.3],[42,.95],[10,.55]]:[[27,1.1],[49,1],[14,.7],[36,.35]];
 for(const [i,w] of map)b[i]=w*scale;
 return b;
}
export function matrix(net,m){
 const A=Array.from({length:net.nodes},()=>Array(net.nodes).fill(0));
 for(let i=0;i<net.nodes;i++){A[i][i]=net.ground;m.add('matrix',1);}
 for(const {u,v,g}of net.edges){A[u][u]+=g;A[v][v]+=g;A[u][v]-=g;A[v][u]-=g;m.add('matrix',4);}
 return A;
}
export async function factor(A,m,checkpoint=async()=>{}){
 const n=A.length,L=Array.from({length:n},()=>Array(n).fill(0));
 for(let i=0;i<n;i++){
  await checkpoint('factor-row');
  for(let j=0;j<=i;j++){
   let sum=A[i][j];
   for(let k=0;k<j;k++){sum-=L[i][k]*L[j][k];m.add('factor-multiply-subtract',2);}
   if(i===j){if(!(sum>1e-12))throw Error('NON_POSITIVE_DEFINITE');L[i][j]=Math.sqrt(sum);m.add('factor-sqrt',1);}
   else{L[i][j]=sum/L[j][j];m.add('factor-division',1);}
  }
 }
 return L;
}
export function triangular(L,b,m,parent=false){
 if(parent)m.parent_calls++;
 const n=b.length,y=Array(n).fill(0),x=Array(n).fill(0);
 for(let i=0;i<n;i++){let s=b[i];for(let j=0;j<i;j++){s-=L[i][j]*y[j];m.add('triangular-multiply-subtract',2);}y[i]=s/L[i][i];m.add('triangular-division',1);}
 for(let i=n-1;i>=0;i--){let s=y[i];for(let j=i+1;j<n;j++){s-=L[j][i]*x[j];m.add('triangular-multiply-subtract',2);}x[i]=s/L[i][i];m.add('triangular-division',1);}
 return x;
}
export function selectedEdges(net,x,strength){
 return net.edges.map((e,index)=>({index,flow:Math.abs(e.g*(x[e.u]-x[e.v]))})).sort((a,b)=>b.flow-a.flow||a.index-b.index).slice(0,2).map(e=>({...net.edges[e.index],index:e.index,delta:strength,source_flow:e.flow}));
}
export function updated(net,changes){const copy=structuredClone(net);for(const c of changes){if(!(c.delta>0)||c.delta>3)throw Error('UNSUPPORTED_UPDATE');copy.edges[c.index].g+=c.delta;}return copy;}
export async function makeUpdate(net,L,changes,m,checkpoint=async()=>{}){
 if(changes.length!==2)throw Error('UNSUPPORTED_UPDATE_RANK');
 const W=[];
 for(const c of changes){await checkpoint('parent-build-call');const u=Array(net.nodes).fill(0);u[c.u]=1;u[c.v]=-1;W.push(triangular(L,u,m,true));}
 const S=changes.map((a,i)=>changes.map((b,j)=>{m.add('schur',3);return (i===j?1/a.delta:0)+W[j][a.u]-W[j][a.v];}));
 return {schema:'woodbury-positive-rank2/v1',changes,W,smallL:await factor(S,m,checkpoint)};
}
export function solveUpdate(L,asset,b,m){
 const y=triangular(L,b,m,true),z=asset.changes.map(e=>{m.add('project',1);return y[e.u]-y[e.v];});
 const q=triangular(asset.smallL,z,m),x=y.slice();
 for(let i=0;i<x.length;i++)for(let j=0;j<q.length;j++){x[i]-=asset.W[j][i]*q[j];m.add('update-apply',2);}
 return x;
}
export function inspectParent(asset,networkHash,sourceHash){
 if(!asset||asset.network_hash!==networkHash||asset.source_hash!==sourceHash||asset.status!=='VALID_LOCAL'||!Array.isArray(asset.L)||asset.L.length!==NODE_COUNT)throw Error('STALE_OR_INAPPLICABLE_PARENT');
 if(asset.L.some((row,i)=>!Array.isArray(row)||row.length!==NODE_COUNT||row.some(v=>!Number.isFinite(v))||!(row[i]>0)))throw Error('INVALID_PARENT_FACTOR');
}
