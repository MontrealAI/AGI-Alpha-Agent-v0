// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..'),target=resolve(root,'protocol/freeze.json');
if(existsSync(target))throw Error('Freeze exists; preserve it and write an explicit amendment instead');
if(!process.argv.includes('--reviewed'))throw Error('Explicit root review required before pre-outcome freeze');
const protocolPath=resolve(root,'protocol/protocol.json'),protocol=JSON.parse(readFileSync(protocolPath,'utf8'));
protocol.status='FROZEN_BEFORE_PRIMARY_MARKET_OUTCOMES';writeFileSync(protocolPath,JSON.stringify(protocol,null,2)+'\n');
const paths=['src/market.mjs','src/run.mjs','src/parameters.mjs','src/freeze.mjs','tests/test_market.mjs','MODEL.md',
  'canonical/shadow-ledger.mjs','canonical/automated-costs.mjs','canonical/PROVENANCE.json','protocol/protocol.json',
  'protocol/parameter-manifest.json','protocol/external-sources.json','protocol/production-joint-summary.json',
  'protocol/production-inherited-bridge.json'];
const files=paths.map(path=>{const b=readFileSync(resolve(root,path));return {path,bytes:b.length,
  sha256:createHash('sha256').update(b).digest('hex')};});
const freeze={schema:'agi-alpha-market-freeze/v1',utc:new Date().toISOString(),marketPrimaryOutcomesInspected:false,
  productionOutputsAlreadyMeasuredAndDisclosed:true,files,
  boundary:'Market protocol/source frozen after calibration, executed production and synthetic software controls, before primary market outcomes. No calibration/validation confusion or prospective technical source novelty is implied.'};
writeFileSync(target,JSON.stringify(freeze,null,2)+'\n');
process.stdout.write(JSON.stringify({path:target,sha256:createHash('sha256').update(readFileSync(target)).digest('hex'),files:files.length,utc:freeze.utc})+'\n');
