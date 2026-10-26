// SPDX-License-Identifier: Apache-2.0
import {readFileSync, writeFileSync, mkdirSync, readdirSync, statSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve, dirname, basename, join} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {AUTOMATED_COST_SCHEMA, AUTOMATED_STAGES, evaluateAutomatedCosts} from '../discovery/canonical/automated-costs.mjs';
import {SCHEMA, replayLedger, calculateInvestment} from '../discovery/canonical/shadow-ledger.mjs';

export const ECONOMIC_SCHEMA = 'value-compounds-economic-input/v1';
export const HORIZONS = Object.freeze([1, 4, 12, 52, 250]);
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,49}$/;
const MAX_AMOUNT = 1_000_000_000_000;
const MAX_BYTES = 20_000_000;
const CANONICAL_SHA256 = Object.freeze({
  'automated-costs.mjs':'0dfca3ae4e7ef1d17bc78521f91917ef068280cf832d3565c354de2085c52506',
  'shadow-ledger.mjs':'cdc7c5a73593050a9af79b54589462e27f61b868e88ca6985d5cb639f3066d21'
});
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const fact = (value, basis, reference) => ({value, basis, reference});
const unknown = reference => fact(null, 'unknown', reference);
const convention = (value, reference) => fact(value, 'estimated', reference);
const SOURCE = {
  us_wage: {currency:'USD', hourly_micros:50_140_000, basis:'sourced',
    reference:'https://www.bls.gov/news.release/ocwage.t01.htm', period:'2025-05'},
  montreal_wage: {currency:'CAD', hourly_micros:46_260_000, basis:'sourced',
    reference:'https://on.jobbank.gc.ca/marketreport/wages-occupation/22511/geo25154', period:'2024'}
};

function plain(value, label) {
  if (!value || Array.isArray(value) || Object.getPrototypeOf(value) !== Object.prototype)
    throw Error(`${label} must be a plain object`);
  return value;
}
function fields(value, allowed, label) {
  plain(value, label);
  for (const key of Object.keys(value)) if (!allowed.includes(key)) throw Error(`Unknown ${label} field: ${key}`);
}
function identifier(value, label) {
  if (typeof value !== 'string' || !ID.test(value)) throw Error(`Invalid ${label}`);
  return value;
}
function reference(value, fallback) {
  if (value === undefined) return fallback;
  if (typeof value !== 'string' || !value.trim() || value.length > 1024 || /[\u0000-\u001f]/.test(value))
    throw Error('Invalid evidence reference');
  return value;
}
function nonnegative(value, label) {
  if (value === null || value === undefined) return null;
  if (!Number.isSafeInteger(value) || value < 0 || value > MAX_AMOUNT) throw Error(`Invalid ${label}`);
  return value;
}
function fileRecord(path) {
  const bytes = readFileSync(path);
  if (bytes.length > MAX_BYTES) throw Error(`Input exceeds ${MAX_BYTES} bytes: ${path}`);
  return {path, sha256:sha(bytes), bytes:bytes.length, data:JSON.parse(bytes)};
}
function totalOrUnknown(values) {
  if (values.some(value => value === null)) return null;
  const total = values.reduce((a,b) => a+b, 0);
  if (!Number.isSafeInteger(total)) throw Error('Unsafe total');
  return total;
}

