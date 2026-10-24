// SPDX-License-Identifier: Apache-2.0
import {planAllocation} from './engine_adapter.mjs';
const used=new Set();
process.send({ready:true,node:process.version,usage:process.resourceUsage()});
process.on('message',async message=>{
  if(message.stats){process.send({id:message.id,stats:process.resourceUsage(),cpu:process.cpuUsage()});return;}
  if(message.close){process.exit(0);return;}
  const {id,mission,options,lease}=message;
  try{
    if(used.has(id)||lease?.missionId!==mission.id||lease.expiresAt<Date.now()||lease.scope!=='local-synthetic-allocation')throw Error('Missing, expired, mismatched or replayed fixture lease');
    used.add(id);
    const result=await planAllocation(mission,options);
    if(lease.expiresAt<Date.now())throw Error('Fixture lease elapsed during computation');
    process.send({id,result,maxRssKiB:process.resourceUsage().maxRSS});
  }catch(error){process.send({id,error:{name:error.name,message:error.message}});}
});
