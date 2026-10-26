// SPDX-License-Identifier: Apache-2.0
// Inert accounting over supplied evidence. This module has no transaction or authority API.
export const SCHEMA = 'alpha-shadow-ledger/v1';
const COSTS = ['delivery', 'business', 'capability', 'maintenance'];
const MAX_AMOUNT = 1_000_000_000_000;
const MAX_EVENTS = 4096;
const ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$/;
const own = (value, key) => Object.hasOwn(value, key);
function ownedFrame(raw) {
  let nodes = 0, textLength = 0;
  const ancestors = new Set();
  const copy = (value, depth) => {
    if (++nodes > 100000 || depth > 32) throw Error('Accounting input exceeds frame bounds');
    if (value === null || typeof value === 'boolean') return value;
    if (typeof value === 'string') {
      textLength += value.length;
      if (textLength > 2_000_000) throw Error('Accounting input exceeds text bounds');
      return value;
    }
    if (typeof value === 'number') {
      if (!Number.isFinite(value)) throw Error('Accounting input requires finite numbers');
      return value;
    }
    if (typeof value !== 'object') throw Error('Accounting input requires plain JSON data');
    const array = Array.isArray(value), prototype = Object.getPrototypeOf(value);
    if (prototype !== (array ? Array.prototype : Object.prototype)) throw Error('Accounting input has unsupported prototype');
    if (ancestors.has(value)) throw Error('Accounting input contains a cycle');
    const descriptors = Object.getOwnPropertyDescriptors(value), keys = Reflect.ownKeys(descriptors);
    for (const key of keys) {
      if (typeof key !== 'string' || key === 'toJSON' || !own(descriptors[key], 'value') ||
          (!descriptors[key].enumerable && !(array && key === 'length')))
        throw Error('Accounting input rejects accessors, hidden properties and serializers');
    }
    let result;
    if (array) {
      const length = descriptors.length?.value;
      if (!Number.isSafeInteger(length) || length < 0 || length > MAX_EVENTS || keys.length !== length + 1 ||
          keys.some(key => key !== 'length' && (!/^(0|[1-9][0-9]*)$/.test(key) || Number(key) >= length)))
        throw Error('Accounting input rejects sparse or oversized arrays');
      result = [];
    } else result = {};
    ancestors.add(value);
    for (const key of keys) {
      if (array && key === 'length') continue;
      Object.defineProperty(result, key, {value: copy(descriptors[key].value, depth + 1),
        enumerable: true, writable: true, configurable: true});
    }
    ancestors.delete(value);
    return result;
  };
  return copy(raw, 0);
}
function object(value, fields, label) {
  if (!value || Array.isArray(value) || Object.getPrototypeOf(value) !== Object.prototype ||
      Object.keys(value).sort().join(',') !== [...fields].sort().join(','))
    throw Error(`${label}: missing or unknown fields`);
}
function identifier(value, label) {
  if (typeof value !== 'string' || !ID.test(value)) throw Error(`Invalid ${label}`);
}
function text(value, label) {
  if (typeof value !== 'string' || !value.trim() || value.length > 1024 || /[\u0000-\u001f]/.test(value))
    throw Error(`Invalid ${label}`);
}
function amount(value, label) {
  if (!Number.isSafeInteger(value) || value < 0 || value > MAX_AMOUNT) throw Error(`Invalid ${label}`);
}
function add(left, right) {
  const result = left + right;
  if (!Number.isSafeInteger(result)) throw Error('Ledger total exceeds supported integer bounds');
  return result;
}
const stable = value => JSON.stringify(value, (_key, item) => item && typeof item === 'object' && !Array.isArray(item) ?
  Object.fromEntries(Object.keys(item).sort().map(key => [key, item[key]])) : item);
