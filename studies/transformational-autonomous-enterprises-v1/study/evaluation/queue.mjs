// SPDX-License-Identifier: Apache-2.0
import {Worker} from 'node:worker_threads';
import {sha256,stable} from './checker.mjs';

export class LocalQueue{
  constructor({concurrency=1,capacity=256,role='executor',history=[]}={}){
    if(![1,2].includes(concurrency)||capacity<1||capacity>256)throw Error('RESOURCE_CEILING');
    this.capacity=capacity;this.role=role;this.pending=[];this.records=new Map();this.history=[...history];this.stopped=false;this.slots=[];
    for(let i=0;i<concurrency;i++){
      const slot={worker:new Worker(new URL('./load-worker.mjs',import.meta.url)),ready:false,job:null};this.slots.push(slot);
      slot.worker.on('message',message=>{if(message.ready){slot.ready=true;this.pump();return;}this.finish(slot,message);});
      slot.worker.on('error',error=>{if(slot.job)this.finish(slot,{id:slot.job.id,error:'WORKER_FAILURE:'+error.message});});
    }
  }
  submit(id,mission,{failFirst=false}={}){
    if(this.role!=='executor')return Promise.reject(Error('ROLE_DENIED'));
    if(this.stopped)return Promise.reject(Error('KILL_SWITCH_ACTIVE'));
    const digest=sha256(stable(mission));const old=this.records.get(id);
    if(old){if(old.digest!==digest)return Promise.reject(Error('IDEMPOTENCY_INPUT_MISMATCH'));this.history.push({id,event:'duplicate-returned-existing-promise'});return old.promise;}
    if(this.records.size>=this.capacity)return Promise.reject(Error('QUEUE_CAPACITY'));
    let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});
    const job={id,mission,digest,failFirst,attempt:0,promise,resolve,reject,queuedAt:performance.now()};this.records.set(id,job);this.pending.push(job);this.history.push({id,event:'queued',inputSha256:digest});this.pump();return promise;
  }
  pump(){if(this.stopped)return;for(const slot of this.slots){if(slot.ready&&!slot.job&&this.pending.length){const job=this.pending.shift();slot.job=job;this.history.push({id:job.id,event:'started',attempt:job.attempt});slot.worker.postMessage({id:job.id,mission:job.mission,failFirst:job.failFirst,attempt:job.attempt});}}}
  finish(slot,message){
    const job=slot.job;if(!job||job.id!==message.id)return;slot.job=null;
    if(message.error){this.history.push({id:job.id,event:'attempt-failed',attempt:job.attempt,error:message.error});if(job.attempt<1&&!this.stopped){job.attempt++;this.pending.push(job);}else job.reject(Error(message.error));}
    else{const result={...message,totalLatencyMs:performance.now()-job.queuedAt,attempts:job.attempt+1};this.history.push({id:job.id,event:'completed',attempts:result.attempts,accepted:result.accepted});job.result=result;job.resolve(result);}
    this.pump();
  }
  exportHistory(){return JSON.parse(JSON.stringify(this.history));}
  async stop(){if(this.stopped)return;this.stopped=true;for(const job of this.pending){this.history.push({id:job.id,event:'interrupted-before-start'});job.reject(Error('INTERRUPTED'));}this.pending=[];for(const slot of this.slots){if(slot.job){this.history.push({id:slot.job.id,event:'interrupted',attempt:slot.job.attempt});slot.job.reject(Error('INTERRUPTED'));slot.job=null;}}await Promise.all(this.slots.map(s=>s.worker.terminate()));}
}
