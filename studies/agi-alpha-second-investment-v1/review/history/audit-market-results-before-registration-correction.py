"""Independently reconcile saved market archives; no simulator imports or runs."""
import collections
import csv
import datetime
import gzip
import hashlib
import json
import math
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'market/results/primary-01'
START = time.perf_counter()
CPU = time.process_time()
COUNTS = collections.Counter()
FAILURES = []


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def check(condition, category, context=''):
    COUNTS[category] += 1
    if not condition and len(FAILURES) < 100:
        FAILURES.append({'category': category, 'context': context})


def same(actual, expected):
    if actual is None or expected is None:
        return actual is expected
    if isinstance(actual, bool) or isinstance(expected, bool):
        return actual is expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-7)
    return actual == expected


def distribution(values):
    known = sorted(v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v))
    n = len(known)
    result = {'n': n, 'missing': len(values) - n, 'negative': sum(v < 0 for v in known),
              'zero': sum(v == 0 for v in known), 'positive': sum(v > 0 for v in known)}
    for key in ['mean', 'min', 'p05', 'median', 'p95', 'max', 'meanMC95Low', 'meanMC95High']:
        result[key] = None
    if not known:
        return result
    def quantile(q):
        position = (n - 1) * q
        lo, hi = math.floor(position), math.ceil(position)
        return known[lo] + (known[hi] - known[lo]) * (position - lo)
    mean = statistics.mean(known)
    half = 1.96 * statistics.stdev(known) / math.sqrt(n) if n > 1 else None
    result.update(mean=mean, min=known[0], max=known[-1], p05=quantile(.05),
                  median=quantile(.5), p95=quantile(.95),
                  meanMC95Low=None if half is None else mean-half,
                  meanMC95High=None if half is None else mean+half)
    return result


completion = read(OUT / 'completion.json')
summary = read(OUT / 'summary.json')
protocol = read(ROOT / 'market/campaign-protocol.json')
freeze = read(ROOT / 'market/campaign-freeze.json')
effect = read(ROOT / 'market/effect-profile.json')
costs = read(ROOT / 'market/cost-profiles.json')
check(completion['complete'] and completion['archiveCompleted'] and completion['failure'] is None, 'completion')
check(completion['completedWorlds'] == completion['attemptedWorlds'] == 1920 and completion['completedEnterpriseRuns'] == 5760, 'completion_counts')
check(completion['sourceFreezeSHA256'] == digest(ROOT / 'market/campaign-freeze.json'), 'freeze_binding')
check(protocol['status'] == 'FROZEN_BEFORE_MARKET_OUTCOMES' and protocol['registrationURL'].endswith('6423978767'), 'registration')
for row in freeze['files']:
    path = ROOT / 'market' / row['path']
    check(digest(path) == row['sha256'] and path.stat().st_size == row['bytes'], 'frozen_file', row['path'])
for filename, field in [('complete-paired-worlds.jsonl.gz', 'completePairedWorldsGzipSHA256'),
                        ('summary.json', 'summarySHA256'), ('compact-worlds.jsonl', 'compactWorldsSHA256')]:
    check(digest(OUT / filename) == completion[field], 'result_hash', filename)
check(completion['executionResources']['wallSeconds'] <= 180 and completion['executionResources']['cpuSeconds'] <= 180, 'execution_budget')
compact = [json.loads(line) for line in (OUT / 'compact-worlds.jsonl').read_text().splitlines()]
compact_by_key = {(row['groupId'], row['seed']): row for row in compact}
check(len(compact) == len(compact_by_key) == 1920, 'compact_unique_count')
groups = collections.defaultdict(list)
for row in compact:
    groups[row['groupId']].append(row)
expected_groups = {f"{condition['id']}__{cost}__{policy['id']}" for condition in protocol['conditions']
                   for cost in protocol['costProfileIds'] for policy in protocol['policies']}
expected_groups |= {f"reference__actual-unknown__{policy['id']}" for policy in protocol['policies']}
check(set(groups) == expected_groups and len(groups) == 80, 'all_groups_retained')
for group, rows in groups.items():
    check(sorted(row['seed'] for row in rows) == protocol['seeds'], 'all_seeds_retained', group)

