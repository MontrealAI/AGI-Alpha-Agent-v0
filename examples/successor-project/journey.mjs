// SPDX-License-Identifier: Apache-2.0
/** One inert history across explicitly selected native protocol receivers. */
import {canonical, parseJourney} from './journey-codec.mjs';
import {validateProject, exactDigest} from './engine.mjs';
export const JOURNEY_SCHEMA = 'alpha-guided-project/v1';
export const JOURNEY_LIMIT = 16_000_000;
const KINDS = ['alpha-project', 'alpha-cycle', 'manager-transfer', 'jobs-transfer', 'fleet-return'];
function fail(ok, code) { if (!ok) throw Error('JOURNEY_' + code); }
function fields(v, names) { fail(v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).sort().join('|') === [...names].sort().join('|'), 'FIELDS'); }
function same(a, b) { return canonical(a) === canonical(b); }
function transferExtension(before, after) {
  const {history:oldHistory,sha256:oldHash,...oldBody}=before;
  const {history:newHistory,sha256:newHash,...newBody}=after;
  fail(same(oldBody,newBody), 'TRANSFER_REPLANNED');
  fail(newHistory.length>oldHistory.length && same(newHistory.slice(0,oldHistory.length),oldHistory), 'TRANSFER_HISTORY_REWRITTEN');
}
async function seal(body) { return canonical({...body, sha256: await exactDigest(canonical(body))}); }
function extending(previous, next) {
  fail(next.projectId === previous.projectId && next.revision > previous.revision, 'PROJECT_LINEAGE');
  fail(next.history.length > previous.history.length && same(next.history.slice(0, previous.history.length), previous.history), 'HISTORY_REWRITTEN');
  fail(next.cycles.length >= previous.cycles.length, 'CYCLE_REMOVED');
  for (let i = 0; i < previous.cycles.length; i++) {
    const old = previous.cycles[i], current = next.cycles[i];
    if (i < previous.cycles.length - 1 || next.cycles.length > previous.cycles.length) fail(same(old, current), 'CYCLE_REWRITTEN');
    else {
      fail(current.cycleId === old.cycleId && same(current.discovery, old.discovery) && same(current.mapping, old.mapping), 'CYCLE_REWRITTEN');
      fail(current.records.length > old.records.length && same(current.records.slice(0, old.records.length), old.records), 'RECORD_REWRITTEN');
    }
  }
}
/** Receivers come from the bundled application, never from imported content. */
export async function inspectJourney(raw, receivers = {}) {
  const value = parseJourney(raw);
  fields(value, ['schema','projectId','revision','native','history','authority','qualification','settlement','sha256']);
  const {sha256, ...body} = value;
  fail(sha256 === await exactDigest(canonical(body)), 'INTEGRITY');
  fail(value.schema === JOURNEY_SCHEMA && value.authority === 'none' && value.qualification === 'not-evaluated' && value.settlement === 'not-connected', 'AUTHORITY');
  fail(Array.isArray(value.history) && value.history.length > 0 && value.history.length <= 16 && value.revision === value.history.length - 1, 'HISTORY_LIMIT');
  let native = null, nativeRaw = null, latestTransfer = null, fleet = null;
  let routeHistory = {}, routeRaw = {};
  const summaries = [], seenEvents = new Set();
  for (const [index, event] of value.history.entries()) {
    fields(event, ['kind','raw','sha256']);
    fail(KINDS.includes(event.kind) && (index === 0 ? event.kind === 'alpha-project' : event.kind !== 'alpha-project'), 'EVENT_KIND');
    fail(event.sha256 === await exactDigest(event.raw), 'NATIVE_BYTES');
    const eventKey=event.kind+':'+event.sha256;fail(!seenEvents.has(eventKey),'DUPLICATE_EVENT');seenEvents.add(eventKey);
    if (['alpha-project','alpha-cycle'].includes(event.kind)) {
      const next = await validateProject(event.raw);
      fail(next.projectId === value.projectId, 'CROSS_PROJECT');
      if (native) extending(native, next);
      native = next; nativeRaw = event.raw; latestTransfer = null; fleet = null; routeHistory = {}; routeRaw = {};
      summaries.push({kind:event.kind, projectId:native.projectId, cycleId:native.cycles.at(-1).cycleId, revision:native.revision});
    } else if (event.kind === 'manager-transfer') {
      fail(typeof receivers.manager === 'function', 'MANAGER_RECEIVER_REQUIRED');
      const read = await receivers.manager(event.raw);
      fail(read.transfer.original.raw === nativeRaw && same(read.originalProject, native), 'MANAGER_PROJECT');
      if (routeHistory[event.kind]) {
        transferExtension(routeHistory[event.kind],read.transfer);
      }
      routeHistory[event.kind] = read.transfer; routeRaw[event.kind] = event.raw;
      latestTransfer = {kind:event.kind, raw:event.raw, value:read.transfer}; fleet = null;
      summaries.push({kind:event.kind, asset:'USDC', planningAmount:read.state.plans.at(-1)?.draft.fields.budget??null, checkpoints:read.transfer.history.length, settlement:'not-connected'});
    } else if (event.kind === 'jobs-transfer') {
      fail(typeof receivers.jobs === 'function', 'JOBS_RECEIVER_REQUIRED');
      const read = await receivers.jobs(event.raw);
      fail([nativeRaw, routeRaw['manager-transfer']].includes(read.transfer.original.raw) && same(read.project, native), 'JOBS_PROJECT');
      if (routeHistory[event.kind]) {
        transferExtension(routeHistory[event.kind],read.transfer);
      }
      routeHistory[event.kind] = read.transfer; routeRaw[event.kind] = event.raw;
      latestTransfer = {kind:event.kind, raw:event.raw, value:read.transfer}; fleet = null;
      summaries.push({kind:event.kind, asset:'AGIALPHA', planningAmount:agialphaTokens(read.transfer.planning.amountBaseUnits), checkpoints:read.transfer.history.length, settlement:'not-connected'});
    } else {
      fail(typeof receivers.fleet === 'function', 'FLEET_RECEIVER_REQUIRED');
      const read = await receivers.fleet(event.raw);
      const request = read.request;
      fail(request.project.projectDigest === native.projectDigest && request.project.projectId === native.projectId, 'FLEET_PROJECT');
      fail(request.upstream.raw === (latestTransfer?.raw ?? nativeRaw), 'FLEET_UPSTREAM');
      fleet = read;
      summaries.push({kind:event.kind, asset:request.route.asset, productionQualified:false, settlement:'not-connected'});
    }
  }
  fields(value.native, ['raw','sha256']);
  fail(value.native.raw === nativeRaw && value.native.sha256 === await exactDigest(nativeRaw), 'CURRENT_NATIVE');
  return {journey:value, project:native, nativeRaw, latestTransfer, routeTransfers:routeRaw, fleet, summaries};
}
export async function createJourney(nativeRaw) {
  const project = await validateProject(nativeRaw), hash = await exactDigest(nativeRaw);
  return seal({schema:JOURNEY_SCHEMA, projectId:project.projectId, revision:0, native:{raw:nativeRaw,sha256:hash}, history:[{kind:'alpha-project',raw:nativeRaw,sha256:hash}], authority:'none',qualification:'not-evaluated',settlement:'not-connected'});
}
export async function appendJourney(raw, kind, nativeRaw, receivers = {}) {
  const {journey, nativeRaw: previous} = await inspectJourney(raw, receivers);
  fail(journey.history.length < 16, 'HISTORY_LIMIT');
  fail(kind !== 'alpha-project' && KINDS.includes(kind), 'EVENT_KIND');
  fail(!journey.history.some(e => e.kind === kind && e.raw === nativeRaw), 'DUPLICATE_EVENT');
  const hash = await exactDigest(nativeRaw);
  journey.history.push({kind,raw:nativeRaw,sha256:hash}); journey.revision++;
  if (kind === 'alpha-cycle') journey.native = {raw:nativeRaw,sha256:hash};
  else fail(previous === journey.native.raw, 'CURRENT_NATIVE');
  delete journey.sha256;
  const result = await seal(journey); await inspectJourney(result, receivers); return result;
}

