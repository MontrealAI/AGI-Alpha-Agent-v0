// SPDX-License-Identifier: Apache-2.0
import { canonical, parseBounded } from '../../docs/assets/successor/engine.mjs';
export const DRAFT_SCHEMA = 'alpha-discovery-draft/v1';
const roles = ['baseline','alternative','candidate'];
function keys(v, expected) { if (!v || typeof v !== 'object' || Array.isArray(v) || Object.keys(v).sort().join('|') !== [...expected].sort().join('|')) throw Error('DRAFT_SCHEMA'); }
function text(v) { if (typeof v !== 'string' || v.length > 2000) throw Error('DRAFT_TEXT'); }
function choice(v, choices) { if (!choices.includes(v)) throw Error('DRAFT_CHOICE'); }
// Draft fields deliberately retain raw strings, including incomplete numbers. They cannot be analyzed or executed.
export function validateDraft(draft) {
  keys(draft,['schema','state','authority','language','step','input']);
  if (draft.schema !== DRAFT_SCHEMA || draft.state !== 'partial-unvalidated' || draft.authority !== 'none') throw Error('DRAFT_VERSION');
  choice(draft.language,['en','fr']); if (!Number.isInteger(draft.step) || draft.step < 0 || draft.step > 3) throw Error('DRAFT_STEP');
  const v=draft.input; keys(v,['schema','mission','changed','baseline','alternative','candidate','rights','evidence','constraints','metrics']);
  if(v.schema !== 'alpha-discovery/v1') throw Error('DRAFT_INPUT');
  for(const k of ['mission','changed',...roles,'rights'])text(v[k]);
  if(!Array.isArray(v.evidence)||v.evidence.length>24||!Array.isArray(v.constraints)||v.constraints.length<1||v.constraints.length>12||!Array.isArray(v.metrics)||v.metrics.length<5||v.metrics.length>12)throw Error('DRAFT_ROWS');
  v.evidence.forEach(r=>{keys(r,['kind','claim','reference','basis','supports']);choice(r.kind,['research','expertise','experiment','lesson','change']);choice(r.basis,['illustrative','supplied-report']);text(r.claim);text(r.reference);if(!Array.isArray(r.supports)||r.supports.length>4||new Set(r.supports).size!==r.supports.length)throw Error('DRAFT_SUPPORTS');r.supports.forEach(s=>choice(s,[...roles,'change']));});
  v.constraints.forEach(r=>{keys(r,['name','status','reference']);text(r.name);text(r.reference);choice(r.status,['unknown','reported-pass','reported-fail']);});
  if(['benefit','cost','proof','risk','human'].some(c=>!v.metrics.some(r=>r.category===c)))throw Error('DRAFT_CATEGORY');
  v.metrics.forEach((r,i)=>{keys(r,['category','name','unit','direction','minimumGain',...roles]);choice(r.category,['benefit','cost','proof','risk','human']);for(const k of ['name','unit','minimumGain'])text(r[k]);choice(r.direction,['higher','lower']);roles.forEach(role=>{const o=r[role];keys(o,['value','basis','reference']);text(o.value);text(o.reference);choice(o.basis,['unknown','illustrative','supplied-report']);});});
  return parseBounded(canonical(draft));
}
export function createDraft(input,step,language) { return validateDraft({schema:DRAFT_SCHEMA,state:'partial-unvalidated',authority:'none',input,step,language}); }
export function restoreDraft(bytes) { return validateDraft(parseBounded(bytes)); }
