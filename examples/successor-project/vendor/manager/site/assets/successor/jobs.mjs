import { emptyDraft, validateDraft, toMetadata, toConsoleDraft, normalizeBudget, publicInputURLs } from '../employer-model.mjs';
import { parseUSDC, splitPayment } from '../payments.mjs';
import { fail, keys, text, canonical, sha256, isHash, publicOnly } from './safe.mjs';

export function planAlternatives(state) {
  const active = state.candidates.find(c => c.id === state.active);
  return [
    { id: 'retain', available: Boolean(active), reason: 'Keep the selected local version and its limitations.' },
    { id: 'repair', available: Boolean(active?.gaps.length), reason: 'Apply the reviewed local improvement and compare actual artifacts.' },
    { id: 'build', available: state.mission.kind !== 'custom', reason: 'Build a new bounded candidate from the supplied template.' },
    { id: 'rent', available: false, reason: 'No provider quote or commissioned runtime is connected.' },
    { id: 'partner', available: false, reason: 'No partner capacity or independently controlled review has been confirmed.' },
    { id: 'reserve', available: false, reason: 'Draft allowances do not reserve workforce capacity or funds.' },
    { id: 'stop', available: true, reason: 'Keep your files; do not run or spend further.' },
  ];
}
export async function prepareImprovement(state, { budget, repairReserve = '0', days = '7', inputURLs = '', requested = '' }) {
  fail(typeof budget === 'string', 'USDC_PRICE_REQUIRED');
  const price = normalizeBudget(budget), reserve = repairReserve === '0' ? 0n : parseUSDC(repairReserve);
  const active = state.candidates.find(c => c.id === state.active);
  fail(active || state.mission.kind === 'custom', 'SELECT_VERSION');
  const fr = state.mission.language === 'fr';
  const goal = requested.trim() || (state.mission.kind === 'analyst' ? (fr ? 'Compter une seule fois les lignes identiques ayant le même identifiant; refuser les doublons contradictoires.' : 'Count identical rows with the same ID once; reject conflicting duplicate IDs.') : state.mission.kind === 'website' ? (fr ? 'Ajouter une navigation au clavier vers chaque section, en conservant le contenu.' : 'Add keyboard-accessible section navigation while preserving all content.') : state.mission.purpose);
  text(goal, 1500); publicOnly(goal); publicInputURLs(inputURLs);
  const draft = emptyDraft(); draft.template = state.mission.kind === 'analyst' ? 'dashboard' : state.mission.kind === 'website' ? 'demo' : 'docs'; draft.stage = 2;
  Object.assign(draft.fields, { title: (state.mission.name || 'SUCCESSOR Ω') + (fr ? ' — amélioration' : ' — improvement'), summary: goal, inputs: inputURLs, deliverables: state.mission.kind === 'custom' ? state.mission.outputs : state.mission.kind === 'website' ? 'index.html\nEditable source and reproduction instructions\nchecker-results.json' : 'result.json\nReadable report and editable source\nchecker-results.json', acceptance: state.mission.kind === 'custom' ? state.mission.success : state.mission.kind === 'website' ? 'Preserve every source heading and paragraph.\nEvery section has a keyboard-accessible navigation link.\nNo network requests, script, form submission or external effects.\nSeparate checker and browser inspection of actual delivered bytes.' : 'Recompute every total from original immutable inputs using a separate implementation.\nUse exact decimal arithmetic; reject malformed input and conflicting duplicate IDs.\nPreserve all failed checks, limitations and the incumbent.\nA passing local check is not independent production qualification.', requirements: 'Public, licensed, synthetic, nonpersonal inputs only.\nNo payment, wallet, private data or inherited authority.\nIndependent qualification and current operator-budget admission before paid execution.\nNo atomic project settlement; earlier paid work may remain paid after later failure.', budget: price, days });
  const errors = validateDraft(draft); fail(!errors.length, 'EMPLOYER_DRAFT', errors[0]?.code);
  const frozenInput = { name: 'mission.json', content: canonical(state.mission), sha256: await sha256(state.mission) };
  const payout = splitPayment(price, 8);
  const plan = { schema: 'agijobmanager/successor-improvement-draft/v1', missionSha256: frozenInput.sha256, candidateSha256: active?.id || null, goal, currency: { symbol: 'USDC', chainId: 1, decimals: 6 }, pricing: { jobBaseUnits: parseUSDC(price).toString(), repairReserveBaseUnits: reserve.toString(), totalPlanBaseUnits: (parseUSDC(price) + reserve).toString(), source: 'explicit-user-planning-allowance', quote: false, reservedFunds: false, unknownCosts: ['gas', 'provider-usage', 'hosting', 'independent-review', 'maintenance', 'unwind'], avoidDoubleCounting: 'Operator price may already include processing and review. Verify before adding external costs.' }, successfulIllustration: { validatorPercentage: 8, sharedReviewers: payout.validators.toString(), wallet30: payout.wallet30.toString(), wallet10: payout.wallet10.toString(), agent: payout.agent.toString(), zeroValidatorAgent: (payout.cost - payout.wallet30 - payout.wallet10).toString(), bondsAndClaims: 'separate', observedLivePolicy: false }, draft, metadata: toMetadata(draft, state.mission.language, 'local-draft-no-publication'), consoleDraft: toConsoleDraft(draft, state.mission.language), immutableInputs: [frozenInput], outputByteLimit: 300000, maxSeconds: 600, dependencies: [], mode: 'draft-only', authorization: 'none', payment: 'unfunded', blockers: ['Publish the exact reviewed input bytes at public immutable references with explicit consent.', 'Bind the commissioned Agent and reviewer runtime hashes and available capabilities.', 'Set the verified deployment, future deadline, current qualification and action-bound operator-budget admission.', 'Close applicable commissioning gates separately; confirm the exact transaction in the existing console.'] };
  publicOnly(canonical(plan)); return { ...plan, commitment: await sha256(plan) };
}
export async function validateImprovement(plan) {
  fail(plan && typeof plan === 'object', 'PLAN');
  keys(plan, ['schema', 'missionSha256', 'candidateSha256', 'goal', 'currency', 'pricing', 'successfulIllustration', 'draft', 'metadata', 'consoleDraft', 'immutableInputs', 'outputByteLimit', 'maxSeconds', 'dependencies', 'mode', 'authorization', 'payment', 'blockers', 'commitment'], 'PLAN_FIELDS');
  const { commitment, ...record } = plan; fail(isHash(commitment) && commitment === await sha256(record), 'PLAN_CHANGED');
  fail(plan.schema === 'agijobmanager/successor-improvement-draft/v1' && plan.mode === 'draft-only' && plan.authorization === 'none' && plan.payment === 'unfunded', 'AUTHORITY_NONE');
  fail(canonical(plan.currency) === canonical({ symbol: 'USDC', chainId: 1, decimals: 6 }), 'TOKEN_SEPARATION');
  fail(!validateDraft(plan.draft).length && canonical(toConsoleDraft(plan.draft, plan.metadata.properties.locale === 'fr-CA' ? 'fr' : 'en')) === canonical(plan.consoleDraft), 'DRAFT_CHANGED');
  fail(canonical(toMetadata(plan.draft, plan.metadata.properties.locale === 'fr-CA' ? 'fr' : 'en', 'local-draft-no-publication')) === canonical(plan.metadata), 'METADATA_CHANGED');
  fail(plan.pricing.jobBaseUnits === parseUSDC(plan.draft.fields.budget).toString() && /^(?:0|[1-9]\d{0,24})$/.test(plan.pricing.repairReserveBaseUnits) && BigInt(plan.pricing.totalPlanBaseUnits) === BigInt(plan.pricing.jobBaseUnits) + BigInt(plan.pricing.repairReserveBaseUnits), 'PLAN_PRICE');
  fail(plan.pricing.reservedFunds === false && plan.pricing.quote === false, 'AUTHORITY_NONE');
  fail(Array.isArray(plan.immutableInputs) && plan.immutableInputs.length === 1 && plan.immutableInputs[0].name === 'mission.json' && plan.immutableInputs[0].sha256 === plan.missionSha256 && canonical(plan.dependencies) === '[]' && plan.outputByteLimit === 300000 && plan.maxSeconds === 600, 'PLAN_BOUNDS');
  for (const input of plan.immutableInputs) { keys(input, ['name', 'content', 'sha256'], 'INPUT_FIELDS'); fail(input.sha256 === await sha256(input.content), 'INPUT_CHANGED'); }
  return plan;
}
export function validateGraph(stages, ceilingBaseUnits) {
  fail(Array.isArray(stages) && stages.length > 0 && stages.length <= 32 && /^(?:0|[1-9]\d{0,24})$/.test(ceilingBaseUnits), 'GRAPH');
  const ids = new Map(); let reserved = 0n;
  for (const stage of stages) {
    keys(stage, ['id', 'dependencies', 'costBaseUnits', 'acceptedInputs'], 'STAGE_FIELDS'); text(stage.id, 80); fail(!ids.has(stage.id), 'GRAPH_DUPLICATE'); ids.set(stage.id, stage);
    fail(/^(?:0|[1-9]\d{0,24})$/.test(stage.costBaseUnits), 'STAGE_COST'); reserved += BigInt(stage.costBaseUnits);
    fail(Array.isArray(stage.dependencies) && new Set(stage.dependencies).size === stage.dependencies.length && Array.isArray(stage.acceptedInputs), 'DEPENDENCIES');
  }
  const complete = new Set(), visiting = new Set();
  const visit = id => { fail(ids.has(id) && !visiting.has(id), 'GRAPH_CYCLE'); if (complete.has(id)) return; visiting.add(id); const stage = ids.get(id); for (const parent of stage.dependencies) { visit(parent); fail(stage.acceptedInputs.some(input => input.stage === parent && isHash(input.artifactSha256) && input.independentlyAccepted === true), 'DEPENDENCY_EVIDENCE'); } visiting.delete(id); complete.add(id); };
  for (const id of ids.keys()) visit(id); fail(reserved <= BigInt(ceilingBaseUnits), 'PLAN_CAPITAL');
  return { reserveRequiredBaseUnits: reserved.toString(), futureReceiptsUsed: false, atomicSettlement: false, authority: 'none' };
}
