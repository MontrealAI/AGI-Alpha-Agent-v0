import collections, datetime, gzip, hashlib, json, pathlib, time

origin = pathlib.Path('/workspace/scratch/da407bff0020/study')
out = pathlib.Path(__file__).resolve().parent
checks, counts = collections.Counter(), collections.Counter()
failures, identities = [], []
started = time.perf_counter()

def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()

def check(ok, kind, context):
    checks[kind] += 1
    if not ok:
        failures.append({'check':kind,'context':context})

def audit(campaign, rel):
    root = origin / rel
    source = root / 'complete-runs.jsonl.gz'
    before = sha(source)
    completion = json.loads((root / 'completion.json').read_text())
    check(before == completion['completeRunsSHA256'], 'recorded outcome identity', campaign)
    cfgs = {x['id']:x for x in json.loads((root/'configurations.json').read_text())}
    all_seeds = set()
    n = 0
    with gzip.open(source, 'rt') as stream:
        for line in stream:
            pair = json.loads(line)
            n += 1
            all_seeds.add(pair['seed'])
            check(pair['arms']['B']['summary'] == pair['arms']['C']['summary'], 'B C exact symmetric outcomes', (campaign,n))
            for arm, row in pair['arms'].items():
                ctx = (campaign, row['config']['id'], row['seed'], arm)
                s,h,c = row['summary'],row['histories'],row['config']
                check(c == cfgs[c['id']], 'frozen supplied configuration', ctx)
                counts[campaign + ':enterprises'] += 1
                counts[campaign + ':investments'] += len(h['investments'])
                counts[campaign + ':earned-investments'] += sum(x['funding']=='operating-surplus' for x in h['investments'])
                counts[campaign + ':profitable'] += s['profitCents'] > 0
                counts[campaign + ':attempts'] += s['enterpriseAttempts']
                own = [x for x in h['jobs'] if x['provider']=='enterprise']
                check(len(own) == s['enterpriseAttempts'], 'enterprise output count', ctx)
                check(sum(x['accepted'] for x in own) == s['enterpriseAccepted'], 'accepted output count', ctx)
                check(all(x['accepted'] or not x['invoiceCreated'] for x in h['jobs']), 'rejected output has no invoice',ctx)
                invoice_map = {x['id']:x for x in h['invoices']}
                bill_map = {x['id']:x for x in h['bills']}
                cash = c['initialCashCents']
                paid, collected = set(), set()
                for event in h['cash']:
                    cash += event['amountCents']
                    check(cash == event['cashAfterCents'] and cash >= 0, 'every cash balance conserved nonnegative',ctx)
                    ref = event['reference']
                    if event['amountCents']<0:
                        check(ref in bill_map and ref not in paid and -event['amountCents']==bill_map[ref]['amountCents'], 'one cash payment per bill',ctx)
                        paid.add(ref)
                    else:
                        check(ref in invoice_map and ref not in collected and event['amountCents']==invoice_map[ref]['amountCents'], 'one cash receipt per invoice',ctx)
                        collected.add(ref)
                unpaid = sum(x['amountCents'] for x in h['bills'] if not x['paid'])
                pending = sum(x['amountCents'] for x in h['invoices'] if x['status']=='pending')
                check(cash == s['finalCashCents'], 'terminal cash conservation',ctx)
                check(sum(x['amountCents'] for x in h['bills']) == s['accruedCostsCents'], 'all accrued bills charged once',ctx)
                check(unpaid == s['obligationsCents'], 'unpaid obligations retained',ctx)
                check(s['profitCents'] == cash + pending - unpaid - c['initialCashCents'], 'profit excludes initial capital',ctx)
                check(row['observedCustomerCollectionsCents']==0 and s['actualRevenueCents']==0, 'simulation not observed revenue',ctx)
                for b in h['balances']:
                    check(b['availableCashCents']==b['cashCents']-b['obligationsCents']-b['reserveCents'], 'liquidity net of reserves obligations',ctx)
                    check(b['earnedAvailableCents']==min(b['availableCashCents'],b['cumulativeCollectionsCents']-b['accruedCostsCents']-b['reserveCents']), 'earned funds exclude seed receivables',ctx)
                for j in own:
                    if j['assetUsed']:
                        check(j['sourceAssetSHA256'] == ('0b4eb1ae2392176ff61ef91b7da0d13df3c6400ee0b3e317439238881adc182d' if arm=='B' else 'cd28579ecf72eba5bdfffa6b3b5483aaaa960322989d2a2369da5431062207ba'), 'tested financed original asset identity',ctx)
                for inv in h['investments']:
                    check(inv['availableCashCents']>=inv['fullCostCents'] and inv['expectedNetBenefitCents']>0,'investment fits current funds and forecast',ctx)
                    check(all(not(inv['week']<=j['week']<inv['availableWeek']) for j in own),'no delivery during investment pause',ctx)
                check(all(x['committedCents']<=x['budgetCents'] for x in h['buyerProcurement']), 'finite buyer budgets',ctx)
                check(row['nextInvestment']['action']=='retain-reserves' and not row['nextInvestment']['actualFinancialAction'], 'no invented successor action',ctx)
    check(n == completion['pairedWorlds'], 'all declared worlds examined',campaign)
    check(len(all_seeds)==completion['seeds'],'all declared seeds examined',campaign)
    check(before == sha(source), 'original archive unchanged after read',campaign)
    identities.append({'campaign':campaign,'path':str(source),'bytes':source.stat().st_size,'sha256':before,'paired_worlds':n,'seeds':len(all_seeds)})

for campaign,path in [('primary','market/results/primary-01'),('exploratory','market/exploratory/results-01'),('policy-diagnostic','market/policy-diagnostic/results-01')]:
    audit(campaign,path)
report = {'schema':'agi-alpha-transfer-prior-audit/v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not failures else 'FAIL','independence':'Fresh arithmetic implementation by a separate same-session agent. Same host and institution; not independent institutional replication.','original_market_core_sha256':sha(origin/'market/src/market.mjs'),'source_identities':identities,'checks':dict(checks),'counts':dict(counts),'failures':failures[:100],'wall_seconds':time.perf_counter()-started,'limits':['Accounting checks are not independent jobs or field demand observations.','Prior empirical-grid and fixed-policy diagnostics are preserved separately.','No original source or result was modified.']}
dest=out/'prior-audit.json'
with dest.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:report[k] for k in ['status','counts','wall_seconds']}))
raise SystemExit(bool(failures))
