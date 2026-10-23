// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { verifyJourney, compactEvm, tokenFlow } from './verify-journey.mjs';
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const read = name => JSON.parse(fs.readFileSync(path.join(root, name)));
const journey = read('study/results/journey.json');
const evm = read('evidence/contracts/writer4-parent-lifecycle.json');
const acceptance = verifyJourney(journey, evm);
const packages = read('study/results/journey-inputs/examples.json');
const workspaces = Object.fromEntries(['parent','successor'].map(name => [name, packages[name].result.workspace]));
const evidence = { schema: 'tae.interface-evidence.v1', mode: 'recorded execution replay', summary: read('study/results/scored-v2/summary.json'), journey, sourceScope: read('study/results/source-scope.json'), evm: { ...compactEvm(evm), observedLiveRead: read('evidence/contracts/live-readonly-observation-proxy.json') }, tokenFlow: tokenFlow(evm), acceptance, workspaces, currentProof: null, authority: [] };
fs.writeFileSync(path.join(root, 'study/results/joined-acceptance.json'), JSON.stringify(acceptance, null, 2) + '\n');
fs.writeFileSync(path.join(root, 'study/interface/evidence.js'), '/* Recorded evidence; not a live run. */\nwindow.TAE_EVIDENCE=' + JSON.stringify(evidence).replace(/</g, '\\u003c') + ';\n');
console.log(JSON.stringify({ accepted: acceptance.accepted, missions: acceptance.joins.map(j => j.missionId), output: 'study/interface/evidence.js' }));
