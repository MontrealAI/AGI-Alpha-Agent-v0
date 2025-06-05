// @ts-nocheck
// SPDX-License-Identifier: Apache-2.0
export const defaults={seed:42,pop:80,gen:60,mutations:['gaussian'],adaptive:false};
const MAX_VAL=500;
export function parseHash(h=window.location.hash){
  if(!h || h==='#'){
    try{
      const stored=localStorage.getItem('insightParams');
      if(stored){
        const p=JSON.parse(stored);
        return{
          seed:p.seed??defaults.seed,
          pop:Math.min(p.pop??defaults.pop,MAX_VAL),
          gen:Math.min(p.gen??defaults.gen,MAX_VAL),
          mutations:p.mutations??defaults.mutations,
          adaptive:p.adaptive??defaults.adaptive
        };
      }
    }catch{}
  }
  const q=new URLSearchParams(h.replace(/^#\/?/,''));
  return{
    seed:+q.get('s')||defaults.seed,
    pop:Math.min(+q.get('p')||defaults.pop,MAX_VAL),
    gen:Math.min(+q.get('g')||defaults.gen,MAX_VAL),
    mutations:(q.get('m')||defaults.mutations.join(',')).split(',').filter(Boolean),
    adaptive:q.get('a')==='1'||defaults.adaptive
  };
}
export function toHash(p){
  const q=new URLSearchParams();
  q.set('s',p.seed);q.set('p',p.pop);q.set('g',p.gen);
  if(p.mutations) q.set('m',p.mutations.join(','));
  if(p.adaptive) q.set('a','1');
  return'#/'+q.toString();
}
