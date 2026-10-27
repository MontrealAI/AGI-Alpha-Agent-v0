// SPDX-License-Identifier: Apache-2.0
import {Worker} from 'node:worker_threads';
// Fixed batches preserve registered task order; parallelism changes no draws or formulas.
export async function orderedPool(tasks,consume,workers=Number(process.env.FLYWHEEL_WORKERS??6)){
 const count=Math.max(1,Math.min(8,workers,tasks.length)),pool=Array.from({length:count},()=>new Worker(new URL('./worker.mjs',import.meta.url)));
 const call=(w,t)=>new Promise((resolve,reject)=>{const onError=e=>{w.off('message',onMessage);reject(e);};
  const onMessage=r=>{w.off('error',onError);r.ok?resolve(r):reject(new Error(r.error));};w.once('error',onError);w.once('message',onMessage);w.postMessage(t);});
 try{for(let i=0;i<tasks.length;i+=count){const batch=tasks.slice(i,i+count),out=await Promise.all(batch.map((t,k)=>call(pool[k],t)));
  for(let k=0;k<out.length;k++)await consume(out[k],tasks[i+k],i+k);}}
 finally{await Promise.all(pool.map(w=>w.terminate()));}
}