export function costTemplate(capabilityId = 'call-compatibility', currency = 'USD') {
  identifier(capabilityId, 'capability_id');
  if (!['USD','CAD'].includes(currency)) throw Error('Benchmark currency must be USD or CAD');
  const wage = currency === 'USD' ? SOURCE.us_wage : SOURCE.montreal_wage;
  const scenarios = ['base','conservative','stress'].map(name => ({
    name,
    capacityRequestsPerMonth:unknown('Real monthly capacity has not been measured.'),
    utilizationBps:unknown('Paid utilization and demand have not been observed.'),
    acceptanceBps:unknown('Future operating acceptance cannot be inferred from finite research cases.'),
    attemptsPerRequestPpm:unknown('Complete production attempts, recovery and fallback rates are unmeasured.'),
    operations:AUTOMATED_STAGES.map(stage => ({
      id:`${stage}-inclusive`, stage, frequency:'request',
      unitsPerOccurrencePpm:convention(1_000_000, 'One inclusive accounting row for this stage per request; not a measured activity count.'),
      unitCostMicros:unknown(`Complete attributable ${stage} cost, including inference, tools and compute, is unpriced.`),
      implementation:'modeled'
    })),
    residual:[{id:'residual-exceptions',stage:'recovery',
      exceptionsPerRequestPpm:unknown('Residual human exception frequency is unmeasured.'),
      minutesPerException:unknown('No human exception duration has been measured.'),
      hourlyCostMicros:unknown('No operator wage or contractor rate is assigned to the research assistant.')}],
    monthly:[
      {id:'shared-capacity',kind:'capacity',amountMicros:unknown('Attributable hosting, storage, tools and idle-capacity charges are unknown.'),allocationBps:convention(10000,'Row means attributable share only; do not charge the whole unrelated enterprise.')},
      {id:'shared-maintenance',kind:'maintenance',amountMicros:unknown('Required recurring maintenance has not been priced.'),allocationBps:convention(10000,'Row means attributable share only.')},
      {id:'business-costs',kind:'business',amountMicros:unknown('Attributable delivery-business costs and obligations have not been priced.'),allocationBps:convention(10000,'Row means attributable share only.')}
    ],
    investments:[
      {id:'discovery-and-unsuccessful',kind:'development',amountMicros:unknown('Include bounded discovery and rejected/unsuccessful candidates; complete inference bill unavailable.'),allocationBps:convention(10000,'Only costs attributable to this selected capability.'),amortizationMonths:unknown('No supported demand horizon for amortization.')},
      {id:'construction-and-validation',kind:'development',amountMicros:unknown('Complete construction, validation, integration and packaging costs are unknown.'),allocationBps:convention(10000,'Only costs attributable to this selected capability; no duplication of discovery.'),amortizationMonths:unknown('No supported demand horizon for amortization.')}
    ],
    humanBaseline:{minutesPerAccepted:unknown('No matched competent-human duration has been measured.'),
      hourlyCostMicros:fact(wage.hourly_micros,'sourced',`${wage.reference}; reference period ${wage.period}; wage only, not customer price.`)}
  }));
  return {schema:AUTOMATED_COST_SCHEMA,offeringId:capabilityId,currency,scenarios};
}

export function finiteInvestmentGrid(supplied = {}) {
  fields(supplied, ['label','basis','constructionCostMinor','failedConstructionCostMinor','maintenancePerReuseMinor','expectedSavingPerReuseMinor'], 'sensitivity');
  const numeric = Object.entries(supplied).some(([key,value]) => key.endsWith('Minor') && value !== null);
  if (numeric && supplied.basis !== 'assumed') throw Error('Numeric sensitivity inputs must be explicitly labeled assumed');
  const input = Object.fromEntries(['constructionCostMinor','failedConstructionCostMinor','maintenancePerReuseMinor','expectedSavingPerReuseMinor'].map(key => [key,supplied[key] ?? null]));
  return {label:reference(supplied.label,'Symbolic finite investment; no monetary inputs supplied'),
    evidence_class:'modeled',currency:'USD',monetary_unit:'cents',
    horizon_basis:'Assumed numbers of future substantive missions; not observed demand or repeated benchmark runs.',
    actual_financial_investment_executed:false,
    rows:HORIZONS.map(remainingReuses => {
      const result = calculateInvestment({...input,remainingReuses});
      const saving = result.expectedSavingPerReuseMinor, maintenance = result.maintenancePerReuseMinor;
      const affordable = saving === null || maintenance === null ? null : remainingReuses*(saving-maintenance);
      if (affordable !== null && !Number.isSafeInteger(affordable)) throw Error('Unsafe affordable investment');
      return {...result,maximumAffordableCompleteInvestmentMinor:affordable,
        economically_admitted:false,
        decision:result.paysBackWithinHorizon === null ? 'UNKNOWN_MONETARY_REPAYMENT' : result.paysBackWithinHorizon ? 'CONDITIONAL_SCENARIO_ONLY' : 'SCENARIO_DOES_NOT_REPAY'};
    }),
    equation:'I_max(N) = N * (incremental_delivery_saving_per_mission - incremental_maintenance_per_mission)',
    unknown_cost_policy:'Null is unknown. No simulation changes actual revenue, cash, obligations or admission.'};
}