summary_by_group = {group['groupId']: group for group in summary['groups']}
check(set(summary_by_group) == expected_groups and summary['complete'], 'summary_groups')
for group_id, records in groups.items():
    recorded = summary_by_group[group_id]
    check(recorded['complete'] and recorded['completedSeeds'] == recorded['expectedSeeds'] == 24, 'summary_denominator', group_id)
    for arm in ['A', 'B', 'C']:
        for key, stats in recorded['arms'][arm].items():
            if key == 'counts':
                continue
            expected = distribution([row['arms'][arm][key] for row in records])
            check(set(stats) == set(expected) and all(same(stats[k], v) for k, v in expected.items()), 'summary_arm_distribution', f'{group_id}/{arm}/{key}')
        for key, count in recorded['arms'][arm]['counts'].items():
            expected = (0 if arm == 'A' else sum(row['qualification'][arm]['conditionalModeledFinancialGatePassed'] for row in records)) if key == 'conditionalFinancialGatePasses' else sum(bool(row['arms'][arm][key]) for row in records)
            check(count == expected, 'summary_boolean_count', f'{group_id}/{arm}/{key}')
    for key, stats in recorded['causal'].items():
        expected = distribution([row['causal'][key] for row in records])
        check(set(stats) == set(expected) and all(same(stats[k], v) for k, v in expected.items()), 'summary_paired_distribution', f'{group_id}/{key}')


def cash_and_funds(run, week=None, stage=None):
    """Reconstruct recorded decision checkpoint from invoices and bills only.

    All registered collection delays are positive. At before-market, current-week
    delivery bills and current-stage second-asset charges have not yet occurred.
    """
    history, config = run['histories'], run['config']
    invoices = history['invoices']
    all_bills = history['bills']
    def included(bill):
        if week is None:
            return True
        if bill['week'] < week:
            return True
        if bill['week'] > week or bill['category'] == 'delivery':
            return False
        if not bill['reference'].startswith('second:'):
            return True
        if stage == 'afterConstruction':
            return True
        return stage == 'afterSearch' and bill['reference'].split(':')[-1] in ['priorDiscovery', 'discovery', 'rejectedCandidates']
    bills = [bill for bill in all_bills if included(bill)]
    paid = [bill for bill in bills if bill['paid'] and (week is None or bill['paidWeek'] <= week)]
    collections = sum(i['amountCents'] for i in invoices if i['status'] == 'collected' and (week is None or i['collectedWeek'] <= week))
    accrued = sum(bill['amountCents'] for bill in bills)
    paid_total = sum(bill['amountCents'] for bill in paid)
    unpaid = accrued - paid_total
    cash = config['initialCashCents'] + collections - paid_total
    opening = sum(bill['amountCents'] for bill in paid if bill['week'] == bill['paidWeek'] == 0 and bill['category'] == 'capability' and bill['reference'] == 'upfront historical R&D cost stress; paid from seed if affordable, never labeled earned financing')
    cash_bound = cash - unpaid - config['reserveCents']
    generated_bound = collections - accrued + opening
    return {'availableCents': max(0, min(cash_bound, generated_bound)), 'cashCents': cash,
            'unpaidObligationsCents': unpaid, 'reserveCents': config['reserveCents'],
            'collectedCents': collections, 'allAccruedCostsCents': accrued,
            'seedPaidOpeningHistoryCents': opening, 'cashBoundCents': cash_bound,
            'generatedBoundCents': generated_bound}


