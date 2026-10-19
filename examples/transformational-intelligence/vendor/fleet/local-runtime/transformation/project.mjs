// SPDX-License-Identifier: MIT
// Inert continuity, never execution, payment, reviewer or promotion authority.
import {canonical, parseStrict, need, keys, uuid} from '../primitives.mjs';
import {sha256} from '../../fleet/successor/vendor/manager/site/assets/successor/safe.mjs';

export const TI_PROJECT_SCHEMA = 'agi-fleet/ti-project/v1';
export const TI_PROJECT_BYTES = 12_000_000;
const KINDS = ['native-request','native-result','native-update','manager-inspection','jobs-inspection',
  'computer-handoff','computer-return','reuse-archive','reuse-update'];
const same = (a,b) => canonical(a) === canonical(b);
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const size = raw => new TextEncoder().encode(raw).length;
const inert = value => need(value.authority === 'none' && value.qualification === 'not-evaluated'
  && value.settlement === 'not-connected', 'TI_PROJECT_AUTHORITY');
async function seal(body) {
  const raw = canonical({...body,sha256:await sha256(body)});
  need(size(raw) <= TI_PROJECT_BYTES, 'TI_PROJECT_CAPACITY'); return raw;
}
function read(raw) {
  need(typeof raw === 'string' && size(raw) <= TI_PROJECT_BYTES, 'TI_PROJECT_CAPACITY');
  return parseStrict(raw,TI_PROJECT_BYTES);
}
function requestIdentity(value) {
  need(value.schema_version === 1 && typeof value.campaign_id === 'string', 'TI_REQUEST_SCHEMA');
  uuid(value.campaign_id);
  need(value.charter?.schema === 'intent-charter/v1' && value.charter.publicOnly === true
    && value.charter.budgets?.money_minor === 0 && value.charter.budgets.USDCBaseUnits === '0'
    && value.charter.budgets.AGIALPHABaseUnits === '0', 'TI_REQUEST_FREE_PUBLIC_SCOPE');
  return value.campaign_id;
}
async function receiver(receivers, name, raw) {
  need(typeof receivers[name] === 'function', 'TI_' + name.toUpperCase() + '_RECEIVER_REQUIRED');
  return receivers[name](raw);
}