export function humanThresholds(requests = []) {
  if (!Array.isArray(requests) || requests.length > 100) throw Error('Invalid threshold requests');
  return {actual_human_duration_minutes:null,actual_customer_price_minor:null,
    normalized:[SOURCE.us_wage,SOURCE.montreal_wage].map(row => ({...row,
      minutes_per_currency_unit:60_000_000/row.hourly_micros,
      interpretation:'Algebraic crossing for equal accepted scope; not an observed duration or saving.'})),
    user_supplied_scenarios:requests.map(row => {
      fields(row,['kind','currency','amountMinor','equal_customer_effort_assumption','reference'],'human threshold');
      if (!['provider_cost','customer_price'].includes(row.kind) || !['USD','CAD'].includes(row.currency)) throw Error('Invalid threshold type/currency');
      const amountMinor = nonnegative(row.amountMinor,'threshold amount');
      if (row.equal_customer_effort_assumption !== undefined && typeof row.equal_customer_effort_assumption !== 'boolean') throw Error('Invalid effort assumption');
      const wage = row.currency === 'USD' ? SOURCE.us_wage : SOURCE.montreal_wage;
      const comparable = row.kind === 'provider_cost' || row.equal_customer_effort_assumption === true;
      return {kind:row.kind,currency:row.currency,amountMinor,evidence_class:'modeled',
        reference:reference(row.reference,'User-input conditional threshold; no price charged or collected.'),
        equal_customer_effort_assumption:row.equal_customer_effort_assumption ?? null,
        break_even_human_minutes:amountMinor === null || !comparable ? null : amountMinor*600000/wage.hourly_micros,
        reason:comparable ? 'Wage-only matched-scope threshold; excludes unspecified differences in responsibility and tools.' : 'Customer effort difference is unknown; no customer-saving threshold asserted.'};
    })};
}

function canonicalLedger(capabilityId, observations, evidenceRef) {
  const observed = plain(observations,'observed');
  if (observed.collections_minor !== undefined && observed.collections_minor !== 0)
    throw Error('This nontransactional study has no paid receipts; supplied collections must be zero.');
  const supplied = observed.missions;
  if (supplied !== undefined && (!Array.isArray(supplied) || supplied.length > 400)) throw Error('Invalid mission inventory');
  const ids = new Set();
  const realMissions = (supplied || []).map(row => {
    fields(row,['mission_id','acceptance','reference'],'mission');
    identifier(row.mission_id,'mission_id');
    if (row.mission_id === 'study-investment' || ids.has(row.mission_id)) throw Error('Duplicate/reserved mission identity');
    ids.add(row.mission_id);
    if (!['accepted','rejected','unknown'].includes(row.acceptance)) throw Error('Invalid mission acceptance');
    return {id:`${row.mission_id}:mission`,type:'mission',missionId:row.mission_id,acceptance:row.acceptance,reference:reference(row.reference,evidenceRef)};
  });
  const project = {id:'study-investment:mission',type:'mission',missionId:'study-investment',acceptance:'unknown',
    reference:'Research investment account for the tested asset; accounting container, not a delivered customer mission.'};
  const events = [project,...realMissions];
  const add = (missionId,type,category,amountMinor,basis,ref) => events.push({id:`${missionId}:${type}:${category}`,type,missionId,category,amountMinor,basis,reference:ref});
  for (const mission of [project,...realMissions]) {
    const id = mission.missionId;
    add(id,'revenue','collected',0,'observed','This internal, nontransactional study collected no customer payment.');
    add(id,'cost','delivery',null,'unknown',id === 'study-investment' ? 'Research preparation, testing and delivery costs unpriced; excludes separately attributed capability investment.' : 'Complete execution, verification, retries, recovery and delivery charges unknown.');
    add(id,'cost','business',null,'unknown','Attributable business costs have not been measured.');
    add(id,'cost','maintenance',null,'unknown','Attributable maintenance and retained storage costs unknown.');
    add(id,'cost','capability',id === 'study-investment' ? null : 0,id === 'study-investment' ? 'unknown' : 'observed',
      id === 'study-investment' ? 'All attributable discovery, rejected candidates, construction, validation and integration charged once here; monetary sum unavailable.' : 'Capability investment allocated to the single study-investment account, never repeated per mission.');
    add(id,'reserve','reliability',null,'unknown','Required reliability and refund reserve not estimated; no arbitrary percentage.');
    add(id,'obligation','unpaid',null,'unknown','Complete unpaid service and research obligations unknown.');
  }
  events.push({id:'study-investment:capability:economic-rejection',type:'capability',missionId:'study-investment',
    capabilityId,action:'rejected',reference:'Economic admission rejected pending identified complete cost, real demand and supported repayment; separate engineering evaluation may still admit a useful tool.'});
  const ledger = {schema:SCHEMA,currency:'USD',events};
  return {ledger,summary:replayLedger(ledger),substantive_mission_count:realMissions.length,
    accepted_research_missions:realMissions.filter(row => row.acceptance === 'accepted').length,
    rejected_research_missions:realMissions.filter(row => row.acceptance === 'rejected').length,
    investment_account_is_customer_mission:false};
}