def audit_arm(run, arm, context):
    config, history, result = run['config'], run['histories'], run['summary']
    check(config['initialCashCents'] == 100000 and config['reserveCents'] == 20000 and config['weeks'] == 52, 'finite_enterprise', context)
    check(run['basis'] == 'SIMULATED' and run['observedCustomerCollectionsCents'] == result['actualRevenueCents'] == 0, 'no_actual_receipts', context)
    invoices = {i['id']: i for i in history['invoices']}
    bills = {b['id']: b for b in history['bills']}
    check(len(invoices) == len(history['invoices']) and len(bills) == len(history['bills']), 'unique_financial_records', context)
    enterprise_jobs = {j['id']: j for j in history['jobs'] if j['provider'] == 'enterprise'}
    check(all(j['week'] < 52 for j in history['jobs']), 'no_service_horizon_extension', context)
    check(result['enterpriseAttempts'] == len(enterprise_jobs) and result['enterpriseAccepted'] == sum(j['accepted'] for j in enterprise_jobs.values()) and result['enterpriseRejected'] == sum(not j['accepted'] for j in enterprise_jobs.values()), 'complete_outcomes', context)
    cash = config['initialCashCents']
    seen_events = set()
    event_by_week = collections.defaultdict(int)
    collection_by_week = collections.defaultdict(int)
    paid_by_week = collections.defaultdict(int)
    for event in history['cash']:
        check(event['reference'] not in seen_events, 'cash_reference_once', context)
        seen_events.add(event['reference'])
        if event['type'] == 'simulated_collection':
            invoice = invoices.get(event['reference'])
            check(invoice is not None and event['amountCents'] == invoice['amountCents'] and invoice['collectedWeek'] == event['week'] and invoice['dueWeek'] <= event['week'] and invoice['status'] == 'collected', 'collection_due_and_bound', context)
            collection_by_week[event['week']] += event['amountCents']
        else:
            bill = bills.get(event['reference'])
            check(event['type'] in ['expense_payment', 'refund'] and bill is not None and bill['paid'] and bill['paidWeek'] == event['week'] and bill['dueWeek'] <= event['week'] and event['amountCents'] == -bill['amountCents'], 'payment_due_and_bound', context)
            paid_by_week[event['week']] -= event['amountCents']
        cash += event['amountCents']
        event_by_week[event['week']] += event['amountCents']
        check(cash >= 0 and cash == event['cashAfterCents'], 'cash_reconciliation_no_new_capital', context)
    check(cash == result['finalCashCents'], 'terminal_cash', context)
    receivable_changes = collections.defaultdict(int)
    accrued_by_week = collections.defaultdict(int)
    for invoice in invoices.values():
        job = enterprise_jobs.get(invoice['mission'])
        check(job is not None and job['accepted'] and job['invoiceCreated'] and job['week'] == invoice['week'] and job['priceCents'] == invoice['amountCents'], 'invoice_accepted_job', context)
        check(invoice['dueWeek'] == invoice['week'] + config['paymentDelayWeeks'], 'invoice_delay', context)
        receivable_changes[invoice['week']] += invoice['amountCents']
        if invoice['status'] == 'collected':
            check(invoice['id'] in seen_events and invoice['pays'], 'collected_once', context)
            receivable_changes[invoice['collectedWeek']] -= invoice['amountCents']
        elif invoice['status'] == 'defaulted':
            check(invoice['id'] not in seen_events and not invoice['pays'], 'default_not_cash', context)
            receivable_changes[invoice['dueWeek']] -= invoice['amountCents']
        else:
            check(invoice['status'] == 'pending', 'known_invoice_status', context)
    for bill in bills.values():
        accrued_by_week[bill['week']] += bill['amountCents']
        check((bill['id'] in seen_events) == bill['paid'] and bill['amountCents'] >= 0, 'bill_paid_once', context)
        if bill['category'] == 'refund':
            invoice = invoices.get(bill['reference'])
            check(invoice is not None and invoice['refund'] and invoice['status'] == 'collected' and bill['amountCents'] == invoice['amountCents'] and bill['week'] == invoice['collectedWeek'] and bill['dueWeek'] == invoice['collectedWeek'] + config['refundDelayWeeks'], 'refund_bound', context)
    accrued = paid = collected = receivables = 0
    cash = config['initialCashCents']
    for balance in history['balances']:
        week = balance['week']
        accrued += accrued_by_week[week]
        paid += paid_by_week[week]
        collected += collection_by_week[week]
        receivables += receivable_changes[week]
        cash += event_by_week[week]
        obligations = accrued - paid
        expected = {'cashCents': cash, 'receivablesCents': receivables, 'obligationsCents': obligations,
                    'reserveCents': config['reserveCents'], 'availableCashCents': cash-obligations-config['reserveCents'],
                    'earnedAvailableCents': min(cash-obligations-config['reserveCents'], collected-accrued-config['reserveCents']),
                    'cumulativeCollectionsCents': collected, 'accruedCostsCents': accrued, 'paidCostsCents': paid}
        check(all(balance[k] == value for k, value in expected.items()), 'weekly_cash_cost_reserve_reconciliation', context)
    check(result['grossInvoicesCents'] == sum(i['amountCents'] for i in invoices.values()) and result['grossCollectionsCents'] == collected and result['paidCostsCents'] == paid and result['accruedCostsCents'] == accrued and result['obligationsCents'] == accrued-paid and result['profitCents'] == collected-accrued and result['refundsCents'] == sum(b['amountCents'] for b in bills.values() if b['category'] == 'refund'), 'summary_financial_reconciliation', context)
    first_history = [b for b in bills.values() if b['reference'] == 'upfront historical R&D cost stress; paid from seed if affordable, never labeled earned financing']
    check(len(first_history) == 1 and first_history[0]['amountCents'] == 36152 and first_history[0]['paidWeek'] == 0, 'opening_history_once', context)
    if arm == 'A':
        check('secondInvestment' not in run and not any(b['reference'].startswith('second:') for b in bills.values()), 'no_investment_A', context)
        return
    second = run['secondInvestment']
    profile = second['profile']
    check(profile['assetSHA256'] == effect['arms'][arm]['assetSHA256'] and profile['acceptanceEvidenceSHA256'] == effect['arms'][arm]['acceptanceEvidenceSHA256'], 'actual_second_asset_identity', context)
    check(profile['effects'] == effect['arms'][arm]['effects'], 'same_measured_effect', context)
    second_bills = [b for b in bills.values() if b['reference'].startswith('second:')]
    oneoff = sum(second['costsPaidByCategoryCents'].values())
    for category, amount in second['costsPaidByCategoryCents'].items():
        matches = [b for b in second_bills if b['reference'] == f"second:{profile['assetSHA256']}:{category}"]
        check(len(matches) == (1 if amount else 0) and sum(b['amountCents'] for b in matches) == amount, 'second_category_once', context+'/'+category)
    maintenance = sum(b['amountCents'] for b in second_bills if b['reference'].endswith(':maintenance'))
    check(sum(b['amountCents'] for b in second_bills) == oneoff + maintenance == second['completeRealizedSecondCostsCents'] and maintenance == second['maintenanceAccruedCents'], 'second_total_cost', context)
    if second['completeCostProfilePriced']:
        declared = sum(v['amountCents'] for k, v in profile['costs'].items() if k != 'weeklyMaintenance')
        check(declared == second['declaredCompletePrototypeOneoffCostCents'] == oneoff + second['outsideEnterprisePrototypeCostCents'] and second['completedResearchCostCountedExactlyOnce'], 'complete_prototype_once', context)
        check(second['projectProfitAfterCompletedPrototypeCostsCents'] == result['profitCents']-second['outsideEnterprisePrototypeCostCents'], 'project_profit_complete_cost', context)
    else:
        check(second['outsideEnterprisePrototypeCostCents'] is None and second['projectProfitAfterCompletedPrototypeCostsCents'] is None and second['declaredCompletePrototypeOneoffCostCents'] is None and oneoff == 0, 'unknown_cost_never_zero_filled', context)
    check(cash_and_funds(run) == second['terminalFunding'], 'terminal_generated_funds', context)
    for decision in second['decisions']:
        for stage in ['beforeSearch', 'afterSearch', 'afterConstruction']:
            if stage in decision:
                check(cash_and_funds(run, decision['week'], stage) == decision[stage], 'decision_generated_funds_no_future', context+'/'+stage)
        if decision['action'] in ['invest-second-capability', 'operating-funded-unqualified-research-attempt']:
            check(decision['beforeSearch']['availableCents'] >= decision['completeOneoffCostCents'] and decision['afterSearch']['availableCents'] >= decision['remainingConstructionCents'], 'second_funded_without_seed_or_future', context)
            check(decision['completeOneoffCostCents'] <= profile['researchEnvelopeCents'], 'second_resource_envelope', context)
    used_jobs = [j for j in enterprise_jobs.values() if j.get('secondAssetSHA256') == profile['assetSHA256']]
    check(len(used_jobs) == second['actualAssetInvocationsInModel'], 'second_invocation_count', context)
    check(all(second['availableWeek'] <= j['week'] < min(52, second['expiresWeek']) for j in used_jobs) and (not second['failedIntegration'] or not used_jobs), 'second_lifetime_and_failure', context)
    check(second['directAvoidedDeliveryCostCents'] == 0 and second['directCostRepayment'] is False, 'no_unearned_direct_benefit', context)
    check(second['financiallyAdmitted'] is False and second['invested'] is False, 'no_unqualified_admission', context)