/** Installed receivers are supplied by the application, never by imported JSON. */
export async function inspectTIProject(raw, receivers = {}) {
  const value = read(raw);
  keys(value,['schema','projectId','revision','history','authority','qualification','settlement','sha256']);
  const {sha256:checksum,...body} = value;
  need(value.schema === TI_PROJECT_SCHEMA && checksum === await sha256(body), 'TI_PROJECT_INTEGRITY');
  inert(value); uuid(value.projectId);
  need(typeof receivers.public === 'function','TI_PUBLIC_RECEIVER_REQUIRED');
  need(Array.isArray(value.history) && value.history.length >= 1 && value.history.length <= 24
    && value.revision === value.history.length - 1, 'TI_PROJECT_HISTORY');
  const seen = new Set(), summaries = [];
  let request = null, native = null, nativeRaw = null, handoffRaw = null, archive = null;
  for (const [index,event] of value.history.entries()) {
    keys(event,['kind','raw','sha256']);
    need(KINDS.includes(event.kind) && hash(event.sha256) && event.sha256 === await sha256(event.raw), 'TI_PROJECT_EVENT');
    const key = event.kind + ':' + event.sha256;
    need(!seen.has(key), 'TI_PROJECT_DUPLICATE'); seen.add(key);
    const item = read(event.raw);
    receivers.public(item);
    if (event.kind === 'native-request') {
      need(index === 0 && request === null && requestIdentity(item) === value.projectId, 'TI_PROJECT_REQUEST');
      request = item;
      summaries.push({kind:event.kind,state:'inert-request',authority:'none'});
      continue;
    }
    need(request !== null, 'TI_PROJECT_REQUEST_REQUIRED');
    if (['native-result','native-update'].includes(event.kind)) {
      need(event.kind === 'native-result' ? native === null : native !== null,'TI_PROJECT_RESULT_ORDER');
      const next = await receiver(receivers,'native',event.raw);
      need(same(next,item) && next.campaign_id === value.projectId
        && same(next.bindings?.request,request), 'TI_PROJECT_NATIVE_BINDING');
      if(native!==null) {
        need(!['completed','canceled'].includes(native.phase) && next.revision>native.revision
          && next.bindings_digest===native.bindings_digest
          && (native.freeze===null||same(next.freeze,native.freeze))
          && (native.freeze===null||same(next.formulation,native.formulation)&&same(next.transformation,native.transformation))
          && (native.result===null||same(next.result,native.result))
          && summaries.every(row=>['native-request','native-result','native-update'].includes(row.kind)),
        'TI_PROJECT_NATIVE_HISTORY_REWRITTEN');
      }
      native=next;
      nativeRaw = event.raw;
      summaries.push({kind:event.kind,state:native.phase,independentReview:false});
      continue;
    }
    need(native !== null && native.phase === 'completed', 'TI_PROJECT_COMPLETED_NATIVE_REQUIRED');
    if (event.kind.endsWith('-inspection')) {
      const name = event.kind === 'manager-inspection' ? 'manager' : 'jobs';
      need(!summaries.some(row=>row.kind===event.kind), 'TI_PROJECT_ROUTE_ONCE');
      const verified = typeof receivers[name] === 'function';
      if(verified) need(same(item,await receivers[name](nativeRaw)), 'TI_PROJECT_ROUTE_BINDING');
      keys(item,['schema','asset','decimals','nativeSha256','bindingsDigest','inspection','paidProposal','authority','settlement','adapterSha256']);
      need(item.schema === 'agi-fleet/ti-route-inspection/v1' && item.nativeSha256 === await sha256(nativeRaw)
        && item.bindingsDigest === native.bindings_digest && item.inspection === 'exact-native-object'
        && item.paidProposal === 'refused-native-zero-allowance' && item.authority === 'none'
        && item.settlement === 'not-connected' && hash(item.adapterSha256)
        && (name==='manager' ? item.asset==='USDC'&&item.decimals===6 : item.asset==='AGIALPHA'&&item.decimals===18),
      'TI_PROJECT_ROUTE_SCOPE');
      summaries.push({kind:event.kind,asset:item.asset,decimals:item.decimals,paidProposal:item.paidProposal,
        inspection:verified?'recomputed-by-installed-adapter':'historical-unverified'});
    } else if (event.kind === 'computer-handoff') {
      need(handoffRaw === null, 'TI_PROJECT_COMPUTER_ONCE');
      await receiver(receivers,'handoff',event.raw);
      need(item.task?.html === await summaryHTML(nativeRaw,receivers.native)
        && item.sourceHash === await sha256(nativeRaw)
        && read(item.projectRaw).id === value.projectId, 'TI_PROJECT_BROWSER_ARTIFACT');
      handoffRaw = event.raw;
      summaries.push({kind:event.kind,state:'requires-separate-native-permission'});
    } else if (event.kind === 'computer-return') {
      need(handoffRaw !== null && !summaries.some(row=>row.kind===event.kind), 'TI_PROJECT_HANDOFF_REQUIRED');
      const result = await receiver(receivers,'computer',canonical({handoffRaw,returnRaw:event.raw}));
      need(result.returned && same(result.returned,item), 'TI_PROJECT_COMPUTER_BINDING');
      summaries.push({kind:event.kind,state:result.returned.receipt?.state,independentReview:false});
    } else {
      need(event.kind === 'reuse-archive' ? archive === null : archive !== null, 'TI_PROJECT_ARCHIVE_ORDER');
      if(typeof receivers.library==='function') need(same(await receivers.library(event.raw),item),'TI_PROJECT_LIBRARY_RECEIVER');
      const expected = await sha256('successor-omega/v1:ti-library-archive\0'+canonical({envelope:item.envelope,
        conditions:item.conditions,behavior_digest:item.behavior_digest}));
      need(item.archive_digest===expected && same(item.envelope,native)
        && item.authority_granted === false && hash(item.archive_digest)
        && (archive === null || item.archive_digest === archive.archive_digest), 'TI_PROJECT_REUSE_BINDING');
      if (event.kind === 'reuse-archive') need(item.state === 'pending-review' && item.review === null
        && item.activation === null, 'TI_PROJECT_REUSE_REVIEW_REQUIRED');
      archive = item;
      summaries.push({kind:event.kind,state:item.state,authorityGranted:false,review:'historical-unverified'});
    }
  }
  return {project:value,request,native,nativeRaw,handoffRaw,archive,summaries,
    authority:'none',runAuthorized:false,independentReview:false,settlement:'not-connected'};
}
export async function createTIProject(requestRaw,receivers={}) {
  const request = read(requestRaw), projectId = requestIdentity(request);
  need(typeof receivers.public==='function','TI_PUBLIC_RECEIVER_REQUIRED'); receivers.public(request);
  return seal({schema:TI_PROJECT_SCHEMA,projectId,revision:0,
    history:[{kind:'native-request',raw:requestRaw,sha256:await sha256(requestRaw)}],
    authority:'none',qualification:'not-evaluated',settlement:'not-connected'});
}
export async function appendTIProject(raw,kind,eventRaw,receivers) {
  const {project} = await inspectTIProject(raw,receivers);
  need(KINDS.includes(kind) && kind !== 'native-request', 'TI_PROJECT_EVENT_KIND');
  // Exact retries are idempotent; changed bytes are validated as a new event.
  if (project.history.some(event=>event.kind===kind&&event.raw===eventRaw)) return raw;
  need(project.history.length < 24, 'TI_PROJECT_HISTORY_CAPACITY');
  project.history.push({kind,raw:eventRaw,sha256:await sha256(eventRaw)}); project.revision++;
  delete project.sha256;
  const result = await seal(project); await inspectTIProject(result,receivers); return result;
}
const escape = value => String(value).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
/** Construct a useful visible artifact; source clauses remain inert escaped text. */
export async function summaryHTML(nativeRaw, inspectNative) {
  need(typeof inspectNative === 'function', 'TI_NATIVE_RECEIVER_REQUIRED');
  const native = await inspectNative(nativeRaw);
  need(native.phase === 'completed' && native.result?.results, 'TI_SUMMARY_COMPLETED_REQUIRED');
  const selected=native.result.decision==='propose-reuse-pending-independent-review'?'candidate':'lead-order';
  const results=native.result.results[selected];
  need(Array.isArray(results)&&results.length>0,'TI_SUMMARY_EVIDENCE_REQUIRED');
  const rows=results.map(row=>`<article><pre>${escape(row.text)}</pre><ul>`
    +row.references.map(reference=>`<li>${escape(reference.id)}: ${escape(reference.provenance)}</li>`).join('')+'</ul></article>').join('');
  return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    + '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;">'
    + '<title>Source-grounded summary · Résumé sourcé</title><style>body{font:18px system-ui;max-width:900px;margin:24px auto;padding:16px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
    + '<h1>Source-grounded summary / Résumé sourcé</h1><p>Exact public source clauses; structural evidence only. Independent usefulness review pending. No authority or payment.</p>'
    + `<p>Campaign / Campagne: ${escape(native.campaign_id)}</p><h2>Fixed summary / Résumé fixe</h2>${rows}`
    + `<h2>Comparison / Comparaison</h2><pre>${escape(canonical(native.result.means_millionths))}</pre>`
    + `<h2>Outcome and limits / Résultat et limites</h2><pre>${escape(canonical({decision:native.result.decision,
      reader_understanding:native.result.reader_understanding,costs:native.result.costs}))}</pre></html>`;
}

