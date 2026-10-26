// SPDX-License-Identifier: Apache-2.0
import { createHash } from 'node:crypto';
import { createReadStream, createWriteStream, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createGzip } from 'node:zlib';
import { once } from 'node:events';
import { pipeline } from 'node:stream/promises';
import { pairedContinuation } from './inherited/continuation.mjs';
import { ROOT, assembleInputs, bindCosts, directAlternativeComparison, fileAt, hypotheticalHumanBreakEven,
  readBound, readJSON, sha256, validateDesign, verifyInherited } from './adapter.mjs';

const assert = (ok, why) => { if (!ok) throw Error(why); };
const sum = values => values.reduce((a, b) => a + b, 0);
const write = (file, x) => writeFileSync(file, JSON.stringify(x, null, 2) + '\n');

export function verifyFreeze(inputs, freezePath, root = ROOT) {
  const d = inputs.design;
  assert(d.status === 'FROZEN_BEFORE_MARKET_OUTCOMES', 'Root must freeze market protocol before execution');
  assert(Number.isFinite(Date.parse(d.registeredAtUTC)) && typeof d.registrationURL === 'string' &&
    d.registrationURL.startsWith('https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850'), 'Public preregistration reference required');
  const bytes = readFileSync(fileAt(root, freezePath)), freeze = JSON.parse(bytes);
  assert(freeze.schema === 'agi-alpha-verified-capability-market-freeze/v1' && freeze.marketOutcomesInspected === false,
    'Explicit pre-outcome market source freeze required');
  const paths = new Set();
  for (const row of freeze.files) {
    assert(!paths.has(row.path), 'Duplicate frozen source'); paths.add(row.path); readBound(root, row);
  }
  const required = ['market/adapter.mjs', 'market/run-campaign.mjs', 'market/inherited/PROVENANCE.json',
    inputs.designPath, d.productionSummary, d.assetBindings, d.costAssumptions,
    ...inputs.inherited.files.map(x => x.path),
    ...Object.values(inputs.bindings.assets).flatMap(x => [x.admission_evidence_path, ...x.files.map(y => y.path)])];
  for (const path of required) assert(paths.has(path), `Required input absent from freeze: ${path}`);
  return {sha256:sha256(bytes), freeze, root};
}

export function distribution(values) {
  const known = values.filter(x => typeof x === 'number' && Number.isFinite(x)).sort((a, b) => a - b);
  const n = known.length, mean = n ? sum(known) / n : null;
  const q = p => { if (!n) return null; const i = (n - 1) * p; return known[Math.floor(i)] + (known[Math.ceil(i)] - known[Math.floor(i)]) * (i % 1); };
  const half = n > 1 ? 1.96 * Math.sqrt(sum(known.map(x => (x - mean) ** 2)) / (n - 1) / n) : null;
  return { n, missing:values.length - n, mean, min:n ? known[0] : null, p05:q(0.05), median:q(0.5), p95:q(0.95),
    max:n ? known.at(-1) : null, negative:known.filter(x => x < 0).length, zero:known.filter(x => x === 0).length,
    positive:known.filter(x => x > 0).length, meanMC95Low:half === null ? null : mean - half, meanMC95High:half === null ? null : mean + half };
}