function checkEvent(event) {
  const common = ['id', 'type', 'missionId', 'reference'];
  if (event?.type === 'mission') {
    object(event, [...common, 'acceptance'], 'Mission event');
    if (!['accepted', 'rejected', 'unknown'].includes(event.acceptance)) throw Error('Invalid acceptance');
  } else if (event?.type === 'capability') {
    object(event, [...common, 'capabilityId', 'action'], 'Capability event');
    identifier(event.capabilityId, 'capability identity');
    if (!['invoked', 'admitted', 'rejected', 'retired'].includes(event.action)) throw Error('Invalid capability action');
  } else {
    object(event, [...common, 'amountMinor', 'basis', 'category'], 'Accounting event');
    const categories = {revenue: ['collected', 'price'], cost: COSTS, reserve: ['reliability'], obligation: ['unpaid']};
    if (!own(categories, event.type) || !categories[event.type].includes(event.category)) throw Error('Invalid event category');
    if (!['observed', 'assumed', 'unknown'].includes(event.basis)) throw Error('Invalid evidence basis');
    if (event.basis === 'unknown') {
      if (event.amountMinor !== null) throw Error('Unknown amounts must be null');
    } else amount(event.amountMinor, 'minor-unit amount');
    if (event.type === 'revenue' && event.basis !== 'unknown' &&
        event.basis !== (event.category === 'collected' ? 'observed' : 'assumed'))
      throw Error('Collected revenue must be observed; price is an assumption');
  }
  identifier(event.id, 'event identity'); identifier(event.missionId, 'mission identity'); text(event.reference, 'reference');
}
function validated(raw) {
  object(raw, ['schema', 'currency', 'events'], 'Ledger');
  if (raw.schema !== SCHEMA || !['USD', 'CAD', 'EUR'].includes(raw.currency)) throw Error('Unsupported ledger schema or currency');
  if (!Array.isArray(raw.events) || raw.events.length > MAX_EVENTS) throw Error('Ledger event limit exceeded');
  const byId = new Map(), missions = new Map();
  for (const event of raw.events) {
    checkEvent(event);
    const previous = byId.get(event.id);
    if (previous && stable(previous) !== stable(event)) throw Error('Conflicting duplicate event');
    if (previous) continue;
    if (event.type === 'mission') {
      if (missions.has(event.missionId)) throw Error('Each mission requires one acceptance record');
      missions.set(event.missionId, event);
    }
    byId.set(event.id, event);
  }
  for (const event of byId.values()) if (!missions.has(event.missionId)) throw Error('Accounting requires a mission reference');
  return {schema: SCHEMA, currency: raw.currency, events: [...byId.values()].sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0)};
}
export function appendEvent(ledger, event) {
  ({ledger, event} = ownedFrame({ledger, event}));
  const current = validated(ledger);
  checkEvent(event);
  const prior = current.events.find(row => row.id === event.id);
  if (prior) {
    if (stable(prior) !== stable(event)) throw Error('Conflicting duplicate event');
    return current;
  }
  return validated({...current, events: [...current.events, event]});
}
function total(rows, observedOnly = false) {
  if (!rows.length || rows.some(row => row.basis === 'unknown' || (observedOnly && row.basis !== 'observed'))) return null;
  return rows.reduce((sum, row) => add(sum, row.amountMinor), 0);
}
function account(revenue, cost, reserve, obligation, acceptance, reinvestmentBps) {
  const operatingMargin = revenue === null || cost === null ? null : revenue - cost;
  const afterReserves = operatingMargin === null || reserve === null || obligation === null ? null :
    operatingMargin - reserve - obligation;
  const availableSurplus = afterReserves === null || acceptance === 'unknown' ? null :
    acceptance === 'accepted' ? Math.max(0, afterReserves) : 0;
  const eligibleInvestment = availableSurplus === null ? null :
    Number(BigInt(availableSurplus) * BigInt(reinvestmentBps) / 10000n);
  return {revenue, fullCost: cost, operatingMargin, reserve, unpaidObligations: obligation, afterReserves,
    availableSurplus, eligibleInvestment};
}
export function replayLedger(raw, options = {}) {
  ({raw, options} = ownedFrame({raw, options}));
  if (!options || Array.isArray(options) || Object.keys(options).some(key => key !== 'reinvestmentBps'))
    throw Error('Unknown replay option');
  const {reinvestmentBps = 0} = options;
  if (!Number.isInteger(reinvestmentBps) || reinvestmentBps < 0 || reinvestmentBps > 10000)
    throw Error('Reinvestment must be 0–10000 basis points');
  const ledger = validated(raw), missions = ledger.events.filter(row => row.type === 'mission').map(mission => {
    const events = ledger.events.filter(row => row.missionId === mission.missionId);
    const costs = events.filter(row => row.type === 'cost');
    const missingCostCategories = COSTS.filter(category => !costs.some(row => row.category === category));
    const cost = missingCostCategories.length ? null : total(costs), observedCost = missingCostCategories.length ? null : total(costs, true);
    const collected = total(events.filter(row => row.type === 'revenue' && row.category === 'collected'));
    const price = total(events.filter(row => row.type === 'revenue' && row.category === 'price'));
    const reserves = events.filter(row => row.type === 'reserve'), obligations = events.filter(row => row.type === 'obligation');
    return {missionId: mission.missionId, acceptance: mission.acceptance, reference: mission.reference,
      observed: account(collected, observedCost, total(reserves, true), total(obligations, true), mission.acceptance, reinvestmentBps),
      scenario: account(price === null ? collected : price, cost, total(reserves), total(obligations), mission.acceptance, reinvestmentBps),
      assumedPrice: price, missingCostCategories,
      unknownEventIds: events.filter(row => row.basis === 'unknown').map(row => row.id),
      capabilityEvents: events.filter(row => row.type === 'capability')};
  });
  const aggregate = basis => {
    const fields = ['revenue', 'fullCost', 'operatingMargin', 'reserve', 'unpaidObligations', 'afterReserves'];
    const result = Object.fromEntries(fields.map(field => [field, missions.length && missions.every(row => row[basis][field] !== null) ?
      missions.reduce((sum, row) => add(sum, row[basis][field]), 0) : null]));
    // Failed work keeps its costs in the enterprise account; one profitable mission cannot erase a loss.
    result.availableSurplus = result.afterReserves === null || missions.some(row => row.acceptance === 'unknown' ||
      (row.acceptance !== 'accepted' && row[basis].revenue !== 0)) ? null :
      Math.max(0, result.afterReserves);
    result.eligibleInvestment = result.availableSurplus === null ? null :
      Number(BigInt(result.availableSurplus) * BigInt(reinvestmentBps) / 10000n);
    return result;
  };
  return {schema: 'alpha-shadow-ledger-summary/v1', currency: ledger.currency, reinvestmentBps,
    eventCount: ledger.events.length, missions, observed: aggregate('observed'), scenario: aggregate('scenario'),
    scope: 'Non-transactional supplied accounting; observed labels are user assertions, not authenticated receipts. Customer savings are not revenue. No funds, authority or capability improvement are created.'};
}
const nullableAmount = (value, label) => {if (value !== null) amount(value, label); return value;};
export function planMission(input = {}) {
  input = ownedFrame(input);
  const allowed = ['missionId', 'reference', 'currency', 'acceptance', 'totalCollectedCents', 'priceAssumptionCents',
    'totalOperatingCostCents', 'operatingCostsComplete', 'capabilityCostCents', 'reserveCents', 'obligationCents',
    'costBasis', 'reinvestmentBps', 'humanMinutes', 'humanHourlyCents', 'traditionalMinutes'];
  if (!input || Array.isArray(input) || Object.getPrototypeOf(input) !== Object.prototype ||
    Object.keys(input).some(key => !allowed.includes(key))) throw Error('Unknown planning input');
  const {missionId = 'mission-1', reference = 'User-supplied planning inputs', currency = 'USD', acceptance = 'unknown',
    totalCollectedCents = null, priceAssumptionCents = null, totalOperatingCostCents = null,
    operatingCostsComplete = false, capabilityCostCents = null, reserveCents = null, obligationCents = null,
    costBasis = 'assumed', reinvestmentBps = 0, humanMinutes = null, humanHourlyCents = null,
    traditionalMinutes = null} = input;
  if (typeof operatingCostsComplete !== 'boolean' || !['observed', 'assumed'].includes(costBasis)) throw Error('Invalid cost completeness or basis');
  identifier(missionId, 'mission identity');
  if (missionId.length > 50) throw Error('Planning mission identity exceeds 50 characters');
  for (const [name, value] of Object.entries({humanMinutes, humanHourlyCents, traditionalMinutes})) nullableAmount(value, name);
  const event = (type, category, value, basis) => ({id: `${missionId}:${type}:${category}`, type, missionId,
    category, amountMinor: nullableAmount(value, category), basis: value === null ? 'unknown' : basis, reference});
  const ledger = validated({schema: SCHEMA, currency, events: [
    {id: `${missionId}:mission`, type: 'mission', missionId, acceptance, reference},
    event('revenue', 'collected', totalCollectedCents, 'observed'), event('revenue', 'price', priceAssumptionCents, 'assumed'),
    event('cost', 'delivery', totalOperatingCostCents, costBasis),
    {...event('cost', 'business', operatingCostsComplete ? 0 : null, costBasis),
      reference: operatingCostsComplete ? `${reference}; included in the attested total operating cost` : reference},
    {...event('cost', 'maintenance', operatingCostsComplete ? 0 : null, costBasis),
      reference: operatingCostsComplete ? `${reference}; included in the attested total operating cost` : reference},
    event('cost', 'capability', capabilityCostCents, costBasis),
    event('reserve', 'reliability', reserveCents, costBasis), event('obligation', 'unpaid', obligationCents, costBasis)]});
  const summary = replayLedger(ledger, {reinvestmentBps});
  const minutesCost = minutes => {
    if (minutes === null || humanHourlyCents === null) return null;
    const value = (BigInt(minutes) * BigInt(humanHourlyCents) + 59n) / 60n;
    if (value > BigInt(Number.MAX_SAFE_INTEGER)) throw Error('Human cost exceeds supported integer bounds');
    return Number(value);
  };
  const attention = minutesCost(humanMinutes), traditional = minutesCost(traditionalMinutes);
  const price = priceAssumptionCents === null ? totalCollectedCents : priceAssumptionCents;
  const buyerCost = price === null || attention === null ? null : add(price, attention);
  return {ledger, summary, comparison: {traditionalCost: traditional, humanAttentionCost: attention,
    customerPricePlusAttention: buyerCost, providerFullCost: summary.scenario.fullCost,
    customerSavings: traditional === null || buyerCost === null ? null : traditional - buyerCost,
    breakEvenTraditionalMinutes: buyerCost === null || !humanHourlyCents ? null : buyerCost * 60 / humanHourlyCents,
    scope: 'Conditional equal-acceptance scenario using supplied wage and duration assumptions; remaining customer attention is distinct from provider costs.'}};
}