def prefix(history, week):
    result = {}
    for key in ['cash', 'balances', 'invoices', 'bills', 'buyerChoices', 'jobs', 'investmentDecisions', 'investments', 'competitorActions', 'prices']:
        rows = []
        for original in history[key]:
            if original['week'] >= week:
                continue
            row = dict(original)
            if key == 'invoices':
                row.pop('status', None)
                row.pop('collectedWeek', None)
            if key == 'bills' and row.get('paidWeek', -1) >= week:
                row['paid'] = False
                row.pop('paidWeek')
            rows.append(row)
        result[key] = rows
    return result


raw_hash = hashlib.sha256()
raw_bytes = 0
seen = set()
representatives = {}
positive_cases = []
with gzip.open(OUT / 'complete-paired-worlds.jsonl.gz', 'rb') as source:
    for index, line in enumerate(source, 1):
        raw_hash.update(line)
        raw_bytes += len(line)
        world = json.loads(line)
        key = (world['groupId'], world['seed'])
        check(key not in seen and key in compact_by_key, 'full_archive_identity', str(key))
        seen.add(key)
        row = compact_by_key[key]
        paired = world['paired']
        check(world['sourceFreezeSHA256'] == completion['sourceFreezeSHA256'], 'world_freeze', str(key))
        check(row['causal'] == paired['causal'] and row['qualification'] == paired['qualification'], 'compact_full_causal', str(key))
        original_prefix = prefix(paired['arms']['A']['histories'], 26)
        for arm in ['A', 'B', 'C']:
            run = paired['arms'][arm]
            context = f'{world["groupId"]}/{world["seed"]}/{arm}'
            audit_arm(run, arm, context)
            check(run['config'] == paired['config'], 'same_market_conditions', context)
            check(prefix(run['histories'], 26) == original_prefix, 'same_enterprise_checkpoint', context)
            recorded = row['arms'][arm]
            result = run['summary']
            aliases = {'enterpriseProfitCents': 'profitCents', 'finalCashCents': 'finalCashCents', 'obligationsCents': 'obligationsCents', 'collectionsCents': 'grossCollectionsCents', 'accepted': 'enterpriseAccepted', 'attempts': 'enterpriseAttempts', 'rejected': 'enterpriseRejected', 'refundsCents': 'refundsCents', 'insolvent': 'insolvent'}
            check(all(recorded[k] == result[v] for k, v in aliases.items()), 'compact_full_financial', context)
            if arm != 'A':
                second = run['secondInvestment']
                check(recorded['projectInclusiveProfitCents'] == second['projectProfitAfterCompletedPrototypeCostsCents'] and recorded['outsideEnterprisePrototypeCostCents'] == second['outsideEnterprisePrototypeCostCents'] and recorded['secondCostsInEnterpriseCents'] == second['completeRealizedSecondCostsCents'], 'compact_full_second_cost', context)
                delta = None if second['projectProfitAfterCompletedPrototypeCostsCents'] is None else second['projectProfitAfterCompletedPrototypeCostsCents']-paired['arms']['A']['summary']['profitCents']
                check(paired['causal'][arm+'_minus_A_projectInclusiveProfitCents'] == delta and paired['qualification'][arm]['projectInclusiveIncrementCents'] == delta, 'paired_complete_cost_delta', context)
                gate = second['invested'] and second['completeCostProfilePriced'] and second['investmentPaidFromGeneratedResources'] and second['actualAssetInvocationsInModel'] > 0 and second['directCostRepayment'] and delta is not None and delta > 0
                check(paired['qualification'][arm]['conditionalModeledFinancialGatePassed'] == gate, 'qualification_requires_repayment', context)
        if world['conditionId'] == 'reference' and world['seed'] == 8001:
            representatives[key] = world
        if paired['causal']['B_minus_A_projectInclusiveProfitCents'] is not None and paired['causal']['B_minus_A_projectInclusiveProfitCents'] > 0:
            positive_cases.append({'groupId': world['groupId'], 'seed': world['seed'], 'projectDeltaCents': paired['causal']['B_minus_A_projectInclusiveProfitCents'], 'acceptedDelta': paired['causal']['B_minus_A_accepted'], 'directAvoidedCostCents': paired['arms']['B']['secondInvestment']['directAvoidedDeliveryCostCents'], 'qualified': paired['qualification']['B']['conditionalModeledFinancialGatePassed']})
        if index % 240 == 0:
            print(json.dumps({'archived_worlds_audited': index, 'failures': len(FAILURES), 'wall_seconds': time.perf_counter()-START}), flush=True)