function compactArm(run, arm, effect) {
  const s = run.summary, x = run.secondInvestment;
  const decision = x?.decisions?.find(r => Object.hasOwn(r, 'forecastUses'));
  const breakEven = hypotheticalHumanBreakEven({ completeOneoffCents:x?.declaredCompletePrototypeOneoffCostCents ?? null,
    maintenanceCents:decision?.forecastMaintenanceCents ?? null, forgoneContributionCents:decision?.expectedForgoneContributionCents ?? null,
    forecastUses:decision?.forecastUses ?? null, computeCentsSavedPerUse:effect?.exactConditionalComputeCentsSavedPerMission ?? null,
    hourlyProviderCents:run.config.hourlyProviderCents, passThrough:run.config.expectedPassThrough });
  return {
    arm, accepted:s.enterpriseAccepted, attempts:s.enterpriseAttempts, rejected:s.enterpriseRejected,
    enterpriseProfitCents:s.profitCents, projectInclusiveProfitCents:x ? x.projectProfitAfterCompletedPrototypeCostsCents : s.profitCents,
    finalCashCents:s.finalCashCents, collectionsCents:s.grossCollectionsCents, obligationsCents:s.obligationsCents,
    refundsCents:s.refundsCents, reserveCents:run.config.reserveCents, insolvent:s.insolvent,
    completeCostsKnown:x ? x.completeCostProfilePriced : true,
    completeOneoffCents:x?.declaredCompletePrototypeOneoffCostCents ?? (arm === 'A' ? 0 : null),
    secondCostsPaidCents:x?.completeRealizedSecondCostsCents ?? 0,
    outsideResearchCostCents:x ? x.outsideEnterprisePrototypeCostCents : 0,
    maintenanceCents:x?.maintenanceAccruedCents ?? 0,
    attempted:x?.modeledConstructionAttempted ?? false, financiallyAdmitted:x?.financiallyAdmitted ?? false,
    fundedFromGeneratedResources:x?.investmentPaidFromGeneratedResources ?? false,
    actualAssetInvocations:x?.actualAssetInvocationsInModel ?? 0,
    directAvoidedCostCents:x?.directAvoidedDeliveryCostCents ?? 0,
    directCostRepayment:x?.directCostRepayment ?? false,
    assetSHA256:x?.profile.assetSHA256 ?? null, fundingCheckpoint:x?.initialCheckpoint ?? null,
    terminalGeneratedResourcesCents:x?.terminalFunding.availableCents ?? null,
    prototypeCostCountedOnce:x?.completedResearchCostCountedExactlyOnce ?? null,
    firstDecision:x?.decisions?.[0] ?? null,
    commitmentDecision:x?.decisions?.find(d => ['invest-second-capability', 'operating-funded-unqualified-research-attempt'].includes(d.action)) ?? null,
    subcentComputeResidualMicrocents:x?.subcentComputeEffect?.netSavingsNotRepresentedByCentLedgerMicrocents ?? null,
    subcentComputeAbsoluteResidualUSD:x?.subcentComputeEffect?.maximumAbsoluteUnrepresentedUSD ?? null,
    hypotheticalHumanBreakEven:breakEven,
    actualCustomerCollectionsCents:0, globalAdoptionOverDirectD:null
  };
}

function summarizeCell(cell, rows) {
  const fields = ['accepted', 'attempts', 'rejected', 'enterpriseProfitCents', 'projectInclusiveProfitCents', 'finalCashCents',
    'collectionsCents', 'obligationsCents', 'completeOneoffCents', 'secondCostsPaidCents', 'outsideResearchCostCents',
    'maintenanceCents', 'actualAssetInvocations', 'directAvoidedCostCents', 'terminalGeneratedResourcesCents',
    'subcentComputeResidualMicrocents', 'subcentComputeAbsoluteResidualUSD'];
  return {
    id:cell.id, condition:cell.condition, policy:cell.policy, costProfile:cell.costProfileId,
    completedWorlds:rows.length, monetaryUnit:'SIMULATED_USD_CENTS',
    arms:Object.fromEntries(['A', 'B', 'C'].map(arm => [arm, {
      ...Object.fromEntries(fields.map(k => [k, distribution(rows.map(r => r.arms[arm][k]))])),
      hypotheticalHumanSecondsForRepayment:distribution(rows.map(r => r.arms[arm].hypotheticalHumanBreakEven.secondsPerUse)),
      counts:Object.fromEntries(['insolvent', 'attempted', 'financiallyAdmitted', 'fundedFromGeneratedResources', 'directCostRepayment']
        .map(k => [k, rows.filter(r => r.arms[arm][k]).length])),
      conditionalNativeFinancialGatePasses:arm === 'A' ? 0 : rows.filter(r => r.qualification[arm].conditionalModeledFinancialGatePassed).length
    }])),
    causal:Object.fromEntries(['B_minus_A_projectInclusiveProfitCents', 'C_minus_A_projectInclusiveProfitCents',
      'C_minus_B_projectInclusiveProfitCents', 'B_minus_A_profitCents', 'C_minus_A_profitCents', 'B_minus_A_accepted', 'C_minus_A_accepted']
      .map(k => [k, distribution(rows.map(r => r.causal[k]))])),
    scope:'Paired conditional scenario; intervals are descriptive Monte Carlo summaries, not observed market confidence.'
  };
}

