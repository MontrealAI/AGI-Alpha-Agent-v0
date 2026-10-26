// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=dirname(fileURLToPath(import.meta.url)),market=resolve(root,'..'),target=resolve(root,'freeze.json');
if(existsSync(target))throw Error('Exploratory freeze already exists');
if(!process.argv.includes('--reviewed'))throw Error('Root review required');
const p=resolve(root,'protocol.json'),protocol=JSON.parse(readFileSync(p,'utf8'));
protocol.status='FROZEN_BEFORE_EXPLORATORY_OUTCOMES_AFTER_PRIMARY';writeFileSync(p,JSON.stringify(protocol,null,2)+'\n');
const paths=['src/market.mjs','canonical/shadow-ledger.mjs','canonical/automated-costs.mjs','protocol/freeze.json',
  'protocol/parameter-manifest.json','protocol/production-joint-summary.json','exploratory/protocol.json',
  'exploratory/MODEL_ADDENDUM.md','exploratory/run.mjs','exploratory/freeze.mjs'];
const files=paths.map(path=>{const b=readFileSync(resolve(market,path));return{path,bytes:b.length,
  sha256:createHash('sha256').update(b).digest('hex')};});
const record={schema:'agi-alpha-exploratory-market-freeze/v1',utc:new Date().toISOString(),primaryOutcomesKnown:true,
  exploratoryOutcomesInspected:false,files,boundary:'Explicit postprimary exploration; no primary replacement, selection of favorable outcomes or source amendment.'};
writeFileSync(target,JSON.stringify(record,null,2)+'\n');
process.stdout.write(JSON.stringify({path:target,utc:record.utc,sha256:createHash('sha256').update(readFileSync(target)).digest('hex')})+'\n');
