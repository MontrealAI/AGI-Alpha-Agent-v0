// SPDX-License-Identifier: Apache-2.0
// Node-only adapter. Scientific/browser modules do not import this file.
import {spawn} from 'node:child_process';
import readline from 'node:readline';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
export function createChecker({python='python',script=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../review/check.py'),timeoutMs=2000}={}){
 const process=spawn(python,[script],{stdio:['pipe','pipe','pipe']}),pending=[];let errors='';
 process.stderr.on('data',chunk=>{errors+=chunk.toString();});
 const lines=readline.createInterface({input:process.stdout});
 lines.on('line',line=>{const request=pending.shift();if(!request)return;clearTimeout(request.timer);try{request.resolve(JSON.parse(line));}catch(error){request.reject(error);}});
 process.on('error',error=>{for(const p of pending.splice(0)){clearTimeout(p.timer);p.reject(error);}});
 let exited=false;process.on('exit',code=>{exited=true;for(const p of pending.splice(0)){clearTimeout(p.timer);p.reject(Error(`CHECKER_EXIT_${code}: ${errors}`));}});
 return {check(task,result){return new Promise((resolve,reject)=>{if(exited){reject(Error('CHECKER_UNAVAILABLE'));return;}const request={resolve,reject,timer:null};request.timer=setTimeout(()=>{const index=pending.indexOf(request);if(index>=0)pending.splice(index,1);reject(Error('CHECKER_TIMEOUT'));process.kill('SIGKILL');},timeoutMs);pending.push(request);process.stdin.write(JSON.stringify({task,result})+'\n');});},
  close(){if(exited)return Promise.resolve();process.stdin.end();return new Promise(resolve=>process.once('exit',resolve));}};
}
