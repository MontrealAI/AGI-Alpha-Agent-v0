import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { balancedPanel, COST_SCHEDULES } from './network_market.mjs';
const protocol = {
  schema: 'capability-advantage-market-protocol/v1',
  status: 'DRAFT_NOT_EXECUTED',
  market_outcomes_inspected: false,
  model: 'Source-bound numerical service procurement and network capability reuse',
  original_source: 'Existing canonical automated-costs and shadow-ledger plus unchanged strategic-market cash helpers',
  four_primary_arms: {A: 'Independent retained experience, ordinary tools and best measured reconstruction',
    B: 'Same capabilities through competent validated registry', C: 'Same capabilities through graph',
    D: 'Strong practical conventional implementation and reconstruction'},
  offering: 'One independently requested stage service per simulated purchase; no triple billing of a connected research chain',
  evidence_boundary: 'Finite executed case resampling; prior raw capability NOT RUN remains unknown. No inference of unique unsupported capability.',
  weeks: 52, original_seed_cents: 100000, reserve_cents: 20000,
  buyer_value_cents: 5000, error_loss_cents: 10000,
  buyer_value_basis: 'Unvalidated demand assumption; no measured willingness to pay',
  schedules: COST_SCHEDULES,
  conditions: balancedPanel(),
  design: '48 fixed balanced-marginal sensitivity cells, not a full factorial or empirical market distribution',
  seeds: Array.from({length: 16}, (_, i) => 12001 + i),
  expected: {cells: 144, paired_worlds: 2304, primary_enterprise_histories: 9216},
  finance_control: 'Same-seed no-later-shared-capability replay for B/C when later investment occurs; otherwise unchanged operations and explicit outside-prototype cost. This is a causal control, not an additional sampled world.',
  funding_gate: 'G1 may use seed liquidity; G2/G3 require currently generated funds after obligations and one reserve, forecast full-cost benefit, and tested source.',
  succession_gate: 'G2+G3 later investment bundle ONLY: every prototype cost funded from operating-generated resources, actual modeled use, aggregate direct cost repayment and positive cash/unrounded project-inclusive difference against the no-later-capability control. Individual generations are not qualified.',
  unknown_actual_cost_boundary: 'No affirmative Level3/5 actual-cost promotion; actual observed receipts zero',
  demand_and_competition: 'Buyers choose enterprise, conventional alternative, own construction/retention or abstention. Competitor copying pays a finite explicit reconstruction cost; internal contributor fee is redistribution only.',
  model_limitations: ['All residual attention and monetary prices are assumptions.',
    'Elapsed constructor time is not active human labor or measured model billing.',
    'Validation carries full costs; no proof/trust/quality premium is assumed.',
    'Stronger reconstruction is a tenfold cost stress, not a newly executed stronger foundation model.',
    'The 4/16/64 recipients are simulated; they do not enlarge the actual comparator sample.',
    'No equilibrium, global uniqueness, autonomous discovery or Level6 acceleration claim.'],
  limits: {wall_seconds: 900, cpu_seconds: 900},
  stopping_rule: 'Exactly the frozen cells/seeds once; retain partial files and failure receipt on budget/invariant failure. No favorable substitution or automatic restart.',
  calibration_path: 'calibration.json',
  frozen_at_utc: null,
  registration_url: null,
  representative: {condition_id: 'structural-01', schedule_id: 'reference', seed: 12001}
};
writeFileSync(fileURLToPath(new URL('./market-protocol.json', import.meta.url)), JSON.stringify(protocol, null, 2) + '\n', {flag: 'wx'});
process.stdout.write(JSON.stringify({protocol: 'market-protocol.json', outcomes_run: 0, cells: 144, paired_worlds: 2304}) + '\n');