export function buildEconomics(input = {}, provenance = {}) {
  fields(input,['schema','capability_id','observed','canonical_cost_record','sensitivity','human_thresholds'],'economic input');
  if (input.schema !== undefined && input.schema !== ECONOMIC_SCHEMA) throw Error('Unsupported economic input schema');
  const capabilityId = identifier(input.capability_id ?? 'call-compatibility','capability_id');
  const observations = input.observed ?? {};
  fields(observations,['collections_minor','missions','resources','limitations'],'observed');
  const evidenceRef = reference(provenance.metrics_reference,'No experiment metrics supplied; no acceptance outcome inferred.');
  const costs = input.canonical_cost_record ?? costTemplate(capabilityId);
  if (costs.offeringId !== capabilityId) throw Error('Canonical cost input must describe the same tested capability');
  if (costs.currency !== 'USD') throw Error('The finite study ledger is USD; CAD human thresholds remain separate and are never converted implicitly');
  const projection = evaluateAutomatedCosts(costs);
  const accounts = canonicalLedger(capabilityId,observations,evidenceRef);
  return {schema:'value-compounds-economics/v1',capability_id:capabilityId,
    scope:'Nontransactional economic evidence for the tested static Python call-compatibility capability; no payments or deployment.',
    provenance,
    accounting_status:{actual_collections_minor:0,currency:'USD',starting_funded_capital_minor:null,
      complete_investment_cost_minor:null,unpaid_obligations_minor:null,required_reserve_minor:null,
      unencumbered_cash_minor:null,earned_available_surplus_minor:null,
      financial_transactions_executed:0,new_paid_commitments_minor:0,observed_investment_outlay_minor:null,
      monetary_repayment_proven:false,economic_admission:'HOLD',
      reason:'No paid receipts; complete inference, construction, maintenance and residual attention costs are unidentified.'},
    empirical_resources:observations.resources ?? null,
    observed_limitations:observations.limitations ?? [],
    monetary_unit:'Canonical cost projections use currency micros; canonical shadow ledger/investment grid use cents. They are never added without conversion.',
    cost_template_status:input.canonical_cost_record ? 'User-supplied canonical conditional input, not a billed-cost attestation.' : 'The three canonical scenario names are schema-required unknown templates, not optimistic/conservative/stress forecasts.',
    canonical_cost_input:costs,canonical_cost_projection:projection,
    canonical_ledger:accounts.ledger,canonical_ledger_summary:accounts.summary,
    recorded_substantive_missions:accounts.substantive_mission_count,
    accepted_research_missions:accounts.accepted_research_missions,
    rejected_research_missions:accounts.rejected_research_missions,
    actual_paid_customer_missions:0,
    accounting_container_count:1,accounting_container_counts_as_job:false,
    cash_flow:{starting_capital_minor:null,observed_collections_minor:0,paid_delivery_minor:null,
      paid_investment_minor:null,unpaid_obligations_minor:null,required_reserves_minor:null,
      ending_cash_minor:null,available_to_commit_minor:null,
      equation:'B_t = B_previous + actual_collections + external_capital - paid_delivery - paid_investment; available = B_t - unpaid_obligations - required_reserves.',
      investment_execution:'No financial transaction or new paid commitment was executed; constructed-capability resource cost remains unknown. A null balance cannot authorize a new commitment.'},
    investment_sensitivity:finiteInvestmentGrid(input.sensitivity),
    human_comparison:humanThresholds(input.human_thresholds),
    required_cost_inventory:['discovery','rejected_opportunities','unsuccessful_candidates','construction','integration','inference','tools','compute','storage','requests','retries','verification','recovery','packaging','shared_maintenance','residual_human_attention','customer_effort'],
    prohibitions:['No-op checks and benchmark repetitions are not new customer jobs.','Elapsed assistant time is not a human wage or inference bill.','Customer savings are not enterprise collections.','Unknown costs are not zero.','A hypothetical positive scenario never changes actual economic admission.']};
}