check(len(seen) == 1920 and seen == set(compact_by_key), 'all_archived_worlds')
check(raw_hash.hexdigest() == completion['completePairedWorldsRawSHA256'], 'raw_archive_hash')
stored_representatives = read(OUT / 'predeclared-representatives.json')
check(stored_representatives['selection'] == protocol['representativeSelection'] and stored_representatives['selectedBeforeOutcomes'] is True and len(stored_representatives['worlds']) == 8, 'representative_rule')
for world in stored_representatives['worlds']:
    check(representatives.get((world['groupId'], world['seed'])) == world, 'representative_exact_archived_world')


CSV_FIELDS = {'A_profit_cents': ('A','enterpriseProfitCents'), 'B_profit_cents': ('B','enterpriseProfitCents'), 'C_profit_cents': ('C','enterpriseProfitCents'), 'B_project_profit_cents': ('B','projectInclusiveProfitCents'), 'C_project_profit_cents': ('C','projectInclusiveProfitCents'), 'B_complete_costs_priced': ('B','completeCostsPriced'), 'B_research_attempted': ('B','modeledConstructionAttempted'), 'C_research_attempted': ('C','modeledConstructionAttempted'), 'B_admitted': ('B','admitted'), 'C_admitted': ('C','admitted'), 'B_generated_funded': ('B','secondInvestmentPaidFromGeneratedResources'), 'C_generated_funded': ('C','secondInvestmentPaidFromGeneratedResources'), 'B_second_uses': ('B','secondInvocations'), 'C_second_uses': ('C','secondInvocations'), 'B_declared_complete_cost_cents': ('B','declaredCompletePrototypeCents'), 'B_outside_prototype_cost_cents': ('B','outsideEnterprisePrototypeCostCents'), 'C_outside_prototype_cost_cents': ('C','outsideEnterprisePrototypeCostCents'), 'B_second_costs_in_enterprise_cents': ('B','secondCostsInEnterpriseCents'), 'B_subcent_residual_microcents': ('B','subcentComputeNetResidualMicrocents'), 'C_subcent_residual_microcents': ('C','subcentComputeNetResidualMicrocents'), 'A_accepted': ('A','accepted'), 'B_accepted': ('B','accepted'), 'C_accepted': ('C','accepted'), 'A_insolvent': ('A','insolvent'), 'B_insolvent': ('B','insolvent'), 'C_insolvent': ('C','insolvent')}
def csv_equal(value, expected):
    if expected is None:
        return value == ''
    if isinstance(expected, bool):
        return value == str(expected).lower()
    if isinstance(expected, (int,float)):
        return value != '' and same(float(value), expected)
    return value == expected
