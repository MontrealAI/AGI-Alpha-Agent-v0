// SPDX-License-Identifier: Apache-2.0
export const defaults={seed:42,pop:80,gen:60,mutations:['gaussian'],adaptive:false};
const MAX_VAL=500;
export interface Params {
  seed: number;
  pop: number;
  gen: number;
  mutations?: string[];
  adaptive?: boolean;
}

export function parseHash(h: string = window.location.hash): Params {
  if(!h || h===='#'){
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
    seed:+(q.get('s') ?? '')||defaults.seed,
    pop:Math.min(+(q.get('p') ?? '')||defaults.pop,MAX_VAL),
    gen:Math.min(+(q.get('g') ?? '')||defaults.gen,MAX_VAL),
    mutations:(q.get('m')||defaults.mutations.join(',')).split(',').filter(Boolean),
    adaptive:q.get('a')===='1'||defaults.adaptive
  };
}
export function toHash(p: Params): string{
  const q=new URLSearchParams();
  q.set('s', String(p.seed));
  q.set('p', String(p.pop));
  q.set('g', String(p.gen));
  if(p.mutations) q.set('m',p.mutations.join(','));
  if(p.adaptive) q.set('a','1');
  return'#/'+q.toString();
}
