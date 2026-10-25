// SPDX-License-Identifier: Apache-2.0
export function rng(seed){let x=seed>>>0;return ()=>{x^=x<<13;x^=x>>>17;x^=x<<5;return (x>>>0)/4294967296;};}
export function generateDevelopment(seed,{count=12,capacity=3,kind='plan',regime='mixed'}={}){
 const random=rng(seed),jobs=[];
 for(let i=0;i<count;i++){
  const deps=[];for(let j=0;j<i;j++){const p=regime==='chains'?(j===i-1?.75:0):regime==='wide'?.04:.12;if(random()<p)deps.push(`J${j+1}`);}
  jobs.push({id:`J${i+1}`,duration:1+Math.floor(random()*9),crew:random()<.25?2:1,deps});
 }
 const calendar=Array(96).fill(capacity);if(kind==='repair'){const start=5+Math.floor(random()*5),end=start+5+Math.floor(random()*5);for(let t=start;t<end;t++)calendar[t]=Math.max(1,capacity-1);}
 return {schema:'release-plan/v1',id:`development-${seed}-${kind}-${regime}`,kind,jobs,capacity:calendar,release:{},locked:{},public_or_synthetic:'synthetic',planning_only:true};
}
