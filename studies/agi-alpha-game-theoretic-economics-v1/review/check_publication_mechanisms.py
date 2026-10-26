#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independently check final mechanism claims by reading existing histories only."""
import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'market/deployment-robustness/results-01'
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'review/final-publication-mechanism-check.json'
if OUT.exists():
    raise SystemExit('Use a fresh output path; original review receipts are immutable.')
started = time.perf_counter()
cpu_started = time.process_time()
archive = DATA / 'complete-runs.jsonl.gz'
reported = json.loads((DATA / 'mechanism-comparisons.json').read_text())
checks = 0
failures = []

def check(ok, label):
    global checks
    checks += 1
    if not ok:
        failures.append(label)

records = {}
groups = {}
prefixes = [('base', 'robust-main-'), ('undercut', 'robust-stress-undercut-'),
            ('delay6', 'robust-stress-collections-week6-'), ('delay13', 'robust-stress-collections-week13-')]
selected_ids = {f'{prefix}i{i}-a0.5-{choice}-adoption-only' for _, prefix in prefixes for i in (0, 500) for choice in ('deterministic', 'logit')}
for line in gzip.open(archive, 'rt'):
    if re.search(r'"id":"([^"]+)"', line[:240]).group(1) not in selected_ids:
        continue
    pair = json.loads(line)
    c = pair['config']
    variant = next((v for v, prefix in prefixes if c['id'].startswith(prefix)), None)
    if variant is None or c['investmentCostBasis'] != 'adoption-only' or c['integrationCents'] not in (0, 500) or c['arrivalProbability'] != .5:
        continue
    run = pair['arms']['B']
    key = (c['integrationCents'], c['choiceModel'], variant)
    g = groups.setdefault(key, {'quotes': [], 'profits': [], 'accepted': [], 'aiAccepted': [], 'inServiceFunding': [], 'insolvent': 0})
    g['quotes'] += [p['aiCents'] for p in run['histories']['prices']]
    g['profits'].append(run['summary']['profitCents'])
    g['accepted'].append(run['summary']['enterpriseAccepted'])
    g['aiAccepted'].append(sum(j['provider'] == 'ai' and j['accepted'] for j in run['histories']['jobs']))
    g['inServiceFunding'].append(pair['successionAvailability']['fundingByArm']['B']['maximumDuringServiceFundingCeilingBeforeUnpricedDiscoveryCents'])
    g['insolvent'] += sum(f['insolvent'] for f in run['competitorAccounts'].values())
    if variant in ('base', 'delay13'):
        records[(c['integrationCents'], c['choiceModel'], pair['seed'], variant)] = run

check(len(records) == 192, '192 existing reference/delay arm records')
for g in reported['groups']:
    for variant, values in g['variants'].items():
        actual = groups[(g['integrationCents'], g['choiceModel'], variant)]
        check(len(actual['profits']) == 24, '24 matched rows in every group')
        check([min(actual['quotes']), max(actual['quotes'])] == values['computedAIWeeklyQuoteRangeCents'], 'AI quote bounds')
        check(sum(q < 1600 for q in actual['quotes']) == values['computedAIQuotesBelow1600Count'], 'quote counts')
        check(len(actual['quotes']) == values['computedAIQuoteCount'], 'quote sample size')
        check(sum(actual['aiAccepted']) == values['acceptedAIJobCount'], 'AI accepted jobs')
        check(actual['insolvent'] == 0, 'no insolvent competitor in inspected groups')
        for field, target in [('profits', 'meanEnterpriseProfitBeforeUnknownDCents'), ('accepted', 'meanEnterpriseAccepted'), ('inServiceFunding', 'meanMaximumDuringServiceFundingCeilingBeforeUnknownDCents')]:
            check(math.isclose(sum(actual[field]) / 24, values[target], abs_tol=1e-8), target)

