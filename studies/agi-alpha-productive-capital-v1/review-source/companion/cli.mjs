// SPDX-License-Identifier: Apache-2.0
import {readFileSync} from 'node:fs';
import {runProject,retainedParent,constructChild,validateProject,childImpact} from './capability.mjs';
const request=JSON.parse(readFileSync(0,'utf8'));
const start=process.hrtime.bigint(),cpu=process.cpuUsage();
try{
 let result;
 if(request.operation==='construct'){
  const p=await retainedParent(request.project,request.previous??null);const c=await constructChild(p.parent);
  result={parent:p.parent,child:c,parent_call:p.parent_call};
 }else if(request.operation==='validate'){result={valid:validateProject(request.project)};}
 else result=await runProject(request.project,request.options);
 const used=process.cpuUsage(cpu);
 console.log(JSON.stringify({ok:true,result,node_cpu_ms:(used.user+used.system)/1000,node_wall_ms:Number(process.hrtime.bigint()-start)/1e6,peak_rss_bytes:process.resourceUsage().maxRSS*1024,node_version:process.version}));
}catch(error){const used=process.cpuUsage(cpu);console.log(JSON.stringify({ok:false,error:error.message,node_cpu_ms:(used.user+used.system)/1000,node_wall_ms:Number(process.hrtime.bigint()-start)/1e6,peak_rss_bytes:process.resourceUsage().maxRSS*1024,node_version:process.version}));process.exitCode=1;}
