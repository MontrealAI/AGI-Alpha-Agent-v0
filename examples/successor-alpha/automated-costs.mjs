// SPDX-License-Identifier: Apache-2.0
export const AUTOMATED_COST_SCHEMA = 'alpha-automated-costs/v1';
export const AUTOMATED_STAGES = Object.freeze([
  'preparation', 'planning', 'execution', 'verification', 'correction', 'packaging', 'reporting', 'recovery'
]);
const MAX = 1_000_000_000_000;
const STAGES = new Set(AUTOMATED_STAGES);
const ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$/;
const BASIS = ['measured', 'sourced', 'estimated', 'unknown'];

function frame(raw) {
  let nodes = 0, characters = 0;
  const seen = new Set();
  function copy(value, depth) {
    if (++nodes > 20000 || depth > 24) throw Error('Automated cost record exceeds bounds');
    if (value === null || typeof value === 'boolean') return value;
    if (typeof value === 'number') {
      if (!Number.isSafeInteger(value) || Object.is(value, -0)) throw Error('Automated costs require safe whole quantities');
      return value;
    }
    if (typeof value === 'string') {
      characters += value.length;
      if (characters > 200000) throw Error('Automated cost text exceeds bounds');
      return value;
    }
    if (!value || typeof value !== 'object') throw Error('Automated costs require plain JSON data');
    const array = Array.isArray(value);
    if (Object.getPrototypeOf(value) !== (array ? Array.prototype : Object.prototype) || seen.has(value))
      throw Error('Automated costs reject custom prototypes and cycles');
    const descriptors = Object.getOwnPropertyDescriptors(value), keys = Reflect.ownKeys(descriptors);
    for (const key of keys) {
      const property = descriptors[key];
      if (typeof key !== 'string' || key === 'toJSON' || !Object.hasOwn(property, 'value') ||
          (!property.enumerable && !(array && key === 'length')))
        throw Error('Automated costs reject accessors, hidden properties and serializers');
    }
    if (array && (descriptors.length.value > 256 || keys.length !== descriptors.length.value + 1 ||
        keys.some(key => key !== 'length' && (!/^(0|[1-9][0-9]*)$/.test(key) || Number(key) >= descriptors.length.value))))
      throw Error('Automated costs reject sparse or oversized arrays');
    const result = array ? [] : {};
    seen.add(value);
    for (const key of keys) {
      if (array && key === 'length') continue;
      Object.defineProperty(result, key, {value:copy(descriptors[key].value, depth+1), enumerable:true,
        writable:true, configurable:true});
    }
    seen.delete(value);
    return result;
  }
  return copy(raw, 0);
}
function exact(value, keys, label) {
  if (!value || Array.isArray(value) || Object.getPrototypeOf(value) !== Object.prototype ||
      Object.keys(value).sort().join('|') !== [...keys].sort().join('|')) throw Error(`Invalid ${label} fields`);
}
function identifier(value, label) {
  if (typeof value !== 'string' || !ID.test(value)) throw Error(`Invalid ${label}`);
}
function fact(value, path, maximum = MAX, minimum = 0) {
  exact(value, ['value', 'basis', 'reference'], path);
  if (!BASIS.includes(value.basis) || typeof value.reference !== 'string' || !value.reference.trim() ||
      value.reference.length > 2000 || /[\u0000-\u001f]/.test(value.reference)) throw Error(`Invalid provenance: ${path}`);
  if (value.basis === 'unknown') {
    if (value.value !== null) throw Error(`Unknown ${path} must be null`);
  } else if (!Number.isSafeInteger(value.value) || value.value < minimum || value.value > maximum)
    throw Error(`Invalid quantity: ${path}`);
}
function array(value, label) {
  if (!Array.isArray(value) || value.length > 128) throw Error(`Invalid ${label} inventory`);
}
function inspectScenario(scenario) {
  exact(scenario, ['name', 'capacityRequestsPerMonth', 'utilizationBps', 'acceptanceBps', 'attemptsPerRequestPpm',
    'operations', 'residual', 'monthly', 'investments', 'humanBaseline'], 'scenario');
  if (!['base', 'conservative', 'stress'].includes(scenario.name)) throw Error('Unsupported scenario name');
  fact(scenario.capacityRequestsPerMonth, 'capacityRequestsPerMonth', 1_000_000);
  fact(scenario.utilizationBps, 'utilizationBps', 10000);
  fact(scenario.acceptanceBps, 'acceptanceBps', 10000);
  fact(scenario.attemptsPerRequestPpm, 'attemptsPerRequestPpm', 100_000_000, 1_000_000);
  const identities = new Set(), stages = new Set();
  const identity = row => {
    identifier(row.id, 'cost identity');
    if (identities.has(row.id)) throw Error('Duplicate cost identity would double count a shared input');
    identities.add(row.id);
  };
  for (const key of ['operations', 'residual', 'monthly', 'investments']) array(scenario[key], key);
  for (const row of scenario.operations) {
    exact(row, ['id', 'stage', 'frequency', 'unitsPerOccurrencePpm', 'unitCostMicros', 'implementation'], 'operation');
    identity(row);
    if (!STAGES.has(row.stage) || !['request', 'attempt', 'accepted'].includes(row.frequency) ||
        !['implemented', 'modeled'].includes(row.implementation)) throw Error('Invalid automated operation scope');
    stages.add(row.stage);
    fact(row.unitsPerOccurrencePpm, row.id+'.unitsPerOccurrencePpm', 100_000_000);
    fact(row.unitCostMicros, row.id+'.unitCostMicros');
  }
  if (AUTOMATED_STAGES.some(stage => !stages.has(stage))) throw Error('Every workflow stage needs a cost or explicit zero record');
  for (const row of scenario.residual) {
    exact(row, ['id', 'stage', 'exceptionsPerRequestPpm', 'minutesPerException', 'hourlyCostMicros'], 'human exception');
    identity(row);
    if (!STAGES.has(row.stage)) throw Error('Invalid residual-work stage');
    fact(row.exceptionsPerRequestPpm, row.id+'.exceptionsPerRequestPpm', 1_000_000);
    fact(row.minutesPerException, row.id+'.minutesPerException', 100000);
    fact(row.hourlyCostMicros, row.id+'.hourlyCostMicros');
  }
  for (const row of scenario.monthly) {
    exact(row, ['id', 'kind', 'amountMicros', 'allocationBps'], 'shared monthly cost');
    identity(row);
    if (!['capacity', 'maintenance', 'business'].includes(row.kind)) throw Error('Invalid monthly cost kind');
    fact(row.amountMicros, row.id+'.amountMicros');
    fact(row.allocationBps, row.id+'.allocationBps', 10000);
  }
  for (const row of scenario.investments) {
    exact(row, ['id', 'kind', 'amountMicros', 'allocationBps', 'amortizationMonths'], 'one-time investment');
    identity(row);
    if (!['setup', 'development'].includes(row.kind)) throw Error('Invalid investment kind');
    fact(row.amountMicros, row.id+'.amountMicros');
    fact(row.allocationBps, row.id+'.allocationBps', 10000);
    fact(row.amortizationMonths, row.id+'.amortizationMonths', 1200, 1);
  }
  exact(scenario.humanBaseline, ['minutesPerAccepted', 'hourlyCostMicros'], 'traditional human baseline');
  fact(scenario.humanBaseline.minutesPerAccepted, 'humanBaseline.minutesPerAccepted', 100000);
  fact(scenario.humanBaseline.hourlyCostMicros, 'humanBaseline.hourlyCostMicros');
}
export function inspectAutomatedCosts(raw) {
  const record = frame(raw);
  exact(record, ['schema', 'offeringId', 'currency', 'scenarios'], 'automated cost record');
  if (record.schema !== AUTOMATED_COST_SCHEMA || !['USD', 'CAD', 'EUR'].includes(record.currency))
    throw Error('Unsupported automated cost schema or currency');
  identifier(record.offeringId, 'offering identity');
  if (!Array.isArray(record.scenarios) || record.scenarios.length !== 3 ||
      new Set(record.scenarios.map(row => row.name)).size !== 3) throw Error('Supply distinct base, conservative and stress scenarios');
  record.scenarios.forEach(inspectScenario);
  return record;
}
function ratio(numerator, denominator = 1n) {
  const n=BigInt(numerator),d=BigInt(denominator);
  let left=n, right=d;
  while(right){const remainder=left%right;left=right;right=remainder;}
  return {n:n/left,d:d/left};
}
const multiply = (left, right) => left === null || right === null ? null : ratio(left.n*right.n, left.d*right.d);
const divide = (left, right) => left === null || right === null || right.n === 0n ? null : ratio(left.n*right.d, left.d*right.n);
const plus = (left, right) => left === null || right === null ? null : ratio(left.n*right.d+right.n*left.d, left.d*right.d);
const sum = values => values.reduce(plus, ratio(0));
const value = input => input.value === null ? null : ratio(input.value);
const scaled = (input, denominator) => input.value === null ? null : ratio(input.value, denominator);
function rounded(input) {
  if (input === null) return null;
  const result = (input.n+input.d-1n)/input.d;
  if (result > BigInt(Number.MAX_SAFE_INTEGER)) throw Error('Automated cost result exceeds safe output bounds');
  return Number(result);
}
function approximate(input) {
  if (input === null) return null;
  const quotient=input.n/input.d,remainder=input.n%input.d;
  if (remainder===0n) return Number(quotient);
  const numerator=remainder.toString(),denominator=input.d.toString();
  const numeratorDigits=Math.min(numerator.length,15),denominatorDigits=Math.min(denominator.length,15);
  const fraction=Number(numerator.slice(0,numeratorDigits))/Number(denominator.slice(0,denominatorDigits)) *
    10**(numerator.length-numeratorDigits-denominator.length+denominatorDigits);
  return Number(quotient)+fraction;
}
const unknowns = (scenario, path = '') => {
  if (scenario && typeof scenario === 'object' && !Array.isArray(scenario) &&
      Object.keys(scenario).sort().join(',') === 'basis,reference,value') return scenario.value === null ? [path] : [];
  return scenario && typeof scenario === 'object' ? Object.entries(scenario)
    .flatMap(([key,item])=>unknowns(item,path ? path+'.'+key : key)) : [];
};
function evaluateScenario(scenario, currency) {
  const requests = multiply(value(scenario.capacityRequestsPerMonth), scaled(scenario.utilizationBps, 10000));
  const acceptance = scaled(scenario.acceptanceBps, 10000), attempts = scaled(scenario.attemptsPerRequestPpm, 1000000);
  const accepted = multiply(requests, acceptance);
  const operationRows = scenario.operations.map(row => {
    const occurrence = row.frequency === 'attempt' ? attempts : row.frequency === 'accepted' ? acceptance : ratio(1);
    const perRequest = multiply(multiply(occurrence, scaled(row.unitsPerOccurrencePpm, 1000000)), value(row.unitCostMicros));
    return {id:row.id, stage:row.stage, implementation:row.implementation, perRequest, costMicrosPerRequest:rounded(perRequest)};
  });
  const humanRows = scenario.residual.map(row => {
    const minutes = multiply(scaled(row.exceptionsPerRequestPpm, 1000000), value(row.minutesPerException));
    const perRequest = multiply(minutes, divide(value(row.hourlyCostMicros), ratio(60)));
    return {id:row.id, stage:row.stage, perRequest, minutes, costMicrosPerRequest:rounded(perRequest)};
  });
  const nextRequest = sum([...operationRows,...humanRows].map(row => row.perRequest));
  const shared = sum(scenario.monthly.map(row => multiply(value(row.amountMicros), scaled(row.allocationBps, 10000))));
  const investments = scenario.investments.map(row => ({id:row.id, kind:row.kind,
    monthly:divide(multiply(value(row.amountMicros), scaled(row.allocationBps, 10000)), value(row.amortizationMonths))}));
  const amortized = sum(investments.map(row => row.monthly));
  const variableMonthly = multiply(nextRequest, requests);
  const marginal = divide(nextRequest, acceptance);
  const recurring = divide(plus(variableMonthly, shared), accepted);
  const fullyLoaded = divide(plus(plus(variableMonthly, shared), amortized), accepted);
  const human = multiply(value(scenario.humanBaseline.minutesPerAccepted),
    divide(value(scenario.humanBaseline.hourlyCostMicros), ratio(60)));
  const tiers = {marginal, recurring, fullyLoaded};
  const comparison = Object.fromEntries(Object.entries(tiers).map(([name,cost]) => {
    const delta = cost === null || human === null ? null : human.n*cost.d-cost.n*human.d;
    const breakEvenMinutes=multiply(divide(cost,value(scenario.humanBaseline.hourlyCostMicros)),ratio(60));
    return [name,{outcome:delta === null ? 'unknown' : delta > 0n ? 'win' : delta < 0n ? 'loss' : 'tie',
      breakEvenHumanMinutes:approximate(breakEvenMinutes),
      breakEvenHumanSeconds:rounded(multiply(breakEvenMinutes,ratio(60)))}];
  }));
  return {name:scenario.name,currency,volume:{requestsPerMonth:approximate(requests),
    attemptsPerMonth:approximate(multiply(requests,attempts)),acceptedPerMonth:approximate(accepted),
    utilizationBps:scenario.utilizationBps.value,acceptanceBps:scenario.acceptanceBps.value},
    costs:{nextRequestMicros:rounded(nextRequest),marginalMicrosPerAccepted:rounded(marginal),
      recurringMicrosPerAccepted:rounded(recurring),fullyLoadedMicrosPerAccepted:rounded(fullyLoaded),
      variableMonthlyMicros:rounded(variableMonthly),sharedMonthlyMicros:rounded(shared),
      amortizedMonthlyMicros:rounded(amortized)},
    residualHumanMinutesPerRequest:approximate(sum(humanRows.map(row=>row.minutes))),
    humanBaselineMicrosPerAccepted:rounded(human),comparison,unknownInputs:unknowns(scenario),
    components:{operations:operationRows.map(({perRequest,...row})=>row),
      humanExceptions:humanRows.map(({perRequest,minutes,...row})=>row),
      investments:investments.map(({monthly,...row})=>({...row,amortizedMonthlyMicros:rounded(monthly)}))}};
}
export function evaluateAutomatedCosts(raw) {
  const record = inspectAutomatedCosts(raw);
  return {schema:'alpha-automated-cost-summary/v1',offeringId:record.offeringId,currency:record.currency,
    monetaryUnit:'one million micros per currency unit; final monetary outputs rounded upward once',
    scenarios:record.scenarios.map(scenario=>evaluateScenario(scenario,record.currency)),
    scope:'Conditional automated-configuration planning over explicitly labeled inputs. Expected failed attempts and residual exceptions are charged. Missing live execution is not qualified by this calculation; no payment, guaranteed acceptance or measured saving is established.',
    decisionBoundary:'Required objective, input-rights, scope and execution approvals remain user decisions. A zero routine handling scenario never grants authority.'};
}