with (OUT / 'outcomes.csv').open() as source:
    csv_rows = list(csv.DictReader(source))
check(len(csv_rows) == 1920, 'csv_count')
for row in csv_rows:
    entry = compact_by_key[(row['group_id'], int(row['seed']))]
    expected = {'group_id': entry['groupId'], 'condition': entry['conditionId'], 'cost_profile': entry['costProfileId'], 'policy': entry['policyId'], 'seed': entry['seed'], 'B_minus_A_project_cents': entry['causal']['B_minus_A_projectInclusiveProfitCents'], 'C_minus_A_project_cents': entry['causal']['C_minus_A_projectInclusiveProfitCents'], 'B_minus_C_project_cents': entry['causal']['B_minus_C_projectInclusiveProfitCents'], 'B_conditional_financial_gate': entry['qualification']['B']['conditionalModeledFinancialGatePassed'], 'C_conditional_financial_gate': entry['qualification']['C']['conditionalModeledFinancialGatePassed']}
    expected.update({column: entry['arms'][arm][field] for column,(arm,field) in CSV_FIELDS.items()})
    check(set(row) == set(expected) and all(csv_equal(row[k],v) for k,v in expected.items()), 'csv_exact_compact_row', str((entry['groupId'],entry['seed'])))

rep_brief = []
for (_, _), world in sorted(representatives.items()):
    run = world['paired']['arms']['B']; first = run['secondInvestment']['decisions'][0]
    second = run['secondInvestment']; a = world['paired']['arms']['A']
    rep_brief.append({'groupId':world['groupId'],'seed':8001,'initialCapitalCents':100000,
       'openingSeedPaidHistoryCents':36152,'firstAssetAdoptionCents':3269,
       'firstDecisionWeek':first['week'],'beforeDecision':first['beforeSearch'],
       'firstAction':first['action'],'reasons':first['reasons'],
       'completePrototypeCents':second['declaredCompletePrototypeOneoffCostCents'],
       'oneoffPaidInEnterpriseCents':sum(second['costsPaidByCategoryCents'].values()),
       'upkeepAccruedCents':second['maintenanceAccruedCents'],
       'outsidePrototypeCents':second['outsideEnterprisePrototypeCostCents'],
       'uses':second['actualAssetInvocationsInModel'],'funded':second['investmentPaidFromGeneratedResources'],
       'qualified':world['paired']['qualification']['B']['conditionalModeledFinancialGatePassed'],
       'terminalCollectionsCents':run['summary']['grossCollectionsCents'],
       'terminalAccruedCostsCents':run['summary']['accruedCostsCents'],
       'terminalCashCents':run['summary']['finalCashCents'],
       'enterpriseProfitCents':run['summary']['profitCents'],
       'projectInclusiveProfitCents':second['projectProfitAfterCompletedPrototypeCostsCents'],
       'AEnterpriseProfitCents':a['summary']['profitCents'],
       'projectIncrementCents':world['paired']['causal']['B_minus_A_projectInclusiveProfitCents'],
       'directAvoidedDeliveryCostCents':second['directAvoidedDeliveryCostCents'],
       'terminalGeneratedFunds':second['terminalFunding']})