async function fileHash(file) {
  const h = createHash('sha256'); for await (const bytes of createReadStream(file)) h.update(bytes); return h.digest('hex');
}

export async function runFrozenCampaign({ root = ROOT, designPath = 'protocol/market-design.json', freezePath, outputPath }) {
  const inputs = assembleInputs(root, designPath), receipt = verifyFreeze(inputs, freezePath, root);
  const output = fileAt(root, outputPath);
  assert(!existsSync(output), 'Refusing to overwrite/restart an existing research campaign');
  mkdirSync(dirname(output), {recursive:true}); mkdirSync(output);
  const start = performance.now(), cpu = process.cpuUsage(), startedUTC = new Date().toISOString();
  const resource = () => { const c = process.cpuUsage(cpu); return {wallSeconds:(performance.now() - start) / 1000, cpuSeconds:(c.user + c.system) / 1e6}; };
  const check = () => { const r = resource(); assert(r.wallSeconds <= 180 && r.cpuSeconds <= 180, 'Frozen180second budget reached'); };
  write(resolve(output, 'STARTED.json'), {schema:'agi-alpha-verified-capability-market-start/v1', startedUTC,
    freezeSHA256:receipt.sha256, expected:inputs.design.expected, actualCustomerCollectionsCents:0, actualTransactions:0});
  write(resolve(output, 'effect-calibration.json'), {productionSHA256:inputs.productionSHA256, effects:inputs.effects,
    directAlternative:directAlternativeComparison(inputs.production), costAssumptions:inputs.costs,
    nativeComparisonOnly:true, actualFullyLoadedCosts:null});
  const gzPath = resolve(output, 'complete-worlds.jsonl.gz'), gzip = createGzip({level:6}), dest = createWriteStream(gzPath, {flags:'wx'});
  let archiveError = null;
  const completion = pipeline(gzip, dest).catch(e => {archiveError = e;});
  const timer = setTimeout(() => {gzip.destroy(Error('Frozen wall budget reached'));}, 180000);
  const rawHash = createHash('sha256'), compact = [], representatives = [], cellRows = new Map(inputs.cells.map(x => [x.id, []]));
  let failure = null, current = null;
  try {
    for (const cell of inputs.cells) for (const seed of inputs.design.seeds) {
      current = {cell:cell.id, seed}; check(); if (archiveError) throw archiveError;
      const paired = pairedContinuation(cell.config, seed, cell.profiles);
      assert(paired.commonPrefixExact === true, 'Unequal inherited prefix');
      for (const arm of ['A', 'B', 'C']) {
        assert(paired.arms[arm].observedCustomerCollectionsCents === 0, 'Simulation mislabeled actual revenue');
        if (arm !== 'A' && paired.arms[arm].secondInvestment.completeCostProfilePriced)
          assert(paired.arms[arm].secondInvestment.completedResearchCostCountedExactlyOnce, 'Prototype cost duplicated/omitted');
      }
      const full = {schema:'agi-alpha-verified-capability-market-world/v1', ...current, condition:cell.condition,
        policy:cell.policy, costProfile:cell.costProfileId, sourceFreezeSHA256:receipt.sha256, paired};
      const line = JSON.stringify(full) + '\n'; rawHash.update(line);
      if (!gzip.write(line)) await once(gzip, 'drain');
      const causal = {...paired.causal, C_minus_B_projectInclusiveProfitCents:
        paired.causal.B_minus_C_projectInclusiveProfitCents === null ? null : -paired.causal.B_minus_C_projectInclusiveProfitCents};
      const row = {...current, condition:cell.condition, policy:cell.policy, costProfile:cell.costProfileId,
        arms:Object.fromEntries(['A', 'B', 'C'].map(arm => [arm, compactArm(paired.arms[arm], arm, inputs.effects[arm])])),
        causal, qualification:paired.qualification,
        alternatives:{retainIncumbent:'A', preserveReserve:'A retains original reserve and existing maintenance',
          registry:'B actual admitted composition', graph:'C actual admitted composition',
          directD:'Measured production alternative; complete global adoption cost remains unknown; see effect-calibration.json'},
        globalGraphAdoptionOverD:null};
      compact.push(row); cellRows.get(cell.id).push(row);
      if (cell.condition === inputs.design.representative.condition && seed === inputs.design.representative.seed)
        representatives.push(full);
      if (compact.length % 96 === 0) process.stdout.write(JSON.stringify({completed:compact.length, expected:1152, resources:resource()}) + '\n');
      check();
    }
  } catch (e) {failure = {message:e.message, at:current, partialOutputsRetained:true, automaticRetry:false};}
  finally {gzip.end(); await completion; clearTimeout(timer);}
  if (archiveError && !failure) failure = {message:archiveError.message, partialOutputsRetained:true, automaticRetry:false};
  const resources = resource();
  if ((resources.wallSeconds > 180 || resources.cpuSeconds > 180) && !failure)
    failure = {message:'Frozen budget reached in archive finalization', partialOutputsRetained:true, automaticRetry:false};
  const complete = failure === null && compact.length === inputs.design.expected.pairedWorlds;
  writeFileSync(resolve(output, 'compact-worlds.jsonl'), compact.map(x => JSON.stringify(x)).join('\n') + '\n');
  write(resolve(output, 'representative-histories.json'), representatives);
  const summary = {schema:'agi-alpha-verified-capability-market-summary/v1', complete, sourceFreezeSHA256:receipt.sha256,
    completedWorlds:compact.length, expected:inputs.design.expected, cells:inputs.cells.map(c => summarizeCell(c, cellRows.get(c.id))),
    actualCustomerCollectionsCents:0, actualTransactions:0, actualFullyLoadedCost:null, globalGraphAdoptionOverDirectD:null,
    interpretation:'All money is modeled USD. Unknown values remain null. Designed-cell frequencies are not market probabilities. This is a native-integration comparison, not an equilibrium or a global advantage over direct D.'};
  write(resolve(output, 'summary.json'), summary);
  write(resolve(output, 'execution.json'), {schema:'agi-alpha-verified-capability-market-execution/v1', startedUTC,
    completedUTC:new Date().toISOString(), complete, failure, resources, completedWorlds:compact.length,
    rawWorldsSHA256:rawHash.digest('hex'), compressedWorldsSHA256:await fileHash(gzPath), sourceFreezeSHA256:receipt.sha256,
    observedReceipts:0, transactions:0, noAutomaticRerun:true});
  if (!complete) throw Error(`Campaign incomplete; evidence retained: ${failure?.message ?? 'world count'}`);
  return {complete, pairedWorlds:compact.length, enterpriseHistories:compact.length * 3, outputPath, resources};
}