export function agialphaBaseUnits(text) {
  fail(typeof text==='string' && /^(?:0|[1-9][0-9]{0,6})(?:\.[0-9]{1,18})?$/.test(text), 'AGIALPHA_DECIMAL_AMOUNT');
  const [whole,fraction='']=text.split('.');
  const amount=BigInt(whole)*10n**18n+BigInt(fraction.padEnd(18,'0'));
  fail(amount>=7n&&amount<=1_000_000n*10n**18n, 'AGIALPHA_AMOUNT_BOUNDS');
  return amount.toString();
}

export function returnKind(raw) {
  const schema=parseJourney(raw).schema;
  const kind={'agijobmanager/alpha-project-transfer/v1':'manager-transfer','agijobsv0/alpha-project-transfer/v1':'jobs-transfer','agi-fleet/project-return/v1':'fleet-return'}[schema];
  fail(kind,'UNSUPPORTED_RETURN');return kind;
}

export function agialphaTokens(baseUnits) {
  fail(typeof baseUnits==='string'&&/^[1-9][0-9]{0,24}$/.test(baseUnits), 'AGIALPHA_BASE_UNITS');
  const amount=BigInt(baseUnits),scale=10n**18n,fraction=(amount%scale).toString().padStart(18,'0').replace(/0+$/,'');
  return (amount/scale).toString()+(fraction?'.'+fraction:'');
}