divergences = []
for integration in (0, 500):
    for choice in ('deterministic', 'logit'):
        for seed in range(3001, 3025):
            base = records[(integration, choice, seed, 'base')]
            delay = records[(integration, choice, seed, 'delay13')]
            bc = base['histories']['buyerChoices']
            dc = delay['histories']['buyerChoices']
            check([(x['week'], x['mission']) for x in bc] == [(x['week'], x['mission']) for x in dc], 'paired opportunity chronology')
            ix = next((i for i, (x, y) in enumerate(zip(bc, dc)) if x['choice'] != y['choice']), None)
            if ix is None:
                continue
            week, mission = bc[ix]['week'], bc[ix]['mission']
            prices = [next(p for p in run['histories']['prices'] if p['week'] == week) for run in (base, delay)]
            check(all(prices[0][k] == prices[1][k] for k in ('aiCents', 'enterpriseCents', 'humanMarkup')), 'same posted quotes and human markup at first divergence')
            c = base['config']
            # Reconstruct a fixed, previously used type key; this draws no new market world.
            buyer_index = int(bc[ix]['buyer'].split('-')[1])
            h = seed ^ 2166136261
            for byte in f'type-minutes|{buyer_index}'.encode('ascii'):
                h = ((h ^ byte) * 16777619) & 0xffffffff
            h = ((h ^ (h >> 16)) * 0x7feb352d) & 0xffffffff
            h = ((h ^ (h >> 15)) * 0x846ca68b) & 0xffffffff
            h ^= h >> 16
            minutes = c['humanMinutes'][int((h + .5) / 4294967296 * len(c['humanMinutes']))]
            required = math.floor(minutes * c['humanHourlyCents'] / 60 * c['failureCorrectionMultiplier'] + .5)
            prior_or_later_human_jobs = [j for j in base['histories']['jobs'] if j['provider'] == 'human' and j['buyer'] == bc[ix]['buyer']]
            for job in prior_or_later_human_jobs:
                markup = next(p['humanMarkup'] for p in base['histories']['prices'] if p['week'] == job['week'])
                check(abs(math.floor(minutes * c['humanHourlyCents'] / 60 * markup + .5) - job['priceCents']) < .1, 'reconstructed buyer type agrees with observed human quotes')
            cash = []
            for run, choices in ((base, bc), (delay, dc)):
                previous = {x['mission'] for x in choices[:ix] if x['week'] == week}
                firm = run['competitorAccounts']['human']
                bills = {b['id']: b for b in firm['bills']}
                cash_now = firm['openingCashCents']
                for event in firm['cashEvents']:
                    if event['week'] > week:
                        continue
                    bill = bills.get(event['reference'])
                    if event['week'] == week and bill and bill['category'] == 'delivery' and bill['reference'] not in previous:
                        continue
                    cash_now += event['amountCents']
                check(run['config']['expenseDelayWeeks'] == 0 and not firm['insolvent'], 'immediate paid-bill reconstruction applies')
                cash.append(cash_now)
            check(cash[0] >= required > cash[1], 'delay binds human cash gate and reference passes')
            expected = next(x for x in reported['allDelay13FirstChoiceDivergences'] if x['integrationCents'] == integration and x['choiceModel'] == choice and x['seed'] == seed)
            check(expected['week'] == week and expected['mission'] == mission, 'first divergence identity')
            check(all(expected[label]['cashStates']['human']['cashCents'] == value for label, value in zip(('base', 'delay13'), cash)), 'independent pre-choice human cash matches')
            check(expected['base']['cashStates']['human']['requiredCashForThisBuyerCents'] == required, 'independent human delivery requirement')
            divergences.append({'integrationCents': integration, 'choiceModel': choice, 'seed': seed, 'week': week, 'referenceCashCents': cash[0], 'delayedCashCents': cash[1], 'requiredCents': required})
check(len(divergences) == 21, '21 of 96 first-choice divergences')
report = {
    'schema': 'agi-alpha-independent-publication-mechanism-claims-check/v1',
    'executedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'passed': not failures, 'assertions': checks, 'failedAssertions': len(failures), 'firstFailures': failures,
    'newEconomicScenarios': 0,
    'method': 'Independent read-only arithmetic from the frozen archive. No market or mechanism-producer import or invocation. Human pre-choice cash uses original events and buyer ordering; required cash reconstructs the already-used semantic type key and checks consistency with recorded human quotes for that buyer.',
    'sourceArchiveSHA256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    'mechanismReportSHA256': hashlib.sha256((DATA / 'mechanism-comparisons.json').read_bytes()).hexdigest(),
    'reviewerSourceSHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'firstDivergences': divergences,
    'wallSeconds': time.perf_counter() - started, 'cpuSeconds': time.process_time() - cpu_started,
    'costBoundary': 'Local review resource observation; monetary authoring and inference cost remains unknown.',
    'priorDevelopmentFailures': [
        {'error': "KeyError: 'mission'", 'exitCode': 1, 'cause': 'The initial inline reviewer read a job identity as jobs.mission; the retained schema uses jobs.id. No market execution or output mutation occurred; the read-only attempt exited before a receipt was created.'},
        {'error': 'StopIteration', 'exitCode': 1, 'cause': 'The initial file-based checker assumed every first reference choice selected the human; two logit cases chose AI/enterprise, but losing the human option changed their choice. The paper claims only the human cash gate binds. No market execution or output mutation occurred; the read-only attempt exited before a receipt was created.'},
    ],
}
with OUT.open('x') as f:
    json.dump(report, f, indent=2)
    f.write('\n')
print(json.dumps({'path': str(OUT), 'passed': report['passed'], 'assertions': checks, 'failedAssertions': len(failures), 'wallSeconds': report['wallSeconds']}))
if failures:
    raise SystemExit(1)
