// SPDX-License-Identifier: Apache-2.0
// Package recorded Python results; never relabel a recording as live execution.
import {readFileSync, writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const here = fileURLToPath(new URL('.', import.meta.url));
const evidence = fileURLToPath(new URL('../evidence/confirmation-v1/', import.meta.url));
const read = name => JSON.parse(readFileSync(evidence + name, 'utf8'));
const data = {summary: read('SUMMARY.json'), samples: read('SAMPLES.json'),
  discovery: read('DISCOVERY.json'), commercial: read('COMMERCIAL.json'), expansion: read('EXPANSION.json')};
if(data.summary.admitted_opportunities !== 0 || data.summary.conventional_ties !== data.summary.fresh_cases)
  throw new Error('This reading edition expects the actual stopped discovery result');
const template = readFileSync(here + 'template.html', 'utf8');
if(template.split('__RECORDED_EVIDENCE__').length !== 2) throw new Error('Ambiguous evidence placeholder');
const html = template.replace('__RECORDED_EVIDENCE__', () => JSON.stringify(data).replaceAll('<', '\\u003c'));
writeFileSync(here + 'index.html', html);
console.log(JSON.stringify({bytes:Buffer.byteLength(html), sha256:createHash('sha256').update(html).digest('hex'),
  status:'source-preview', publicBytesVerified:false}));
