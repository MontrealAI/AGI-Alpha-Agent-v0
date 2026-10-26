// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {configurationsFor} from './design.mjs';
const root=dirname(fileURLToPath(import.meta.url)),market=resolve(root,'..'),freezePath=resolve(root,'freeze.json');
const sha=x=>createHash('sha256').update(x).digest('hex');
if(!process.argv.includes('--reviewed'))throw Error('Root and independent pre-outcome review required');
if(existsSync(freezePath))throw Error('Refusing to replace an existing freeze');
const protocolPath=resolve(root,'protocol.json'),protocol=JSON.parse(readFileSync(protocolPath,'utf8'));
if(Date.now()>Date.parse(protocol.research_cutoff_utc))throw Error('Research cutoff already passed');
if(configurationsFor(protocol).length!==128)throw Error('Exact configuration product changed');
const gatePath=resolve(root,protocol.successor_gate.no_go_record);
if(sha(readFileSync(gatePath))!==protocol.successor_gate.no_go_record_sha256)throw Error('Second-asset NO-GO gate changed');
if(protocol.successor_gate.status!=='NO_GO_AFTER_BOUNDED_DISCOVERY'||protocol.successor_gate.candidate_manifest!==null||
  protocol.successor_gate.generated_earmarks_cents!==0||protocol.fixed.nextAsset!==null)throw Error('Untested successor cannot enter the campaign');
protocol.status='FROZEN_BEFORE_FRESH_EXTENSION_OUTCOMES';writeFileSync(protocolPath,JSON.stringify(protocol,null,2)+'\n');
const paths=['src/market.mjs','canonical/shadow-ledger.mjs','canonical/automated-costs.mjs',
  'reporting/market-expose.mjs','reporting/instrumentation.diff','reporting/source-manifest.json',
  'reporting/results-01/completion.json','protocol/freeze.json','exploratory/freeze.json','policy-diagnostic/freeze.json',
  'protocol/parameter-manifest.json','protocol/external-sources.json','protocol/production-joint-summary.json',
  '../protocol/succession-envelope.json','../review/second-capability-gate.json',
  '../review/competitor-account-outcome-audit.json','../review/prefreeze-funding-view-audit.json',
  'deployment-robustness/protocol.json','deployment-robustness/MODEL_ADDENDUM.md','deployment-robustness/funding.mjs',
  'deployment-robustness/design.mjs','deployment-robustness/run.mjs','deployment-robustness/test-funding.mjs',
  'deployment-robustness/execute-bounded.py','../review/prefreeze-deployment-robustness-review.json',
  'deployment-robustness/freeze.mjs','deployment-robustness/README.md'];
const files=paths.map(path=>{const data=readFileSync(resolve(market,path));return {path,bytes:data.length,sha256:sha(data)};});
const freeze={schema:'agi-alpha-bounded-deployment-robustness-freeze/v1',utc:new Date().toISOString(),
  priorOutcomesKnown:true,freshExtensionOutcomesInspected:false,files,
  configurations:128,freshSeeds:24,pairedWorlds:3072,enterpriseRuns:9216,
  budgetSeconds:{wall:120,cpu:120},cutoff:protocol.research_cutoff_utc,
  secondAsset:null,secondAssetDecision:'NO_GO',earmarkedGeneratedFundsCents:0,
  unknownIncrementalDiscoveryCostCents:null,
  boundary:'One user-authorized bounded fresh-seed extension; unchanged economic core, no second purchase, unknown discovery cost retained.'};
writeFileSync(freezePath,JSON.stringify(freeze,null,2)+'\n');
process.stdout.write(JSON.stringify({path:freezePath,utc:freeze.utc,sha256:sha(readFileSync(freezePath))})+'\n');
