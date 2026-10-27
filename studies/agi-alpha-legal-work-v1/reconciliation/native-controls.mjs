// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {verify} from './package.mjs';
const text='Café 🌌',hash=x=>createHash('sha256').update(x).digest('hex');
const sample={schema:'legal-reconciliation/v1',decision:'TEXT_RECONCILIATION_ONLY',professional_acceptance:'unknown',legal_or_playbook_conclusions:[],proposed_revisions:[],documents:{original:text,revised:text},source_hashes:{original:hash(text),revised:hash(text)},amendments:[],operations:[{kind:'equal',original_span:{document:'original',start:0,end:Array.from(text).length,quote:text},revised_span:{document:'revised',start:0,end:Array.from(text).length,quote:text}}]};
verify(sample);
for(const kind of ['invented','insert','delete','replace']){const p=structuredClone(sample);p.operations[0].kind=kind;assert.throws(()=>verify(p));}
{const p=structuredClone(sample);p.source_hashes.extra=hash('');assert.throws(()=>verify(p),/HASH_SET/);}
{const p=structuredClone(sample);p.operations[0].original_span.end=text.length;assert.throws(()=>verify(p),/SPAN/);}
{const p=structuredClone(sample);p.professional_acceptance='accepted';assert.throws(()=>verify(p),/SCOPE/);}
console.log(JSON.stringify({controls:8,passed:true}));
