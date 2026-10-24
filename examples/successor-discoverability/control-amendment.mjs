import {createCompiler} from './compiler.mjs';import{digitalFault}from'./domains.mjs';
const p=JSON.parse(JSON.stringify(digitalFault()));p.id=true;
let record;
try{await createCompiler().compile(p);throw Error('INVALID_ID_ACCEPTED');}
catch(e){if(e.message==='INVALID_ID_ACCEPTED')throw e;record={schema:'discoverability-control-amendment/v1',runId:'discoverability-20261022-v1',recordedAt:new Date().toISOString(),originalControl:'malformed input',originalFailure:'Test fixture attempted to mutate a frozen domain before entering compiler validation.',correction:'Clone the generated finite problem, then set id=true and call unchanged frozen compiler.',compilerCommit:'ece8f2aa1480ec7b50f633b7893a11c3f22de894',observed:e.message,passed:e.message.includes('identity'),changedAcceptance:false,repeatedLoadRuns:false};}
console.log(JSON.stringify(record,null,2));if(!record.passed)process.exitCode=1;
