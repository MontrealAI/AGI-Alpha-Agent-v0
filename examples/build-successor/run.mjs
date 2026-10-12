// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { buildPack, jobBriefs } from './model.mjs';
const output = path.resolve(process.argv[2] || 'successor-build-output');
const engine = fs.readFileSync(new URL('../../docs/assets/successor/engine.mjs', import.meta.url));
const pack = await buildPack({ engineSourceHash: createHash('sha256').update(engine).digest('hex') });
fs.mkdirSync(output, { recursive: false });
for (const [name, value] of Object.entries({ 'successor-build-pack.json': JSON.stringify(pack,null,2)+'\n', 'request.json': JSON.stringify(pack.request,null,2)+'\n', 'job-briefs.md': jobBriefs(pack) })) fs.writeFileSync(path.join(output,name),value,{flag:'wx'});
console.log(JSON.stringify({output, jobs:pack.compilation.graph.nodes.length, correctness:pack.evaluation.correctness, admission:pack.admission.decision, authority:pack.admission.authority, spentBaseUnits:'0'},null,2));