async function main(argv) {
  const args = {designPath:'protocol/market-design.json'};
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (['--design-only', '--validate-only', '--run'].includes(token)) args[token.slice(2)] = true;
    else if (['--design', '--freeze', '--output'].includes(token)) {
      assert(argv[i + 1] && !argv[i + 1].startsWith('--'), `Missing ${token}`);
      args[{'--design':'designPath', '--freeze':'freezePath', '--output':'outputPath'}[token]] = argv[++i];
    } else throw Error(`Unknown argument ${token}`);
  }
  assert(['design-only', 'validate-only', 'run'].filter(k => args[k]).length === 1, 'Choose exactly one design-only/validate-only/run mode');
  if (args['design-only']) {
    const d = validateDesign(readJSON(ROOT, args.designPath)), c = readJSON(ROOT, d.costAssumptions); verifyInherited();
    for (const p of d.costProfileIds) for (const a of ['B', 'C']) bindCosts(c, p, a);
    return {designValid:true, outcomesExecuted:0, expected:d.expected};
  }
  if (args['validate-only']) {
    const x = assembleInputs(ROOT, args.designPath);
    return {inputsValid:true, outcomesExecuted:0, cells:x.cells.length, effects:x.effects,
      directAlternative:directAlternativeComparison(x.production)};
  }
  assert(args.freezePath && args.outputPath, 'Frozen execution requires --freeze and fresh --output');
  return runFrozenCampaign(args);
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url))
  main(process.argv.slice(2)).then(x => console.log(JSON.stringify(x, null, 2))).catch(e => {console.error(e.stack); process.exitCode = 1;});
