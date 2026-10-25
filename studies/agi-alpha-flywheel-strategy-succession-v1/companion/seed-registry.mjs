// SPDX-License-Identifier: Apache-2.0
import crypto from 'node:crypto';import fs from 'node:fs';import path from 'node:path';
import {makeTask,demoConfiguration,SCOPES} from './scenarios.mjs';
export const MAIN_SEEDS=Array.from({length:12},(_,i)=>1000001+i*100000);
export const DIAGNOSTIC_SEEDS=Array.from({length:12},(_,i)=>5000001+i*100000);
const stable=value=>value&&typeof value==='object'?(Array.isArray(value)?value.map(stable):Object.fromEntries(Object.keys(value).sort().map(k=>[k,stable(value[k])]))):value;
export function semanticTask(task){return stable({kind:task.kind,jobs:[...task.jobs].sort((a,b)=>a.id<b.id?-1:1).map(j=>({id:j.id,duration:j.duration,crew:j.crew,deps:[...j.deps].sort()})),capacity:task.capacity,
 release:Object.fromEntries(task.jobs.map(j=>[j.id,task.release?.[j.id]??0])),locked:task.locked??{},baseline:task.baseline??null,deadline:task.deadline??task.capacity.length,movement_limit:task.kind==='repair'?(task.movement_limit??2304):null});}
export const semanticDigest=task=>crypto.createHash('sha256').update(JSON.stringify(semanticTask(task))).digest('hex');
export function scanDevelopment(directory){const tasks=new Map();
 function inspect(value){if(!value||typeof value!=='object')return;if(value.schema==='release-plan/v1'&&Array.isArray(value.jobs)&&Array.isArray(value.capacity)){tasks.set(semanticDigest(value),value);return;}if(Array.isArray(value))for(const v of value)inspect(v);else for(const v of Object.values(value))inspect(v);}
 function visit(dir){if(!fs.existsSync(dir))return;for(const entry of fs.readdirSync(dir,{withFileTypes:true})){const full=path.join(dir,entry.name);if(entry.isDirectory())visit(full);else if(entry.name.endsWith('.json')){try{inspect(JSON.parse(fs.readFileSync(full,'utf8')));}catch{}}else if(entry.name.endsWith('.jsonl'))for(const line of fs.readFileSync(full,'utf8').split('\n'))if(line.trim()){try{inspect(JSON.parse(line));}catch{}}}}
 visit(directory);return [...tasks.values()];}
export function assertDisjoint(configurations,{development=[]}={}){
 const known=new Map(),seeds=new Map(),records=[],collisions=[];
 const exposed=[...development,...demoConfiguration().tasks,...Object.values(demoConfiguration().qualification).flatMap(x=>[...x.training,...x.validation]),
  ...Array.from({length:85},(_,i)=>makeTask(670000+i,SCOPES[i%3],{prefix:'reserved-load'}))];
 for(const task of exposed){known.set(semanticDigest(task),{role:'public-development',task_id:task.id});if(Number.isInteger(task.fixture_seed))seeds.set(`${task.fixture_seed}:${task.scope}`,{role:'public-development',task_id:task.id});}
 for(const {id,config,role='main'}of configurations){
  const groups=[['confirmation',config.tasks],...Object.entries(config.qualification).flatMap(([stage,data])=>[[`${stage}-training`,data.training],[`${stage}-qualification`,data.validation]])];
  for(const [group,tasks]of groups)for(const task of tasks){const record={stream:id,role,group,task_id:task.id,fixture_seed:task.fixture_seed,scope:task.scope,semantic_sha256:semanticDigest(task)};
   const prior=known.get(record.semantic_sha256),seedKey=`${task.fixture_seed}:${task.scope}`,seedPrior=seeds.get(seedKey);
   if(prior||seedPrior)collisions.push({current:record,prior:prior??seedPrior});known.set(record.semantic_sha256,record);seeds.set(seedKey,record);records.push(record);
  }
 }
 if(collisions.length)throw Error('INPUT_OVERLAP: '+JSON.stringify(collisions.slice(0,5)));
 return {schema:'release-input-registry/v1',main_seeds:MAIN_SEEDS,diagnostic_seeds:DIAGNOSTIC_SEEDS,public_development_problems:exposed.length,
  checked_records:records.length,collisions:[],records,scope:'Exact semantic input equality after removing labels/IDs of the task, not arbitrary graph-isomorphism equivalence. Comparator reuse of one materialized input is intentional pairing.'};
}
