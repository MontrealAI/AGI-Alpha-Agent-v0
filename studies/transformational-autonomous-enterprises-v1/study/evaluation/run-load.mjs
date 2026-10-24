// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {LocalQueue} from './queue.mjs';
import {sourceManifest} from '../enterprise/compiler.mjs';
import {sha256} from './checker.mjs';
const here=path.dirname(fileURLToPath(import.meta.url)),missions=JSON.parse(fs.readFileSync(path.join(here,'missions.json'))).slice(0,40),out=path.join(here,'../results/load');fs.mkdirSync(out,{recursive:true});
const rows=[];
for(const concurrency of [1,2])for(const volume of [8,32,128])for(let repeat=0;repeat<2;repeat++){
  const start=performance.now(),cpu=process.cpuUsage(),queue=new LocalQueue({concurrency,capacity:256});
  const results=await Promise.all(Array.from({length:volume},(_,i)=>queue.submit('load-'+i,{...missions[i%missions.length],missionId:'load-'+i})));
  const wall=performance.now()-start,latencies=results.map(r=>r.totalLatencyMs).sort((a,b)=>a-b),history=queue.exportHistory();await queue.stop();
  const row={concurrency,volume,repeat,accepted:results.filter(r=>r.accepted).length,correct:results.filter(r=>r.correct).length,failureRate:results.filter(r=>!r.accepted).length/volume,wallMs:wall,throughputPerSecond:volume*1000/wall,p50LatencyMs:latencies[Math.floor(volume*.5)],p95LatencyMs:latencies[Math.min(volume-1,Math.floor(volume*.95))],candidateOperations:results.reduce((s,r)=>s+r.operations,0),hashBytes:results.reduce((s,r)=>s+r.hashBytes,0),qualificationCases:results.reduce((s,r)=>s+(r.qualification?.qualificationCases??0),0),cpuMicroseconds:process.cpuUsage(cpu),peakRSSKiB:process.resourceUsage().maxRSS,humanInterventionsDuringRun:0,costPerAcceptedDollar:null,includesWorkerStartup:true,execution:'local Node worker threads; not physical Fleet machines'};rows.push(row);fs.writeFileSync(path.join(out,`c${concurrency}-n${volume}-r${repeat}.json`),JSON.stringify({row,results,history},null,2));console.log(JSON.stringify(row));
}
const summary={schema:'tae.load-results.v1',candidateSource:sourceManifest(),criteriaSha256:sha256(fs.readFileSync(path.join(here,'criteria.json'))),rows,interpretation:'Execution volume only. Finite mission-set expansion is measured separately. Dollar costs and complete oversight time remain unknown.'};fs.writeFileSync(path.join(out,'summary.json'),JSON.stringify(summary,null,2)+'\n');