/** Reuse the existing native Computer Use handoff; its separate grant is unchanged. */
export async function createSummaryHandoff(nativeRaw,{inspectNative,createProject,createComputerHandoff}={}) {
  need([inspectNative,createProject,createComputerHandoff].every(value=>typeof value==='function'),'TI_COMPUTER_RECEIVERS_REQUIRED');
  const native=await inspectNative(nativeRaw), project=createProject({name:'TI source summary',goal:native.charter.purpose});
  project.id=native.campaign_id;
  return createComputerHandoff(project,{sourceHash:await sha256(nativeRaw),goal:native.charter.purpose,selected:'reframe',
    valueHypothesis:'Inspect the exact source-grounded summary; independent practical usefulness remains pending.',
    hypotheses:['Retain the original lead-order summary.','Represent prerequisites before fixed-length compression.'],
    combination:'Preserve exact source clauses and the original fixed-summary limit.',
    reframing:'Inspect the supported prerequisite closure before selecting exact source clauses.',
    successCriteria:['Display the retained exact-source summary and references.','Preserve the campaign identity and structural limitations.'],
    html:await summaryHTML(nativeRaw,inspectNative),allowedUrls:[],inputRights:'public',
    license:'Public paper excerpts with retained provenance; local annotations are not independent truth.',
    maxTurns:3,maxActions:2,maxSeconds:60,reviewMinutes:5});
}