function readMetering(path) {
  if (!path) return {files:[],events:[],monetary_cost_inferred:false};
  const files = statSync(path).isDirectory() ? readdirSync(path).filter(name => name.endsWith('.jsonl')).sort().map(name => join(path,name)) : [path];
  if (files.length > 100) throw Error('Too many metering files');
  const events = [], identities = [];
  for (const file of files) {
    const bytes = readFileSync(file);
    if (bytes.length > MAX_BYTES) throw Error('Metering file exceeds bound');
    const rows = bytes.toString('utf8').split('\n').filter(Boolean).map(line => JSON.parse(line));
    if (events.length+rows.length > 100000) throw Error('Too many metering records');
    identities.push({path:file,sha256:sha(bytes),bytes:bytes.length,events:rows.length});
    events.push(...rows.map((row,index) => ({...row,source_file:basename(file),line:index+1})));
  }
  return {files:identities,events,monetary_cost_inferred:false,
    note:'Operation timestamps, model/tool counts, resource samples and unknown charges are retained without converting elapsed assistant time into money.'};
}

function commandLine() {
  const args = process.argv.slice(2), options = {};
  for (let i=0;i<args.length;i+=2) {
    if (!['--input','--metrics','--metering','--out'].includes(args[i]) || !args[i+1]) throw Error('Usage: node src/economics.mjs [--input economics-input.json] [--metrics result-metrics.json] [--metering metering-directory] --out output-directory');
    if (options[args[i]]) throw Error('Duplicate argument');
    options[args[i]] = resolve(args[i+1]);
  }
  if (!options['--out']) throw Error('--out is required');
  const supplied = options['--input'] ? fileRecord(options['--input']) : null;
  const metrics = options['--metrics'] ? fileRecord(options['--metrics']) : null;
  const metering = readMetering(options['--metering']);
  const input = supplied?.data ?? metrics?.data?.economic_input ?? {};
  const canonical_sources = ['automated-costs.mjs','shadow-ledger.mjs'].map(name => {
    const path = join(ROOT,'discovery','canonical',name), bytes = readFileSync(path);
    if (sha(bytes) !== CANONICAL_SHA256[name]) throw Error(`Canonical source identity differs from the inspected study pin: ${name}`);
    return {path:`discovery/canonical/${name}`,sha256:sha(bytes),bytes:bytes.length,unmodified:true};
  });
  const provenance = {canonical_sources,metrics:metrics ? {path:metrics.path,sha256:metrics.sha256,bytes:metrics.bytes} : null,
    metrics_reference:metrics ? `Metrics ${basename(metrics.path)} SHA256 ${metrics.sha256}; only explicit economic_input observation mappings are interpreted.` : undefined,
    economic_input:supplied ? {path:supplied.path,sha256:supplied.sha256} : null,metering};
  const output = buildEconomics(input,provenance), dest = options['--out'];
  mkdirSync(dest,{recursive:true});
  const artifacts = {'economics.json':output,'canonical-cost-input.json':output.canonical_cost_input,
    'canonical-cost-output.json':output.canonical_cost_projection,'canonical-ledger.json':output.canonical_ledger,
    'canonical-ledger-output.json':output.canonical_ledger_summary,'investment-grid.json':output.investment_sensitivity};
  for (const [name,value] of Object.entries(artifacts)) writeFileSync(join(dest,name),JSON.stringify(value,null,2)+'\n');
  console.log(JSON.stringify({status:'complete',economic_admission:output.accounting_status.economic_admission,
    observed_collections_minor:0,full_cost_minor:null,repayment_proven:false,output_directory:dest,files:Object.keys(artifacts)}));
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) commandLine();