signs = distribution([row['causal']['B_minus_A_projectInclusiveProfitCents'] for row in compact])
report = {'schema':'agi-alpha-second-investment-market-results-independent-review/v1',
 'reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer_role':'/root/coordination_audit',
 'status':'PASS_ARCHIVED_RESULTS_RECONCILED' if not FAILURES else 'FAIL',
 'simulation_runs_performed_by_auditor':0,'audit_source_sha256':digest(__file__),
 'source_freeze_sha256':digest(ROOT/'market/campaign-freeze.json'),
 'completion_sha256':digest(OUT/'completion.json'),'compressed_archive_sha256':digest(OUT/'complete-paired-worlds.jsonl.gz'),
 'raw_archive_sha256':raw_hash.hexdigest(),'raw_archive_bytes':raw_bytes,
 'frozen_files_checked':len(freeze['files']),'worlds':len(seen),'enterprise_histories':len(seen)*3,'groups':len(groups),
 'checks_by_category':dict(COUNTS),'failures':FAILURES,
 'financial_gate_passes':{arm:sum(row['qualification'][arm]['conditionalModeledFinancialGatePassed'] for row in compact) for arm in ['B','C']},
 'funded_research_attempts':{arm:sum(row['arms'][arm]['secondInvestmentPaidFromGeneratedResources'] for row in compact) for arm in ['B','C']},
 'priced_project_increment_signs':{key:signs[key] for key in ['n','missing','negative','zero','positive','min','max']},
 'B_C_integer_cent_project_ties':sum(row['causal']['B_minus_C_projectInclusiveProfitCents']==0 for row in compact),
 'positive_paired_paths':positive_cases,'preselected_seed8001_reconciliations':rep_brief,
 'interpretation_limits':['This is an independent source-and-arithmetic audit of saved simulated histories, not a new market experiment or external customer validation.',
 'Designed scenario counts and empirical simulation quantiles are not observed market probabilities or quality rates.',
 'Two priced paired project differences are positive because the modeled research intervention changes the realized market path; the second asset has zero evidenced delivery benefit and neither case passes the financial gate. Do not describe all priced worlds as losses.',
 'The service horizon remains52weeks. Later ledger rows settle already-issued invoices and obligations; they contain no new production jobs.',
 'Generated funds add back only the already seed-paid opening historical R&D for financing. Full-history and project-inclusive profit retain the historical cost; it is not charged twice as a new outflow.',
 'Outside-enterprise completed research contributions remain separately disclosed and enter project-inclusive profit once. Unknown complete costs remainnull.',
 'All timing and CPU figures in this audit describe archive checking only; no primary producer or market simulation was rerun.'],
 'audit_wall_seconds':time.perf_counter()-START,'audit_cpu_seconds':time.process_time()-CPU}
target=ROOT/'review/market-results-independent-review.json'
target.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'worlds':len(seen),'failures':FAILURES,
 'checks':sum(COUNTS.values()),'signs':report['priced_project_increment_signs'],
 'financial_gate_passes':report['financial_gate_passes'],'audit_wall_seconds':report['audit_wall_seconds'],
 'audit_cpu_seconds':report['audit_cpu_seconds']},indent=2),flush=True)
