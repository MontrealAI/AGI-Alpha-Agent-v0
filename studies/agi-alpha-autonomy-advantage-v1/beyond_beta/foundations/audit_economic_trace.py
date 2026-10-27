# SPDX-License-Identifier: Apache-2.0
"""Independent read-only reconciliation of recorded BeyondBeta worlds.

No simulator import, policy selection, model call, payment, or world execution.
The audit validates recorded accounting and reservation consistency; it cannot
turn simulated task quality, demand or resource assumptions into measurements.
"""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import argparse
import base64
import gzip
import hashlib
import json
import math
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

TOKENS = ('astraInput', 'astraOutput', 'terraInput', 'terraOutput')
RESOURCE_KEYS = TOKENS + ('cpuHours', 'requests', 'modelHours', 'storageGbDays', 'tools')
CAPACITY_KEYS = ('modelHours', 'cpuHours', 'tokens', 'requests')


class AuditFailure(ValueError):
    pass


def micros(value):
    return int((Decimal(str(value))*1_000_000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def integer(value):
    return type(value) is int and value >= 0


def close(a, b, absolute=1e-7):
    return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=absolute)


def sum_resources(items):
    items = list(items)
    return {k: sum(item.get(k, 0) for item in items) for k in RESOURCE_KEYS}


def capacity(work):
    return {'modelHours': work.get('modelHours', 0), 'cpuHours': work.get('cpuHours', 0), 'tokens': sum(work.get(k, 0) for k in TOKENS), 'requests': work.get('requests', 0)}


def commitment(bill):
    record = {'id': bill['id'], 'ref': bill['ref'], 'amountMicros': bill['amountMicros'], 'ledger': bill['ledger']}
    raw = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    return hashlib.sha256(b'BEYOND-BETA-V1\0SIMULATED-LEDGER-COMMITMENT\0'+raw).hexdigest()


def digest(kind, value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    return hashlib.sha256(b'BEYOND-BETA-V1\0'+kind.encode()+b'\0'+raw).hexdigest()


def merkle_root(events):
    nodes = [digest('MERKLE-LEAF', e) for e in events]
    if not nodes: return digest('MERKLE-EMPTY', {})
    while len(nodes) > 1:
        if len(nodes)%2: nodes.append(nodes[-1])
        nodes = [digest('MERKLE-NODE', {'left':nodes[i], 'right':nodes[i+1]}) for i in range(0,len(nodes),2)]
    return nodes[0]


def audit_graph_uses(world, check):
    graph=world.get('graph', {}); log=graph.get('audit')
    uses=[]
    for job in world['jobs']:
        records=job.get('completionReuseReceipts', [])
        check('Every applied asset has a completion-time reuse receipt '+job['id'], sorted(j['key'] for j in records)==sorted(job.get('usedAssets', [])))
        uses.extend((r,job['worker']) for r in records)
    for asset in world.get('assets', []):
        uses.extend((r['helperReceipt'],asset['worker']) for r in asset.get('revalidationHistory', []) if r.get('helperReceipt'))
    if not log:
        check('Applied skills require a historical proof log', not uses)
        return 0
    events=log['events']; records={r['descriptor']['key']:r for r in graph['records']}; authorities={a['name']:a for a in graph['publicAuthorities']}
    previous=digest('GENESIS', {})
    for i,e in enumerate(events):
        unsigned={k:v for k,v in e.items() if k!='hash'}
        check('Typed graph event chain '+str(i), e['index']==i and e['previous']==previous and e['hash']==digest('EVENT',unsigned))
        previous=e['hash']
    check('Exact graph Merkle root', log['root']==merkle_root(events))
    check('Existing club roles preserved and identity fixture labeled', log['existingClubRoles']=='UNCHANGED' and log['liveIdentity'] is False)
    receipts={}
    for r in records.values():
        for receipt in [r.get('admission')]+[h.get('admission') for h in r.get('history', [])]:
            if receipt:receipts[digest('ADMISSION',receipt)]=receipt
    roots={}
    for use,worker in uses:
        count=use['eventIndex']+1;prefix=events[:count];p=use['permit']['payload'];key=use['key'];record=records[key]
        check('Reuse checkpoint names an existing historical prefix', 0<=count<=len(events) and all(e['epoch']<=use['epoch'] for e in prefix))
        if count not in roots:roots[count]=merkle_root(prefix)
        check('Reuse binds the exact prior graph prefix', use['logRoot']==roots[count])
        check('Reuse is assigned to the eligible executing worker', p['key']==key and p['actor']==f'worker-{worker}.agent.agi.eth')
        authority=authorities[p['actor']]
        check('Execution and plaintext retrieval remain separately authorized', authority['eligible'] and not authority['revoked'] and authority['validFromWeek']<=use['epoch']<authority['expiresWeek'] and {'execution','retrieve'}<=set(authority['roles']))
        check('Private availability is not bypassed', record['descriptor']['shareable'] or record['descriptor']['creator']==p['actor'])
        check('Permit is current at actual completion', p['issuedEpoch']<=use['epoch']<=p['expiry'])
        receipt=receipts.get(p['admissionHash']);check('Permit binds a preserved signed admission receipt',receipt is not None)
        payload=receipt['payload'];signer=authorities[payload['signer']]
        try:Ed25519PublicKey.from_public_bytes(bytes.fromhex(signer['publicKey'])).verify(base64.b64decode(receipt['signature'],validate=True),json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
        except Exception as exc:raise AuditFailure('Invalid admission signature in historical reuse') from exc
        admissions=[e for e in prefix if e['kind']=='CANONICAL_ADMISSION' and e['key']==key]
        check('Reuse uses latest admission for this exact artifact',bool(admissions) and admissions[-1]['binding']==p['admissionHash'])
        check('No revoked or retired history is revived',not any(e['key']==key and e['kind'] in ('REVOKED','RETIRED','SUPERSEDED') and e['index']>admissions[-1]['index'] for e in prefix))
        check('Admission proof remains within its fresh lifetime',payload['admittedEpoch']<=use['epoch']<=payload['validUntil'])
        check('Permit and admission bind the same Beta/policy',p['betaHash']==payload['betaHash'] and p['policyHash']==payload['policyHash'])
        beta_events=[e for e in prefix if e['kind']=='BETA_ADVANCED']
        if beta_events:check('Reuse compares against the current Beta version',payload['betaHash']==beta_events[-1]['binding'])
        function=record['descriptor']['function']
        current_epoch=sum(e['kind']=='CANONICAL_ADMISSION' and records[e['key']]['descriptor']['function']==function for e in prefix)
        check('New relevant admission cannot be bypassed',payload['comparisonEpoch']==p['comparisonEpoch']==current_epoch)
    return len(uses)


def audit_cash_checkpoint(decision, world, by_id, check):
    cp=decision.get('cashCheckpoint');check('Retained investment has a causal cash checkpoint',cp is not None)
    cash=world['cash'];n=cp['cashEventCount'];events=cash['events'][:n];t=cp['week']*7
    check('Cash checkpoint excludes future events',n==cp['cashEventIndex']+1 and n<=len(cash['events']) and cp['week']==decision['week'] and all(e['t']<=t for e in events))
    committed={e['billId'] for e in events if e['type']=='SIMULATED_COST_COMMITMENT'}
    collected_ids={e['invoiceId'] for e in events if e['type']=='SIMULATED_COLLECTION'}
    accrued=sum(by_id[x]['amountMicros'] for x in committed)
    collected=sum(e['amountMicros'] for e in events if e['type']=='SIMULATED_COLLECTION')
    paid=-sum(e['amountMicros'] for e in events if e['type']=='SIMULATED_EXPENSE_PAYMENT')
    remaining=cash['seedMicros']+collected-paid;unpaid=accrued-paid
    refund_invoices={by_id[x]['ref'] for x in committed if by_id[x]['category']=='refunds'}
    rounded=lambda amount,fraction:int((Decimal(amount)*Decimal(str(fraction))).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    warranty=sum(rounded(i['amountMicros'],cash['warrantyFraction']) for i in cash['invoices'] if i['id'] in collected_ids and i['warrantyUntil']>=t and i['id'] not in refund_invoices)
    tax=rounded(max(0,collected-accrued),cash['taxFraction']);reserve=cash['baseReserveMicros']+warranty+tax
    liquid=remaining-unpaid-reserve;earned=collected-accrued-reserve;operating=max(0,min(liquid,earned))
    f=cp['funds']
    check('Cash checkpoint independently replays past collections and obligations',all(f[k]==v for k,v in {'cashMicros':remaining,'collectedMicros':collected,'accruedMicros':accrued,'paidMicros':paid,'unpaidMicros':unpaid,'reserveMicros':reserve,'availableOperatingMicros':operating,'liquidAfterObligationsMicros':liquid}.items()))
    holds=cp['publicHoldsUSD'];check('Public holds are finite nonnegative commitments',all(math.isfinite(v) and v>=0 for v in holds.values()))
    known={j['id'] for j in world['jobs']}|{c['id'] for c in world.get('candidates', [])}|{a['key'] for a in world.get('assets', [])}
    check('Held costs name actual committed work',set(holds)<=known)
    for job in world['jobs']:
        if job['week']<cp['week']<job['completionWeek']:
            check('In-flight delivery funding is not spent again',job['id'] in holds and close(holds[job['id']],job['maximumCostUSD']))
    base=operating if decision['funding']=='operating-only' else max(0,liquid)
    available=base/1e6-sum(holds.values())
    check('Investment funds derive from past cash after existing holds',close(available,decision['fundsBefore'],1e-5))
    check('No future collections finance the reservation',decision['reservedUSD']<=available+1e-5)
    if decision.get('wholeInitialProgramFundingOrigin')=='OPERATING_GENERATED':
        check('Whole initial program includes assessment funding',decision['assessmentFundingOrigin']==decision['constructionFundingOrigin']=='OPERATING_GENERATED')


def audit_world(world, protocol):
    checks = []
    def check(name, condition):
        if not condition:
            raise AuditFailure(name)
        checks.append(name)

    s, cash = world['summary'], world['cash']
    bills, invoices, funds = cash['bills'], cash['invoices'], cash['funds']
    by_id = {b['id']: b for b in bills}
    check('Unique bill identifiers', len(by_id) == len(bills))
    check('Nonnegative exact money units', all(integer(b['amountMicros']) for b in bills))
    check('No invoice duplicates', len({i['jobId'] for i in invoices}) == len(invoices))
    check('Every paid bill has a settlement date', all(not b['paid'] or b.get('paidAt') is not None for b in bills))
    accrued = sum(b['amountMicros'] for b in bills)
    paid = sum(b['amountMicros'] for b in bills if b['paid'])
    collected = sum(i['amountMicros'] for i in invoices if i['status'] == 'collected')
    check('Accrued complete costs include every committed bill', accrued == funds['accruedMicros'])
    check('Paid costs reconcile to bills', paid == funds['paidMicros'])
    check('Collections reconcile to issued invoices', collected == funds['collectedMicros'])
    check('Finite cash conservation excludes seed from revenue', cash['seedMicros']+collected-paid == funds['cashMicros'] and funds['cashMicros'] >= 0)
    check('Unpaid commitments remain explicit', accrued-paid == funds['unpaidMicros'])
    check('Complete profit uses collected revenue and all accrued costs', abs(micros(s['completeProfitUSD'])-(collected-accrued)) <= 1)
    check('Complete-cost and revenue summaries reconcile', abs(micros(s['completeCostsUSD'])-accrued) <= 1 and abs(micros(s['collectionsUSD'])-collected) <= 1)
    check('Actual dollars are not inferred from modeled bills', s['actualRevenueUSD'] == 0 and s['actualCompleteCostUSD'] is None and world['actualModelCalls'] == 0)
    check('Settlement leaves no pending operational events or cost holds', not world['pendingEvents'] and not world['unspentPublicCostHolds'])
    check('Settlement leaves no pending invoices', all(i['status'] != 'pending' for i in invoices))
    check('Active warranty reserves have run off', all(i['status'] != 'collected' or i['warrantyUntil'] < cash['t'] or i.get('refundBillId') for i in invoices))
    check('Cash-invalid worlds are not marked solvent', s['cashValid'] == (not cash['insolvent']))
    if s['cashValid']:
        check('Solvent settled world has no unpaid due bills', all(b['paid'] or b['due'] > cash['t'] for b in bills))

    ledgers = defaultdict(int)
    categories = defaultdict(int)
    by_commitment = {}
    for b in bills:
        ledger = b.get('ledger', 'FINANCIAL')
        check('Recognized ledger '+b['id'], ledger in ('A', 'B', 'C', 'OPERATIONS', 'FINANCIAL'))
        ledgers[ledger] += b['amountMicros']; categories[b['category']] += b['amountMicros']
        if ledger != 'FINANCIAL':
            check('Immutable amount/account commitment '+b['id'], b['commitment'] == commitment(b))
            check('Unique source ledger commitment '+b['id'], b['commitment'] not in by_commitment)
            by_commitment[b['commitment']] = b
        else:
            check('Only disclosed financial adjustments lack A/B/C classification '+b['id'], b['category'] in ('paymentFees', 'refunds'))
    check('All accounts reconcile once to complete cost', dict(ledgers) == s['ledgerCostsMicros'] and sum(ledgers.values()) == accrued)
    check('Cost-category report reconciles exactly', dict(categories) == world['costCategoriesMicros'])
    program = sum(b['amountMicros'] for b in bills if b.get('ledger') in ('B', 'C') and b['ref'] != 'enterprise-opening')
    check('Retention/research program includes failed and declined attempts', abs(micros(s['retentionResearchProgramCostUSD'])-program) <= 1)

    jobs = world['jobs']; job_by_id = {j['id']: j for j in jobs}
    check('Unique commissions', len(job_by_id) == len(jobs))
    check('Accepted denominator contains useful accepted outcomes only', s['accepted'] == sum(j['usefulAccepted'] for j in jobs))
    check('Technical acceptances and false passes remain distinct', s['technicalAccepted'] == sum(j.get('technicalAccepted', False) for j in jobs) and s['falsePasses'] == sum(j.get('technicalAccepted', False) and not j['usefulAccepted'] for j in jobs))
    check('Rejected costs stay in the accepted denominator', (s['costPerAcceptedUSD'] is None if s['accepted'] == 0 else close(s['costPerAcceptedUSD'], accrued/1e6/s['accepted'])))

    resource_trace_complete = True
    for j in jobs:
        jid = j['id']; charges = [b for b in bills if b['ref'] == jid]
        a = [b for b in charges if b.get('ledger') == 'A']
        b = [b for b in charges if b.get('ledger') == 'B']
        check('Completed commission '+jid, j['finished'])
        check('Exactly one recorded complete delivery charge '+jid, len(a) == 1 and a[0]['id'] == j['billId'])
        check('A delivery cost and B extra-retention cost remain separate '+jid, abs(sum(x['amountMicros'] for x in a)-micros(j['costUSD'])) <= 1 and abs(sum(x['amountMicros'] for x in b)-micros(j.get('additionalRetentionUSD', 0))) <= max(1, len(b)))
        check('Every repeated delivery stage is charged '+jid, close(sum(x['costUSD'] for x in j['stages']), j['costUSD']))
        check('Actual commission spending respects its public maximum '+jid, sum(x['amountMicros'] for x in a+b) <= micros(j['maximumCostUSD'])+2)
        reserved = {k: sum(x[k] for x in j['reservation']['allocations']) for k in CAPACITY_KEYS}
        actual = capacity(sum_resources(x['resource'] for x in a+b if x.get('resource')))
        check('Consumed commission resources fit reserved capacity '+jid, all(actual[k] <= reserved[k]+1e-6 for k in CAPACITY_KEYS))
        if all('resources' in row and 'worker' in row and 'role' in row for row in j['stages']):
            check('Stage resources reconcile to charged delivery '+jid, all(close(v, a[0]['resource'][k]) for k,v in sum_resources(x['resources'] for x in j['stages']).items()))
            check('Independent checks use another worker '+jid, all(x['worker'] != j['worker'] and x['role'] == 'independent-verifier' for x in j['stages'] if x['stage'] == 'verify'))
            if j.get('technicalAccepted'):
                check('Accepted commission includes independent checking '+jid, any(x['stage'] == 'verify' for x in j['stages']))
            for worker in {r['worker'] for r in j['stages']}:
                consumed = sum_resources(r['resources'] for r in j['stages'] if r['worker'] == worker)
                if worker == j['worker']:
                    consumed = sum_resources([consumed]+[x['resource'] for x in b if x.get('resource')])
                used = capacity(consumed)
                held = {k:sum(x[k] for x in j['reservation']['allocations'] if x['worker'] == worker) for k in CAPACITY_KEYS}
                check('Actual worker resources fit that worker reservation '+jid+'/'+str(worker), all(used[k] <= held[k]+1e-6 for k in CAPACITY_KEYS))
        else:
            resource_trace_complete = False

    ownership_rows = 0
    for record in world.get('graph', {}).get('records', []):
        e = record.get('evidence')
        if not e: continue
        co = e['costOwnership']; seen = set(); fixed = 0
        for item in co['originJobCosts']:
            source = by_commitment.get(item['ledgerCommitment'])
            check('Origin A is a real original paid-job bill', source is not None and source['ledger'] == 'A' and source['ref'] == item['jobId'] and source['amountMicros'] == item['costMicros'])
            check('Origin A retains provenance-only ownership', item['ownership'] == 'DELIVERY_A_ALREADY_CHARGED')
            check('No duplicate origin/retention charge in an assessment', item['ledgerCommitment'] not in seen)
            seen.add(item['ledgerCommitment'])
        for field, ledger in [('retentionEntries', 'B'), ('researchEntries', 'C')]:
            for item in co[field]:
                source = by_id.get(item['chargeId']); amount = sum(item['costs'].values())
                check('Admission B/C binds the actual bill and immutable commitment', source is not None and source.get('ledger') == ledger and source['commitment'] == item['ledgerCommitment'] and source['amountMicros'] == amount)
                check('Admission does not use future unpaid construction evidence', source['t'] <= e['capturedEpoch']*7 and source['paid'])
                check('No duplicated incremental charge within an assessment', item['ledgerCommitment'] not in seen)
                seen.add(item['ledgerCommitment']); fixed += amount; ownership_rows += 1
        check('Alpha fixed denominator includes B+C exactly and excludes A', fixed == sum(e['arms']['candidate']['lifecycleCosts'].values()))

    allocations = [r for plan in world['resourceSchedules'] for r in plan['allocations']]
    overrides = next(x['overrides'] for x in protocol['scenarios'] if x['id'] == s['scenario'])
    by_worker_week = defaultdict(lambda: defaultdict(float)); by_week = defaultdict(lambda: defaultdict(float))
    for r in allocations:
        check('Reservation is within operating horizon and eligible worker set', 0 <= r['week'] < protocol['experiment']['weeks'] and 0 <= r['worker'] < protocol['network']['agentCount'])
        for k in CAPACITY_KEYS:
            check('Finite nonnegative capacity reservation', math.isfinite(r[k]) and r[k] >= 0)
            by_worker_week[(r['week'],r['worker'])][k] += r[k]; by_week[r['week']][k] += r[k]
    caps = protocol['capacity']
    for (week,worker), r in by_worker_week.items():
        check('Per-worker model/proof capacity '+str((week,worker)), r['modelHours'] <= caps['modelHoursPerAgentWeek']+1e-6 and r['cpuHours'] <= caps['proofContainerHoursPerAgentWeek']+1e-6)
    for week,r in by_week.items():
        multiplier = overrides.get('quotaMultiplier',1)
        check('Total token/request quotas '+str(week), r['tokens'] <= caps['tokensPerMinuteTotal']*10080*multiplier+1e-6 and r['requests'] <= caps['requestsPerMinuteTotal']*10080*multiplier+1e-6)
    actual = capacity(sum_resources(world['resourceConsumption']))
    check('Total charged resource consumption fits all reserved work', all(actual[k] <= sum(r[k] for r in allocations)+1e-5 for k in CAPACITY_KEYS))
    for decision in world['investmentDecisions']:
        if decision['decision'] == 'RETAIN':
            check('Investment respects recorded available finite funds', decision['reservedUSD'] <= decision['fundsBefore']+1e-7)
            audit_cash_checkpoint(decision,world,by_id,check)
    graph_uses=audit_graph_uses(world,check)
    check('Actual stage/worker resource traces are complete',resource_trace_complete)
    return {'identity': {k:s[k] for k in ('scenario','profile','seed','arm')}, 'checks': len(checks), 'status': 'PASS', 'boundIncrementalOwnershipRows': ownership_rows, 'actualStageWorkerTraceComplete': resource_trace_complete, 'historicalReuseReceiptsAudited':graph_uses, 'limitation': 'Reconciles recorded modeled costs and capacity. No real quality, demand, pricing, resource consumption, or commercial success is established.'}


def read_worlds(path):
    opener = gzip.open if path.suffix == '.gz' else open
    if '.jsonl' in path.name:
        with opener(path, 'rt', encoding='utf-8') as stream:
            for line in stream:
                if line.strip(): yield json.loads(line)
    else:
        with opener(path, 'rt', encoding='utf-8') as stream:
            yield json.load(stream)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('worlds', type=Path)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('Preserve the existing audit; use a new output path.')
    protocol = json.loads(args.protocol.read_text()); count=0; checks=0; stage_trace=0; reuse_receipts=0; failures=[]
    for world in read_worlds(args.worlds):
        count += 1
        try:
            r = audit_world(world, protocol); checks += r['checks']; stage_trace += r['actualStageWorkerTraceComplete']; reuse_receipts += r['historicalReuseReceiptsAudited']
        except (AuditFailure, KeyError, TypeError, ValueError) as exc:
            failures.append({'identity': {k:world.get('summary',{}).get(k) for k in ('scenario','profile','seed','arm')}, 'error': str(exc)})
    digest_file = lambda p: hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
    result = {'schema':'beyond-beta-independent-economic-trace-audit/v1','basis':'READ_ONLY_AUDIT_OF_RECORDED_SIMULATION_NOT_NEW_PRODUCTION','status':'FAIL' if failures else 'PASS','worlds':count,'checks':checks,'worldsWithCompleteStageWorkerTrace':stage_trace,'historicalReuseReceiptsAudited':reuse_receipts,'failures':failures,'inputSha256':digest_file(args.worlds),'protocolSha256':digest_file(args.protocol),'auditorSha256':digest_file(Path(__file__)),'economicWorldsExecuted':0}
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','worlds','checks','worldsWithCompleteStageWorkerTrace','economicWorldsExecuted')}))
    if failures: raise SystemExit(1)


if __name__ == '__main__': main()