export function calculateInvestment(input = {}) {
  input = ownedFrame(input);
  const fields = ['constructionCostMinor', 'failedConstructionCostMinor', 'maintenancePerReuseMinor',
    'expectedSavingPerReuseMinor', 'remainingReuses'];
  if (!input || Array.isArray(input) || Object.getPrototypeOf(input) !== Object.prototype ||
      Object.keys(input).some(key => !fields.includes(key))) throw Error('Unknown investment input');
  const values = Object.fromEntries(fields.map(key => [key, input[key] ?? null]));
  for (const [key, value] of Object.entries(values)) {
    if (value === null) continue;
    if (key === 'expectedSavingPerReuseMinor') {
      if (!Number.isSafeInteger(value) || Math.abs(value) > MAX_AMOUNT) throw Error('Invalid expected saving');
    } else if (key === 'remainingReuses') {
      if (!Number.isSafeInteger(value) || value < 0 || value > 1_000_000) throw Error('Invalid finite reuse horizon');
    } else amount(value, key);
  }
  const safe = value => {
    if (value > BigInt(Number.MAX_SAFE_INTEGER) || value < BigInt(Number.MIN_SAFE_INTEGER))
      throw Error('Investment total exceeds supported integer bounds');
    return Number(value);
  };
  const {constructionCostMinor: construction, failedConstructionCostMinor: failed,
    maintenancePerReuseMinor: maintenance, expectedSavingPerReuseMinor: saving, remainingReuses: reuse} = values;
  const fixedCost = construction === null || failed === null ? null : add(construction, failed);
  const maintenanceCost = maintenance === null || reuse === null ? null : safe(BigInt(maintenance) * BigInt(reuse));
  const grossSaving = saving === null || reuse === null ? null : safe(BigInt(saving) * BigInt(reuse));
  const lifetimeCost = fixedCost === null || maintenanceCost === null ? null : add(fixedCost, maintenanceCost);
  const netBenefit = lifetimeCost === null || grossSaving === null ? null : safe(BigInt(grossSaving) - BigInt(lifetimeCost));
  const marginalSaving = saving === null || maintenance === null ? null : saving - maintenance;
  const breakEvenReuses = fixedCost === null || marginalSaving === null ? null : fixedCost === 0 ? 0 :
    marginalSaving <= 0 ? null : safe((BigInt(fixedCost) + BigInt(marginalSaving) - 1n) / BigInt(marginalSaving));
  return {...values, fixedCost, maintenanceCost, grossSaving, lifetimeCost, netBenefit, breakEvenReuses,
    paysBackWithinHorizon: netBenefit === null ? null : netBenefit >= 0,
    scope: 'Conditional finite-reuse scenario. Supplied savings are assumptions, not demonstrated improvement; failed construction and maintenance remain costs. No investment is executed.'};
}
