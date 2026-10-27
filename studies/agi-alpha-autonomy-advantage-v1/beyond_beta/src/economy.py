# SPDX-License-Identifier: Apache-2.0
"""Fresh BeyondBeta scenario engine. No model requests, customers or transactions.

All economic outcomes are conditional simulations. The graph and cryptographic
guards execute locally; task quality/effects are explicit stochastic assumptions.
Delivery A, incremental retention B and optional separate research C never share
an expense. Public maximum reservations precede latent trial outcomes.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import importlib.util
import math
from pathlib import Path
import statistics

from graph_lifecycle import BeyondBetaGraph, OfflinePrincipal, authority_fixture, costs, digest, Refusal
from fixture_factory import fixture_artifact, matched_evidence, mission_for

_spec = importlib.util.spec_from_file_location('bb_finance', Path(__file__).resolve().parents[2] / 'venture_creation/src/finance_capacity.py')
_finance = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_finance)
CashBook, micros = _finance.CashBook, _finance.usd_to_micros
TOKEN_KEYS = ('astraInput', 'astraOutput', 'terraInput', 'terraOutput')
RESOURCE_KEYS = TOKEN_KEYS + ('cpuHours', 'requests', 'modelHours', 'storageGbDays', 'tools')


def draw(seed, *parts):
    raw = hashlib.sha256(('|'.join(map(str, (seed,) + parts))).encode()).digest()
    return int.from_bytes(raw[:8], 'big') / 2**64


def mix(a, b, u): return a + (b-a)*u
def bounded(x): return max(0, min(1, x))
def vector(): return {k: 0.0 for k in RESOURCE_KEYS}


def add(*items):
    return {k: sum(x.get(k, 0) for x in items) for k in RESOURCE_KEYS}


def scale(item, factor):
    return {k: (math.ceil(item[k]*factor) if k in TOKEN_KEYS or k == 'requests' else item[k]*factor) for k in RESOURCE_KEYS}


def resource_cost(item, rates, multiplier=1):
    return multiplier*(sum(item[k]*rates[k]/1e6 for k in TOKEN_KEYS) + item['cpuHours']*rates['cpuHour'] + item['storageGbDays']*rates['storageGbDay'] + item['tools']*rates['tools'])


class Calendar:
    """Six equal weekly budgets; verifier consumes another worker's same budget.

    Maximum retries remain reserved until completion. This conservative scheduler
    reports reservation separately from consumption; unused space is not sold twice.
    """
    def __init__(self, p, override):
        c = p['capacity']; self.agents = p['network']['agentCount']; self.slots = {}
        self.model = c['modelHoursPerAgentWeek']; self.cpu = c['proofContainerHoursPerAgentWeek']
        self.tokens = c['tokensPerMinuteTotal']*10080*override.get('quotaMultiplier', 1)
        self.requests = c['requestsPerMinuteTotal']*10080*override.get('quotaMultiplier', 1)
        self.records = []; self.horizon = p['experiment']['weeks']

    def preview(self, week, worker, producer, verifier=None):
        slots = {w:{'workers':{a:dict(v) for a,v in s['workers'].items()},'tokens':s['tokens'],'requests':s['requests']} for w,s in self.slots.items()}; rows = []; end = week
        for agent, work in ((worker, producer), ((worker+1) % self.agents, verifier or vector())):
            remaining = dict(modelHours=work['modelHours'], cpuHours=work['cpuHours'], tokens=sum(work[k] for k in TOKEN_KEYS), requests=work['requests'])
            cursor = end
            while max(remaining.values()) > 1e-8:
                if cursor >= self.horizon: return None
                slot = slots.setdefault(cursor, {'workers': {}, 'tokens': 0.0, 'requests': 0.0})
                used = slot['workers'].setdefault(agent, {'modelHours': 0.0, 'cpuHours': 0.0})
                free = dict(modelHours=self.model-used['modelHours'], cpuHours=self.cpu-used['cpuHours'], tokens=self.tokens-slot['tokens'], requests=self.requests-slot['requests'])
                fraction = min([1.0] + [max(0, free[k])/v for k, v in remaining.items() if v > 1e-8])
                if fraction > 1e-12:
                    allocation = {k: v*fraction for k, v in remaining.items()}
                    used['modelHours'] += allocation['modelHours']; used['cpuHours'] += allocation['cpuHours']
                    slot['tokens'] += allocation['tokens']; slot['requests'] += allocation['requests']
                    rows.append(dict(week=cursor, worker=agent, **allocation))
                    remaining = {k: max(0, v-allocation[k]) for k, v in remaining.items()}
                cursor += 1
            end = cursor
        return {'startWeek': week, 'completionWeek': end, 'allocations': rows, '_slots': slots}

    def commit(self, preview, ref):
        self.slots = preview.pop('_slots'); row = {**preview, 'ref': ref}; self.records.append(row)
        return deepcopy(row)


def policy_grid(p):
    result = []
    for price in p['policies']['priceGridUsd'] + [None]:
        for investment in p['policies']['investmentRules']:
            for funding in p['policies']['fundingRules']:
                result.append(dict(id=f'policy-{len(result):02d}', priceUSD=price, pricing='adaptive' if price is None else 'fixed', investment=investment, funding=funding))
    return result


class World:
    def __init__(self, p, policy, scenario, profile, seed, arm):
        self.p, self.policy, self.seed, self.arm = p, deepcopy(policy), seed, arm
        self.scenario = scenario; self.o = deepcopy(next(x['overrides'] for x in p['scenarios'] if x['id'] == scenario))
        self.profile_id = profile; self.profile = p['profiles'][profile]; self.d = p['engineDefaults']; self.design = p['engineDesign']
        self.week = 0; self.horizon = p['experiment']['weeks']; self.beta_index = 0; self.calendar = Calendar(p, self.o)
        c = p['company']; self.cash = CashBook(c['seedUsd'], c['reserveUsd'], c['taxReserveFraction'], c['warrantyReserveFraction'])
        self.jobs, self.offers, self.candidates, self.assets, self.events, self.decisions = [], [], [], {}, [], []
        self.pending, self.holds, self.integrated, self.probes = [], {}, {}, {}; self.closed = False;self.closure_reason=None;self.closure_week=None
        self.program_spend = {}; self.feedback = []; self.seen_candidates = set(); self.resource_consumption = []
        self.versions = deepcopy(p['betaVersions'])
        if 'versionWeeks' in self.o:
            for row, when in zip(self.versions, self.o['versionWeeks']): row['startWeek'] = when
        self.frozen = arm in ('network-alpha-frozen-beta', 'frozen-beta-only')
        self.can_retain = arm not in ('moving-beta-only', 'frozen-beta-only', 'trained-beta') and policy['investment'] != 'never'
        self.people, self.graph = self.make_graph()
        b = p['buyers']; self.buyers = []
        for i in range(b['buyers']):
            self.buyers.append(dict(id=i, budget=mix(b['annualBudgetUsdLow'], b['annualBudgetUsdHigh'], self.u('budget', i)), spent={}, trust=self.profile['buyerTrust'], used=False,
                threshold=mix(*b['qualityThresholdInterval'], self.u('quality', i)), switching=mix(*b['switchingCostUsdInterval'], self.u('switch', i))))

    def u(self, *parts): return draw(self.seed, self.scenario, *parts)
    def beta(self): return self.versions[self.beta_index]
    def family_stage(self, family): return self.p['skills'][family]['affectedStages'][0]

    def beta_descriptor(self):
        return dict(id=self.beta()['id'], version=self.beta_index+1, competent=True, competenceEvidenceHash=digest('SCENARIO-COMPETENT-BETA', {'version': self.beta_index+1, 'assumed': True}))

    def make_graph(self):
        roles = {f'worker-{i}': ['creator', 'compose', 'execution', 'retrieve'] for i in range(self.p['network']['agentCount'])}
        roles.update(writer=['writer'], assessor=['assessor'], validator_a=['validator'], validator_b=['validator'], admitter=['admission'])
        people = {k: OfflinePrincipal(k.replace('_', '-')+'.agent.agi.eth') for k in roles}
        policy = dict(id='BEYOND-BETA-MODELED-RETENTION', version=1, functions=list(self.p['skills']), contractHash=digest('WHOLE-MISSION-CONTRACT', {'scope': 'faithful-bounded-component-v1'}),
            minCases=self.p['network']['independentCases'], minValidators=2, minAcceptanceBps=self.d['graphAdmissionAcceptanceBps'], maxEvidenceAge=self.d['maxGraphEvidenceAgeWeeks'], permitLife=40,
            maxAllocationUses=self.d['maxCostAllocationUses'], minCompositionCases=self.p['network']['independentCases'], uncertaintyMultiplierMilli=int(1000*self.d['netAlphaUncertaintyMultiplier']), minimumNetAlphaMicros=0,
            operators={'IDENTITY': 1, 'ADD': 2, 'RETURN': 1}, inputArity=2, publicParameters={'public-zero': 0, 'public-one': 1}, publicSourceIds=['public-fixture-v1'], privateAblation=self.arm == 'private-alpha-availability-ablation')
        return people, BeyondBetaGraph(policy, self.beta_descriptor(), [], [authority_fixture(people[k], v) for k, v in roles.items()])

    def bundle(self, name, multiplier=1, effect=0):
        raw = self.p['bundles'][name]; beta = self.beta(); out = scale(raw, multiplier*self.profile['resourceMultiplier']*(1-effect))
        for k in TOKEN_KEYS: out[k] = math.ceil(out[k]*beta['modelResourceMultiplier'])
        out['cpuHours'] *= beta['proofResourceMultiplier']; out['modelHours'] *= beta['latencyMultiplier']
        return out

    def cost(self, bundle): return resource_cost(bundle, self.p['rates'], self.o.get('resourcePriceMultiplier', 1))
    def free(self, operating=False):
        f = self.cash.funds(); return (f['availableOperating'] if operating else max(0, f['liquidAfterObligations'])) - sum(self.holds.values())

    def charge(self, amount, category, ref, ledger, resource=None):
        available_operating=self.free(True)
        bill = self.cash.expense(self.week*7, amount, category, ref)
        bill.update(ledger=ledger,resource=deepcopy(resource),operatingFundsAtCommitUSD=available_operating,fundingAtCommit='OPERATING_GENERATED' if amount<=available_operating else 'SEED_OR_MIXED',commitment=digest('SIMULATED-LEDGER-COMMITMENT',{'id':bill['id'],'ref':ref,'amountMicros':bill['amountMicros'],'ledger':ledger}))
        if resource: self.resource_consumption.append(dict(week=self.week, ref=ref, ledger=ledger, **resource))
        self.cash.advance(self.week*7); return bill

    def spend_bundle(self, name, ref, ledger='B', multiplier=1):
        work = self.bundle(name, multiplier); return self.charge(self.cost(work), name, ref, ledger, work)

    def worker(self, index): return self.people[f'worker-{index}']
    def origin(self, job):
        return [dict(jobId=job['id'], ledgerCommitment=b['commitment'], costMicros=b['amountMicros'], ownership='DELIVERY_A_ALREADY_CHARGED') for b in self.cash.bills if b['ref'] == job['id'] and b['ledger'] == 'A']

    def equivalent(self, worker, family, scope):
        initial = self.o.get('initialEquivalentProbability', self.p['network']['agents'][worker]['initialEquivalentProbability'])
        probability = max(initial, self.beta()['equivalentByFamily'][family])
        if self.week >= self.o.get('atWeek', self.horizon+1): probability = max(probability, self.o.get('baselineEquivalent', {}).get(family, 0))
        return self.u('functional-equivalence', worker, family, scope) < probability

    def quoted_precision(self):
        weight = self.d['priorWeight']; observed = [x for x in self.feedback if x['technicalAccepted']]
        return (weight*self.d['initialPrecision'] + sum(x['publicUseful'] for x in observed))/(weight+len(observed))

    def public_completed(self):
        ids = {x['jobId'] for x in self.feedback if x['technicalAccepted'] and x['publicUseful']}
        return [j for j in self.jobs if j['id'] in ids]

    def job_maximum(self, factor,worker):
        names = self.p['resourceRules']['deliveryStages']; producer = add(*(self.bundle(n, factor) for n in names if n != 'verify'))
        producer = add(producer, scale(add(self.bundle('repair', factor), self.bundle('prove', factor)), self.p['resourceRules']['maxRepairs']))
        verifier = scale(self.bundle('verify', factor), 1+self.p['resourceRules']['maxRepairs'])
        # Known configuration controls the bound, never a future success/effect draw.
        available=self.graph.discover(self.worker(worker),self.week) if self.can_retain and self.assets else []
        possible=[x for x in available if self.assets[x['key']]['family']!='revalidation' and not self.assets[x['key']].get('maintenancePending') and not self.assets[x['key']].get('revalidationPending') and self.assets[x['key']]['expiresWeek']>self.week]
        if possible:producer=add(scale(producer,1.2),scale(add(self.bundle('discovery'),self.bundle('gapProbe'),self.bundle('adapt')),len(possible)))
        return producer, verifier

    def choose_price(self, maximum_cost):
        if self.policy['priceUSD'] is not None: return self.policy['priceUSD']
        available = self.p['policies']['priceGridUsd']; best = available[0]; score = -math.inf
        for price in available:
            observed = [x for x in self.offers if x['priceUSD'] == price]
            if not observed: return price
            conversion = (1+sum(x['choice']=='network' for x in observed))/(2+len(observed))
            candidate = conversion*(self.quoted_precision()*price-maximum_cost)
            if candidate > score: best, score = price, candidate
        return best

    def utilities(self, buyer, value, human_price, delay, price):
        b = self.p['buyers']; decay = self.d['valueDecayWeekly']; hours = b['customerIntakeHours'][{'efficient': 0, 'reference': 1, 'burdensome': 2}[self.profile_id]]
        effort = hours*b['customerEffortHourlyUsd']; switching = 0 if buyer['used'] else buyer['switching']; q = self.quoted_precision()
        human = self.d['humanQuality']*(value*math.exp(-decay*self.d['humanDeliveryDays']/7)-human_price)-effort
        network = buyer['trust']*self.d['initialDelivery']*q*(value*math.exp(-decay*delay/7)-price)-effort-switching
        if q < buyer['threshold']: network = -math.inf
        remaining = buyer['budget']-buyer['spent'].get(self.week//52, 0)
        if price > remaining: network = -math.inf
        if human_price > remaining: human = -math.inf
        postpone = max(0, self.design['postponeValueFraction']*self.d['humanQuality']*(value*math.exp(-decay*self.design['postponeWeeks'])-human_price)-effort-self.design['postponeCostUsd'])
        return {'decline': 0, 'postpone': postpone, 'human': human, 'network': network}

    def opportunity(self, buyer):
        bid = buyer['id']; ref = f'job-{self.week}-{bid}'; worker = bid % self.p['network']['agentCount']; u = self.u('job-type', self.week, bid)
        shares = deepcopy(self.p['jobTypes'])
        if 'composedShare' in self.o:
            shares['interfaceComposition']['share'] = self.o['composedShare']; shares['boundedModule']['share'] = 1-self.o['composedShare']-shares['statefulComponent']['share']
        cumulative = 0
        for kind, spec in shares.items():
            cumulative += spec['share']
            if u <= cumulative: break
        factor = spec['resourceMultiplier']; maximum, verify = self.job_maximum(factor,worker); max_cost = self.cost(add(maximum, verify))
        schedule = self.calendar.preview(self.week, worker, maximum, verify); delay = 7*((schedule['completionWeek']-self.week) if schedule else self.horizon)
        value = math.exp(mix(math.log(self.p['buyers']['valueUsdLow']), math.log(self.p['buyers']['valueUsdHigh']), self.u('project-value', self.week, bid)))
        nominal_cpu = sum(self.p['bundles'][n]['cpuHours'] for n in self.p['resourceRules']['deliveryStages'])*factor
        human = (self.p['humanReference']['hoursByProfile'][self.profile_id]*factor*self.p['humanReference']['loadedHourlyProxy']+nominal_cpu*self.p['rates']['cpuHour'])*(1+self.p['humanReference']['businessLoadingFraction'])
        price = self.choose_price(max_cost); utilities = self.utilities(buyer, value, human, delay, price)
        deadline = mix(*self.p['buyers']['deadlineDaysInterval'], self.u('deadline', self.week, bid))
        if self.closed or not schedule or delay > deadline or max_cost > self.free(): utilities['network'] = -math.inf
        if self.d['humanDeliveryDays'] > deadline: utilities['human'] = -math.inf
        choice = max(utilities, key=utilities.get)  # Decline wins every zero-utility tie.
        offer = dict(id=ref, week=self.week, buyer=bid, worker=worker, jobType=kind, priceUSD=price, humanReferenceUSD=human, valueUSD=value, deadlineDays=deadline, publicMaximumCostUSD=max_cost, quotedDays=delay,
            utilities={k: (v if math.isfinite(v) else None) for k, v in utilities.items()}, choice=choice, cashAvailableBefore=self.free(), quality=self.quoted_precision(), trust=buyer['trust'])
        self.offers.append(offer)
        if choice == 'human':
            if self.u('human-accepted', ref) < self.d['humanQuality']: buyer['spent'][self.week//52] = buyer['spent'].get(self.week//52, 0)+human
            return
        if choice != 'network': return
        operating_before = self.free(True)
        reservation = self.calendar.commit(schedule, ref); self.holds[ref] = max_cost
        buyer['spent'][self.week//52] = buyer['spent'].get(self.week//52, 0)+price
        job = dict(id=ref, week=self.week, completionWeek=reservation['completionWeek'], worker=worker, buyer=bid, factor=factor, jobType=kind, priceUSD=price, valueUSD=value, betaAtDispatch=self.beta_index,
            reservation=reservation, maximumCostUSD=max_cost, operatingFundsBeforeReservationUSD=operating_before, assets=[], preparation=[], probeResults=[], originCandidateIds=[], finished=False, usefulAccepted=False)
        self.prepare_assets(job); self.jobs.append(job); self.pending.append(('job', job))

    def prepare_assets(self, job):
        if not self.can_retain or not self.assets: return
        agent = self.worker(job['worker']); discovered = self.graph.discover(agent, self.week)
        preparation_limit=max(0,job['operatingFundsBeforeReservationUSD']-(job['maximumCostUSD'] if job['jobType']!='revalidation' else 0)) if self.policy['funding']=='operating-only' else job['maximumCostUSD']
        for item in discovered:
            asset = self.assets.get(item['key'])
            if not asset or asset['expiresWeek'] <= job['completionWeek'] or asset.get('maintenancePending') or asset.get('revalidationPending'): continue
            family = asset['family']; cache = (job['worker'], item['key'], self.beta_index, job['jobType'])
            if (family == 'revalidation') != (job['jobType']=='revalidation'): continue
            worst_preparation = self.cost(add(self.bundle('discovery'),self.bundle('gapProbe'),self.bundle('adapt')))
            if preparation_limit < worst_preparation: continue
            preparation_limit -= worst_preparation
            job['preparation'].append('discovery')
            if cache not in self.probes:
                job['preparation'].append('gapProbe');gap=not self.equivalent(job['worker'],family,job['jobType']);job['probeResults'].append(dict(cache=list(cache),gap=gap))
            else:gap=self.probes[cache]
            if not gap:
                self.events.append(dict(week=self.week, type='EQUIVALENT_BASELINE_NO_ALPHA', key=item['key'], worker=job['worker'])); continue
            if asset['observedEffect'] <= 0: continue
            if cache not in self.integrated:
                prior_jobs = [j for j in self.public_completed() if j['worker'] == job['worker']]
                reuse = len(prior_jobs)/max(1,self.week)*max(0,min(asset['expiresWeek'],self.horizon)-self.week)
                future_saving = self.cost(self.bundle(self.family_stage(family),job['factor']))*asset['observedEffect']*reuse
                if future_saving <= self.cost(self.bundle('adapt')): continue
                if self.u('optional-adopt', job['worker'], item['key']) >= self.p['network']['adoptionProbabilityIfGapAndPositiveValue']: continue
                job['preparation'].append('adapt')
                success = self.u('adapt', job['worker'], item['key'], self.beta_index) < self.o.get('adaptationSuccessProbability', self.p['network']['adaptationSuccessProbability'])
            else: success = self.integrated[cache]
            permit = self.graph.authorize_reuse(agent, item['key'], mission_for(self.graph, family), self.week)
            self.graph.resolve_reuse(agent, permit, self.week)
            job['assets'].append(dict(key=item['key'], permit=permit, cache=list(cache), adaptationSuccess=success))

    def finish_job(self, job):
        ref = job['id']; effects = {}; used = []; invalid_asset = False
        job['completionReuseReceipts']=[]
        for row in job['probeResults']:self.probes[tuple(row['cache'])]=row['gap']
        for entry in job['assets']:
            self.integrated[tuple(entry['cache'])] = entry['adaptationSuccess']
            try:
                a=self.assets[entry['key']]
                if a.get('maintenancePending') or a.get('revalidationPending') or self.week>=a['expiresWeek']:raise Refusal('ASSET_NOT_OPERATIONALLY_CURRENT')
                self.graph.resolve_reuse(self.worker(job['worker']), entry['permit'], self.week)
            except Refusal as exc:
                self.events.append(dict(week=self.week, type='COMPLETION_REUSE_REFUSED_BETA_RECONSTRUCTION', jobId=ref, reason=str(exc))); continue
            if entry['adaptationSuccess']:
                asset = self.assets[entry['key']]; effects[self.family_stage(asset['family'])] = asset['trueEffect']; used.append(entry['key']); invalid_asset |= not asset['trueValid']
                audit=self.graph.audit_log();job['completionReuseReceipts'].append(dict(key=entry['key'],permit=entry['permit'],epoch=self.week,eventIndex=len(audit['events'])-1,logRoot=audit['root']))
        common = self.u('specification-common-error', ref) < self.profile['commonErrorProbability']*self.o.get('commonErrorMultiplier', 1)
        valid = self.u('first-valid', ref) < bounded(self.profile['firstAttemptValidProbability']+self.beta()['candidateValidityAdd'])
        valid = valid and not common and not invalid_asset
        unsupported = self.u('unsupported', ref) < self.d['unsupportedProbability']
        clarification = self.u('clarification', ref) < self.d['clarificationProbability']
        if clarification and self.u('clarification-success', ref) >= self.d['clarificationSuccess']: unsupported = True
        rows = []; consumed = vector(); accepted = False
        stages = ['intake','specify'] if unsupported else self.p['resourceRules']['deliveryStages']
        for n in stages:
            work = self.bundle(n, job['factor'], effects.get(n, 0)); consumed = add(consumed, work); rows.append(dict(stage=n,costUSD=self.cost(work),resources=work,worker=(job['worker']+1)%self.p['network']['agentCount'] if n=='verify' else job['worker'],role='independent-verifier' if n=='verify' else 'producer'))
        preparation = add(*(self.bundle(n) for n in job['preparation']))
        for attempt in range(0 if unsupported else self.p['resourceRules']['maxRepairs']+1):
            if attempt:
                if not common and not invalid_asset and self.u('repair-valid', ref, attempt) < self.profile['repairProbability']: valid = True
                for n in self.p['resourceRules']['repairStages']:
                    work = self.bundle(n, job['factor'], effects.get(n, 0)); consumed = add(consumed, work); rows.append(dict(stage=n,costUSD=self.cost(work),resources=work,worker=(job['worker']+1)%self.p['network']['agentCount'] if n=='verify' else job['worker'],role='independent-verifier' if n=='verify' else 'producer'))
            accepted = (self.u('verify', ref, attempt) < self.profile['validatorSpecificity']) if valid else ((common and self.u('common-reference-blind', ref) < self.d['commonReferenceBlind']) or self.u('verify', ref, attempt) > self.profile['validatorSensitivity'])
            if accepted: break
        amount = self.cost(consumed); prep_amount = self.cost(preparation); self.holds.pop(ref)
        if amount+prep_amount > job['maximumCostUSD']+1e-5: raise AssertionError('Actual delivery exceeded public maximum reservation')
        bill = self.charge(amount, 'completeDelivery', ref, 'A', consumed)
        if prep_amount: self.charge(prep_amount, 'retentionDiscoveryAndIntegration', ref, 'B', preparation)
        job.update(finished=True,technicalAccepted=accepted,trueValid=valid and not unsupported,usefulAccepted=accepted and valid and not unsupported,costUSD=amount,additionalRetentionUSD=prep_amount,stages=rows,preparationResources=preparation,actualBetaAtCompletion=self.beta_index,usedAssets=used,billId=bill['id'],repairs=attempt if not unsupported else 0)
        buyer = self.buyers[job['buyer']]
        if accepted:
            self.cash.invoice(self.week*7, ref, job['priceUSD'], (self.week+self.o.get('collectionDelayWeeks', self.p['buyers']['collectionDelayWeeks']))*7, self.u('collection', ref) < self.p['buyers']['collectionProbability'], self.p['buyers']['paymentFeeFraction'], (self.week+self.p['buyers']['supportWindowWeeks'])*7)
            buyer['used'] = True
            detect = not job['usefulAccepted'] and self.u('post-defect', ref) < self.p['buyers']['postDeliveryDefectDetection']
            self.pending.append(('feedback', dict(completionWeek=self.week+1, job=job, detected=detect)))
        else:
            buyer['spent'][job['week']//52] -= job['priceUSD']; self.feedback.append(dict(jobId=ref, technicalAccepted=False, publicUseful=False, week=self.week))
        for key in used:
            asset = self.assets[key]; saving = sum(self.cost(self.bundle(row['stage'], job['factor']))-row['costUSD'] for row in rows if row['stage'] in self.p['skills'][asset['family']]['affectedStages'])
            asset['realizedGrossSavingsUSD'] += saving; asset['useCount'] += 1
        if job['assets']:
            for entry in job['assets']: self.assets[entry['key']]['programCostUSD'] += prep_amount/len(job['assets'])
        elif prep_amount: self.events.append(dict(week=self.week,type='UNASSIGNED_RETENTION_PREPARATION_COST',jobId=ref,amountUSD=prep_amount))

    def emerge(self, job):
        if self.u('candidate-emergence', job['id']) >= self.design['paidJobCandidateProbability']: return
        family = 'composition' if job['jobType'] == 'interfaceComposition' else ('revalidation' if self.beta_index and self.u('family', job['id']) < .25 else 'contracts')
        if self.u('rights-clearance', job['id']) >= self.design['rightsClearedProbability']:
            self.events.append(dict(week=self.week, type='CANDIDATE_RIGHTS_NOT_CLEARED', originJob=job['id'])); return
        ref = 'retained-'+job['id']+'-'+family
        self.candidates.append(dict(id=ref, family=family, originJobId=job['id'], worker=job['worker'], emergedWeek=self.week, source='PAID_JOB_LEARNING_A', originCosts=self.origin(job), state='CANDIDATE', evaluated=False))

    def assay_plan(self,family,inventory_count,size=1,harm=0):
        stage=self.family_stage(family);n=self.p['network']['independentCases'];fraction=self.design['qualificationContextFractionByProfile'][self.profile_id]*size
        producer=add(scale(self.bundle(stage,effect=harm),n*fraction*(2+inventory_count)),self.bundle('intake'),self.bundle('package'))
        verifier=add(self.bundle('alphaQualify'),scale(self.bundle('verify'),n*fraction*(2+inventory_count)*self.design['qualificationCheckFraction']))
        if family=='composition':verifier=add(verifier,self.bundle('alphaJoint'))
        return producer,verifier

    def actual_assay(self,asset):
        family=asset['family'];stage=self.family_stage(family);context_fraction=self.design['qualificationContextFractionByProfile'][self.profile_id]
        producer=add(self.bundle('intake'),self.bundle('package'));verifier=self.bundle('alphaQualify')
        if family=='composition':verifier=add(verifier,self.bundle('alphaJoint'))
        for i in range(self.p['network']['independentCases']):
            fraction=context_fraction*mix(.6,1.4,self.u('qualification-context',asset['id'],self.week,i))
            equivalent=self.equivalent(i%self.p['network']['agentCount'],family,f'{asset["id"]}-{self.week}-{i}')
            effects=[0,0 if equivalent else asset['trueEffect']]+[0 if equivalent else self.assets[k]['trueEffect'] for k in asset['forecast']['comparisonKeys']]
            for effect in effects:
                producer=add(producer,self.bundle(stage,fraction,effect));verifier=add(verifier,self.bundle('verify',fraction*self.design['qualificationCheckFraction']))
        return producer,verifier

    def context_unchanged(self,asset):
        current=sorted(x['key'] for x in self.graph.discover(self.worker(asset['worker']),self.week,asset['family']) if x['key']!=asset.get('key'))
        return current==asset['forecast']['comparisonKeys'] and self.beta_index==asset['forecast']['comparisonBetaIndex']

    def forecast(self, candidate, deliberate=False):
        family = candidate['family']; worker = candidate['worker']; horizon = min(self.p['policies']['forecastMaximumWeeks'], self.horizon-self.week, self.o.get('assetLifetimeWeeks', self.p['network']['assetLifetimeWeeks']))
        if 'expiresWeek' in candidate:horizon=min(horizon,max(0,candidate['expiresWeek']-self.week))
        completed = [j for j in self.public_completed() if j['completionWeek'] <= self.week and (self.arm != 'private-alpha-availability-ablation' or j['worker'] == worker)]
        observed = [j for j in completed if j['completionWeek'] >= max(0, self.week-12)]
        frequency = len(observed)/max(1, min(12, self.week)); uses = min(self.d['maxCostAllocationUses'], frequency*horizon)
        stage = self.family_stage(family); burden = statistics.mean([sum(x['costUSD'] for x in j['stages'] if x['stage'] == stage) for j in observed]) if observed else 0
        if family == 'revalidation':
            burden = self.cost(self.bundle('revalidate')); uses = min(uses, len(self.assets)*horizon/max(1,self.d['maxGraphEvidenceAgeWeeks']))
        effect = max(0, statistics.mean(self.profile['effectStrengthInterval'])); effect = min(effect, self.p['skills'][family]['maximumStageReduction'])
        already = [x for x in self.graph.discover(self.worker(worker), self.week, family) if x['key']!=candidate.get('key')]
        equivalent_asset_effect = max([0]+[self.assets[x['key']]['observedEffect'] for x in already if x['key'] in self.assets])
        effect = max(0,effect-equivalent_asset_effect)
        overlap = max(self.beta()['equivalentByFamily'][family], statistics.mean(a['initialEquivalentProbability'] for a in self.p['network']['agents']))
        success = self.profile['constructionSuccessProbability'] if deliberate else self.design['paidCandidateUsefulPrior']
        assay_producer,assay_verifier=self.assay_plan(family,len(already));assay=add(assay_producer,assay_verifier)
        max_producer,max_verifier=self.assay_plan(family,len(already),size=1.4,harm=-.2)
        build = self.bundle(self.p['skills'][family]['constructBundle'] if deliberate else 'alphaExtract')
        fixed = self.cost(add(build, assay, self.bundle('alphaPublish')))
        maintain = self.cost(self.bundle('maintain'))*math.floor(horizon/self.p['network']['maintenanceIntervalWeeks'])
        distribution = self.cost(add(self.bundle('gapProbe'), self.bundle('adapt')))*(1 if self.arm == 'private-alpha-availability-ablation' else self.p['network']['agentCount'])*(1-overlap)
        gross = uses*burden*effect*success*(1-overlap)
        if self.policy['investment'] == 'riskAdjustedPositiveNetValue': gross *= self.design['riskAdjustedBenefitFraction']
        historical_margin = statistics.mean(max(0,j['priceUSD']-j['costUSD']) for j in observed) if observed else 0
        recent = [r for plan in self.calendar.records for r in plan['allocations'] if max(0,self.week-12) <= r['week'] < self.week]
        elapsed = max(1,min(12,self.week)); workers = self.p['network']['agentCount']; proposal = add(build,assay)
        capacities = {'modelHours':self.p['capacity']['modelHoursPerAgentWeek']*workers,'cpuHours':self.p['capacity']['proofContainerHoursPerAgentWeek']*workers,'tokens':self.calendar.tokens}
        extra = {'modelHours':proposal['modelHours'],'cpuHours':proposal['cpuHours'],'tokens':sum(proposal[k] for k in TOKEN_KEYS)}
        overflow = max([0]+[sum(r[k] for r in recent)/(capacity*elapsed)+extra[k]/max(1,capacity*horizon)-1 for k,capacity in capacities.items()])
        foregone = frequency*horizon*historical_margin*overflow
        return dict(asOfWeek=self.week,horizonWeeks=horizon,expectedUses=uses,grossExpectedSavingsUSD=gross,incrementalFixedUSD=fixed,maintenanceUSD=maintain,distributionUSD=distribution,foregoneContributionUSD=foregone,
            expectedNetUSD=gross-fixed-maintain-distribution-foregone, assayResources=assay, assayProducerResources=assay_producer,assayVerifierResources=assay_verifier,assayMaximumProducerResources=max_producer,assayMaximumVerifierResources=max_verifier,
            comparisonKeys=sorted(x['key'] for x in already),comparisonBetaIndex=self.beta_index,buildResources=build,observedCompleted=len(completed),scope='PAST_FEEDBACK_AND_DECLARED_PRIORS_ONLY; origin A excluded')

    def aged_forecast(self,forecast,at_week=None):
        at_week=self.week if at_week is None else at_week
        out=deepcopy(forecast);remaining=max(0,forecast['horizonWeeks']-(at_week-forecast['asOfWeek']));ratio=remaining/max(1,forecast['horizonWeeks'])
        out['expectedUses']*=ratio;out['grossExpectedSavingsUSD']*=ratio;out['maintenanceUSD']*=ratio
        out['usableForecastWeeksAtEvidence']=remaining
        out['expectedNetUSD']=out['grossExpectedSavingsUSD']-out['incrementalFixedUSD']-out['maintenanceUSD']-out['distributionUSD']-out['foregoneContributionUSD']
        return out

    def retention(self):
        if not self.can_retain or self.closed: return
        completed = self.public_completed()
        cohort = len(completed)//self.design['newCompletedJobsBeforeReassessment']
        if self.design['optionalDeliberateResearchEnabled'] and self.week % self.design['separateResearchReviewIntervalWeeks'] == 0 and len(completed) >= self.design['minimumJobsForSeparateResearch']:
            for family in ('contracts','composition','revalidation'):
                if (family,self.beta_index,cohort) not in self.seen_candidates and not any(c['family']==family and not c['evaluated'] for c in self.candidates):
                    origin=completed[-1]; self.candidates.append(dict(id=f'research-{self.week}-{family}',family=family,originJobId=origin['id'],worker=origin['worker'],emergedWeek=self.week,source='OPTIONAL_SEPARATE_RESEARCH_C',originCosts=self.origin(origin),state='CANDIDATE',evaluated=False))
        for candidate in self.candidates:
            if candidate['evaluated']: continue
            family = candidate['family']; minimum = self.p['skills'][family]['minimumMotivatingAcceptedJobs']
            if len(completed) < minimum: continue
            if family == 'revalidation' and self.beta_index == 0: continue
            marker = (family, self.beta_index, cohort)
            if marker in self.seen_candidates: candidate.update(evaluated=True, state='DEFERRED_EXISTING_EVALUATION'); continue
            evaluation = self.bundle('alphaAssess'); preview = self.calendar.preview(self.week, candidate['worker'], evaluation)
            operating = self.policy['funding'] == 'operating-only'
            if not preview or preview['completionWeek'] > self.week+1 or self.cost(evaluation) > self.free(operating): continue
            deliberate = candidate['source'] == 'OPTIONAL_SEPARATE_RESEARCH_C'
            self.calendar.commit(preview, candidate['id']+'-assessment'); bill = self.charge(self.cost(evaluation), 'candidateAssessment', candidate['id'], 'C' if deliberate else 'B', evaluation)
            candidate.update(evaluated=True,assessmentBillId=bill['id'],assessmentFundingOrigin=bill['fundingAtCommit'],state='ASSESSING');self.seen_candidates.add(marker)
            self.pending.append(('assessment',dict(completionWeek=preview['completionWeek'],candidate=candidate,deliberate=deliberate))); break

    def finish_assessment(self,event):
        candidate=event['candidate']; operating=self.policy['funding']=='operating-only'; family=candidate['family']
        forecast=self.forecast(candidate,event['deliberate']); candidate['forecast']=forecast
        decision=dict(week=self.week,candidateId=candidate['id'],family=family,source=candidate['source'],funding=self.policy['funding'],fundsBefore=self.free(operating),**{k:v for k,v in forecast.items() if not k.endswith('Resources')},decision='DECLINE')
        self.decisions.append(decision)
        if forecast['expectedNetUSD']<=0 or forecast['expectedUses']<1:
            candidate['state']='DECLINED_NONPOSITIVE_INCREMENTAL_VALUE'; return
        producer=add(forecast['buildResources'],forecast['assayMaximumProducerResources'],self.bundle('alphaPublish'));verifier=forecast['assayMaximumVerifierResources'];reserve=self.cost(add(producer,verifier))
        schedule=self.calendar.preview(self.week,candidate['worker'],producer,verifier)
        if not schedule or reserve>self.free(operating) or schedule['completionWeek']>=self.horizon:
            candidate['state']='DEFERRED_CASH_OR_CAPACITY'; return
        at_ready=self.aged_forecast(forecast,schedule['completionWeek'])
        decision.update(expectedUses=at_ready['expectedUses'],grossExpectedSavingsUSD=at_ready['grossExpectedSavingsUSD'],maintenanceUSD=at_ready['maintenanceUSD'],expectedNetUSD=at_ready['expectedNetUSD'],publicConstructionDelayWeeks=schedule['completionWeek']-self.week,usableForecastWeeksAtEvidence=at_ready['usableForecastWeeksAtEvidence'])
        if at_ready['expectedNetUSD']<=0 or at_ready['expectedUses']<1:
            candidate['state']='DECLINED_AFTER_PUBLIC_CAPACITY_QUOTE';return
        origin='OPERATING_GENERATED' if reserve<=self.free(True) else 'SEED_OR_MIXED'
        decision['cashCheckpoint']=dict(week=self.week,cashEventIndex=len(self.cash.events)-1,cashEventCount=len(self.cash.events),funds=deepcopy(self.cash.funds()),publicHoldsUSD=deepcopy(self.holds))
        self.holds[candidate['id']]=reserve; candidate['reservation']=self.calendar.commit(schedule,candidate['id']); candidate['completionWeek']=schedule['completionWeek']
        candidate['state']='RETAINING';candidate['reservationFundingOrigin']=origin
        decision.update(decision='RETAIN',reservedUSD=reserve,constructionFundingOrigin=origin,assessmentFundingOrigin=candidate['assessmentFundingOrigin'],wholeInitialProgramFundingOrigin='OPERATING_GENERATED' if origin==candidate['assessmentFundingOrigin']=='OPERATING_GENERATED' else 'SEED_OR_MIXED')
        self.pending.append(('candidate',candidate))

    def evidence(self, asset, revalidation=False):
        family = asset['family']; stage = self.family_stage(family); n = self.p['network']['independentCases']; context = self.graph.comparison_context(asset['key'])
        costs_beta, costs_candidate, truth = [], [], []; common_blind = self.u('qualification-common-blind', asset['id'], self.beta_index, self.week) < self.p['network']['commonBlindSpotProbability']
        for i in range(n):
            fraction = mix(.6, 1.4, self.u('qualification-context', asset['id'], self.week, i)); equivalent = self.equivalent(i % self.p['network']['agentCount'], family, f'{asset["id"]}-{self.week}-{i}')
            base = self.cost(self.bundle(stage, fraction)); effect = 0 if equivalent else asset['trueEffect']; candidate = self.cost(self.bundle(stage, fraction, effect))
            check = self.cost(self.bundle('verify', fraction*self.design['qualificationCheckFraction']))
            costs_beta.append(micros(base+check)); costs_candidate.append(micros(candidate+check))
            valid = asset['trueValid'] and not asset.get('qualificationHelperFault',False); passed = common_blind or self.u('qualification-case', asset['id'], self.week, i) < (self.p['network']['admissionCasesProbabilityIfValid'] if valid else self.p['network']['admissionCasesProbabilityIfInvalid'])
            truth.append(dict(case=i, trueValid=valid, observedAccepted=passed, equivalentBaseline=equivalent))
        comparators = {name: list(costs_beta) for name in context['requiredArms'] if name != 'candidate'}
        for name in comparators:
            if name.startswith('inventory:'):
                prior = self.assets.get(name.removeprefix('inventory:'))
                if prior: comparators[name] = [micros(self.cost(self.bundle(stage,mix(.6,1.4,self.u('qualification-context',asset['id'],self.week,i)),0 if truth[i]['equivalentBaseline'] else prior['trueEffect']))+self.cost(self.bundle('verify',mix(.6,1.4,self.u('qualification-context',asset['id'],self.week,i))*self.design['qualificationCheckFraction']))) for i in range(n)]
        evidence = matched_evidence(self.graph, asset['key'], costs_candidate, comparators, epoch=self.week, case_prefix=f'{asset["id"]}-v{self.beta_index}-w{self.week}', allocation_uses=max(1, min(self.d['maxCostAllocationUses'], math.floor(asset['forecast']['expectedUses']))), revalidation=revalidation)
        remaining = max(1,asset['forecast']['expectedUses'])
        for row, t in zip(evidence['arms']['candidate']['records'], truth):
            row['accepted'] = t['observedAccepted']; row['criticalFailure'] = False
            row['costs']['maintenance']=micros(asset['forecast']['maintenanceUSD']/remaining)
            row['costs']['adaptation']=micros(asset['forecast']['distributionUSD']/remaining)
        for name,arm in evidence['arms'].items():
            if not name.startswith('inventory:'):continue
            prior=self.assets.get(name.removeprefix('inventory:'))
            if prior:
                for i,row in enumerate(arm['records']):row['accepted']=common_blind or self.u('inventory-qualification',asset['id'],self.week,i,name)<(self.p['network']['admissionCasesProbabilityIfValid'] if prior['trueValid'] else self.p['network']['admissionCasesProbabilityIfInvalid'])
        from fixture_factory import bind_cost_ownership
        bills = [b for b in self.cash.bills if b['ref'] == asset['id'] and b['ledger'] in ('B','C') and (not revalidation or b['t'] == self.week*7)]
        entries = []; research_entries=[]
        for bill in bills:
            category = 'revalidation' if revalidation else ('failed_research' if bill['category'] == 'candidateAssessment' else 'construction')
            target=research_entries if bill['ledger']=='C' else entries
            target.append(dict(chargeId=bill['id'], ledgerCommitment=bill['commitment'], costs=costs(**{category:bill['amountMicros']}), ownership='OPTIONAL_RESEARCH_C' if bill['ledger']=='C' else 'INCREMENTAL_RETENTION_B'))
        evidence=bind_cost_ownership(evidence, origin_job_costs=asset['originCosts'], retention_entries=entries, research_entries=research_entries)
        asset['observedEffect']=statistics.mean((b-c)/max(1,b) for b,c in zip(costs_beta,costs_candidate))
        asset.setdefault('qualificationTruth', []).append(dict(week=self.week, commonBlind=common_blind, cases=truth)); return evidence

    def finish_candidate(self, candidate):
        ref=candidate['id'];reserved=self.holds.pop(ref);forecast=self.aged_forecast(candidate['forecast']);candidate['forecast']=forecast
        deliberate=candidate['source']=='OPTIONAL_SEPARATE_RESEARCH_C'
        family=candidate['family'];origin=next(j for j in self.jobs if j['id']==candidate['originJobId'])
        true_valid=self.u('paid-candidate-useful',ref)<(self.profile['constructionSuccessProbability'] if deliberate else self.design['paidCandidateUsefulPrior'])
        if not deliberate:true_valid=true_valid and origin['trueValid']
        effect=min(self.o.get('incrementalEffect',mix(*self.profile['effectStrengthInterval'],self.u('retained-effect',ref))),self.p['skills'][family]['maximumStageReduction'])
        prospective={**candidate,'trueEffect':effect,'trueValid':true_valid}
        assay_producer,assay_verifier=self.actual_assay(prospective);assay=add(assay_producer,assay_verifier)
        work=add(forecast['buildResources'],assay,self.bundle('alphaPublish'))
        if self.cost(work)>reserved+.01:raise AssertionError('Retention trial exceeded public maximum cost reservation')
        if deliberate:
            self.charge(self.cost(forecast['buildResources']), 'separateResearchConstruction',ref,'C',forecast['buildResources'])
            retained_work=add(assay,self.bundle('alphaPublish'))
        else: retained_work=work
        bill = self.charge(self.cost(retained_work), 'incrementalRetention', ref, 'B', retained_work)
        if not self.context_unchanged(prospective) or forecast['expectedUses']<1:
            candidate.update(state='QUALIFICATION_CONTEXT_CHANGED',failure='Paid qualification cannot establish current Alpha after a Beta/inventory change.');return
        deps = []
        if family == 'composition':
            available = self.graph.discover(self.worker(candidate['worker']), self.week, 'contracts')
            if available: deps = [dict(key=available[0]['key'], artifactHash=available[0]['artifactHash'])]
            # Otherwise the already-paid Beta specification stage supplies contracts.
        key = self.graph.create(self.worker(candidate['worker']), self.people['writer'], fixture_artifact(family), dependencies=deps, shareable=self.arm != 'private-alpha-availability-ablation', epoch=self.week, skill_id=ref)
        asset = {**candidate, 'key':key, 'trueValid':true_valid, 'trueEffect':effect, 'observedEffect':0, 'admittedWeek':None, 'expiresWeek':self.week+self.o.get('assetLifetimeWeeks',self.p['network']['assetLifetimeWeeks']), 'lastMaintenanceWeek':self.week,
            'realizedGrossSavingsUSD':0,'useCount':0,'qualificationResourcesByRole':{'producer':assay_producer,'independentVerifier':assay_verifier},'programCostUSD':self.cost(work)+self.cash.bills[int(candidate['assessmentBillId'].split('-')[1])]['amountMicros']/1e6,'billId':bill['id']}
        self.assets[key] = asset
        try:
            evidence = self.evidence(asset); self.graph.register_evidence(self.people['writer'], key, evidence, self.week); assessment = self.graph.assess(self.people['assessor'], key, self.week)
            self.graph.validate(self.people['validator_a'], key, self.week); self.graph.validate(self.people['validator_b'], key, self.week); self.graph.admit(self.people['admitter'], key, self.week)
            asset['admittedWeek'] = self.week; asset['state'] = 'ADMITTED'; candidate['state'] = 'ADMITTED'; asset['assessment'] = assessment
        except Refusal as exc:
            asset['state'] = 'REJECTED'; candidate['state'] = 'REJECTED'; asset['refusal'] = str(exc)

    def maintain_assets(self):
        for key, asset in list(self.assets.items()):
            if asset['state'] != 'ADMITTED': continue
            if self.closed:
                self.graph.retire(self.people['writer'],key,self.week);asset['state']='RETIRED_ENTERPRISE_CLOSED';continue
            if self.week >= asset['expiresWeek']:
                self.graph.retire(self.people['writer'], key, self.week); asset['state'] = 'EXPIRED'; continue
            record=self.graph.record(key);context=self.graph.comparison_context(key)
            stale=record['admission']['payload']['betaHash']!=self.graph.beta_hash or self.week>record['admission']['payload']['validUntil'] or record['admission']['payload']['comparisonEpoch']!=context['comparisonEpoch']
            if stale and not asset.get('maintenancePending'):
                # Fresh paired tests remain paid; only historical construction is sunk.
                forecast=self.forecast(asset);assay=forecast['assayResources'];work=add(scale(self.bundle('revalidate'),1.2),forecast['assayMaximumProducerResources'],scale(add(self.bundle('discovery'),self.bundle('gapProbe'),self.bundle('adapt')),len(self.p['skills'])));verification=forecast['assayMaximumVerifierResources'];amount=self.cost(add(work,verification));schedule=self.calendar.preview(self.week,asset['worker'],work,verification)
                if not schedule or amount > self.free(self.policy['funding']=='operating-only') or asset.get('revalidationPending'): continue
                if schedule['completionWeek']>=asset['expiresWeek']:
                    self.graph.retire(self.people['writer'],key,self.week);asset['state']='RETIRED_INSUFFICIENT_REMAINING_LIFE';continue
                if not self.upkeep_justified(asset,'revalidation',add(self.bundle('revalidate'),assay),schedule['completionWeek']):
                    self.graph.retire(self.people['writer'],key,self.week);asset['state']='RETIRED_NONPOSITIVE_MARGINAL_REVALIDATION';continue
                operating_before=self.free(True); self.holds[key] = amount; asset['revalidationPending'] = True; self.calendar.commit(schedule, key+'-revalidate')
                task=dict(id=f'revalidate-{key}-{self.week}',worker=asset['worker'],jobType='revalidation',factor=1,maximumCostUSD=amount,operatingFundsBeforeReservationUSD=operating_before,completionWeek=schedule['completionWeek'],assets=[],preparation=[],probeResults=[])
                self.prepare_assets(task)
                self.pending.append(('revalidate', dict(completionWeek=schedule['completionWeek'],key=key,assayResources=assay,maximumCostUSD=amount,task=task,forecast=forecast)))
            elif not asset.get('maintenancePending') and self.week-asset['lastMaintenanceWeek'] >= self.p['network']['maintenanceIntervalWeeks']:
                work = self.bundle('maintain'); schedule = self.calendar.preview(self.week, asset['worker'], work)
                if not schedule or self.cost(work) > self.free(self.policy['funding']=='operating-only'):
                    self.graph.retire(self.people['writer'], key, self.week); asset['state'] = 'RETIRED_UNFUNDED_UPKEEP'; continue
                if not self.upkeep_justified(asset,'maintenance',work,schedule['completionWeek']):
                    self.graph.retire(self.people['writer'],key,self.week);asset['state']='RETIRED_NONPOSITIVE_MARGINAL_MAINTENANCE';continue
                self.calendar.commit(schedule, key+'-maintenance'); self.charge(self.cost(work), 'assetMaintenance', asset['id'], 'B', work)
                asset['programCostUSD'] += self.cost(work); asset['maintenancePending']=True
                self.pending.append(('maintenance',dict(completionWeek=schedule['completionWeek'],key=key)))

    def upkeep_justified(self,asset,kind,new_work,ready_week):
        family=asset['family'];stage=self.family_stage(family);record=self.graph.record(asset['key'])
        proof_end=ready_week+self.d['maxGraphEvidenceAgeWeeks'] if kind=='revalidation' else record['admission']['payload']['validUntil']+1
        remaining=max(0,min(asset['expiresWeek'],self.horizon,self.week+self.p['policies']['forecastMaximumWeeks'],proof_end)-ready_week)
        observed=[j for j in self.public_completed() if j['completionWeek']>=max(0,self.week-12) and (self.arm!='private-alpha-availability-ablation' or j['worker']==asset['worker'])]
        frequency=len(observed)/max(1,min(12,self.week));uses=min(self.d['maxCostAllocationUses'],frequency*remaining)
        burden=statistics.mean(self.cost(self.bundle(stage,j['factor'])) for j in observed) if observed else 0
        if family=='revalidation':burden=self.cost(self.bundle('revalidate'));uses=min(uses,len(self.assets)*remaining/max(1,self.d['maxGraphEvidenceAgeWeeks']))
        overlap=max(self.beta()['equivalentByFamily'][family],statistics.mean(a['initialEquivalentProbability'] for a in self.p['network']['agents']))
        if self.week>=self.o.get('atWeek',self.horizon+1):overlap=max(overlap,self.o.get('baselineEquivalent',{}).get(family,0))
        alternatives=[self.assets[x['key']]['observedEffect'] for x in self.graph.discover(self.worker(asset['worker']),self.week,family) if x['key']!=asset['key']]
        net_effect=max(0,asset['observedEffect']-max([0]+alternatives))
        gross=uses*burden*net_effect*(1-overlap)*(1-self.p['network']['commonBlindSpotProbability'])
        new_cost=self.cost(new_work);future_upkeep=self.cost(self.bundle('maintain'))*math.floor(remaining/self.p['network']['maintenanceIntervalWeeks'])
        recipients=[asset['worker']] if self.arm=='private-alpha-availability-ablation' else range(self.p['network']['agentCount'])
        unintegrated=sum(not any(k[0]==worker and k[1]==asset['key'] and k[2]==self.beta_index and ok for k,ok in self.integrated.items()) for worker in recipients)
        distribution=self.cost(add(self.bundle('discovery'),self.bundle('gapProbe'),self.bundle('adapt')))*unintegrated*self.p['network']['adoptionProbabilityIfGapAndPositiveValue']*(1-overlap)
        expected_net=gross-new_cost-future_upkeep-distribution
        self.events.append(dict(week=self.week,type='MARGINAL_UPKEEP_DECISION',key=asset['key'],kind=kind,decision='SPEND' if expected_net>0 else 'RETIRE',remainingProofValidWeeks=remaining,expectedUses=uses,observedNetEffect=net_effect,grossExpectedSavingsUSD=gross,newWorkUSD=new_cost,newFutureUpkeepUSD=future_upkeep,newDistributionUSD=distribution,expectedNetUSD=expected_net,sunkDeliveryAndOriginalRetentionChargedUSD=0,
            cashCheckpoint=dict(week=self.week,cashEventIndex=len(self.cash.events)-1,cashEventCount=len(self.cash.events),funds=deepcopy(self.cash.funds()),publicHoldsUSD=deepcopy(self.holds))))
        return expected_net>0

    def finish_revalidation(self, event):
        asset = self.assets[event['key']]; self.holds.pop(event['key']); asset['revalidationPending'] = False
        asset['forecast']=self.aged_forecast(event['forecast']);task=event['task'];effect=0;helper=None;helper_receipt=None
        for row in task['probeResults']:self.probes[tuple(row['cache'])]=row['gap']
        for entry in task['assets']:
            self.integrated[tuple(entry['cache'])]=entry['adaptationSuccess']
            try:
                possible=self.assets[entry['key']]
                if possible.get('maintenancePending') or possible.get('revalidationPending') or self.week>=possible['expiresWeek']:raise Refusal('ASSET_NOT_OPERATIONALLY_CURRENT')
                self.graph.resolve_reuse(self.worker(task['worker']),entry['permit'],self.week)
                if entry['adaptationSuccess']:
                    helper=possible;effect=possible['trueEffect'];audit=self.graph.audit_log()
                    helper_receipt=dict(key=entry['key'],permit=entry['permit'],epoch=self.week,eventIndex=len(audit['events'])-1,logRoot=audit['root'])
            except Refusal as exc:self.events.append(dict(week=self.week,type='REVALIDATION_HELPER_REFUSED',reason=str(exc)))
        assay_producer,assay_verifier=self.actual_assay(asset)
        work=add(self.bundle('revalidate',effect=effect),assay_producer,assay_verifier);prep=add(*(self.bundle(n) for n in task['preparation']))
        amount=self.cost(work);prepcost=self.cost(prep)
        if amount+prepcost>event['maximumCostUSD']+1e-5:raise AssertionError('Revalidation exceeded its public reservation')
        self.charge(amount,'freshRevalidation',asset['id'],'B',work);asset['programCostUSD']+=amount
        if prepcost:self.charge(prepcost,'revalidationIntegration',asset['id'],'B',prep)
        if helper:
            helper['realizedGrossSavingsUSD']+=self.cost(self.bundle('revalidate'))-self.cost(self.bundle('revalidate',effect=effect));helper['useCount']+=1;helper['programCostUSD']+=prepcost
        else:asset['programCostUSD']+=prepcost
        asset['qualificationHelperFault']=bool(helper and not helper['trueValid'])
        asset.setdefault('revalidationHistory',[]).append(dict(week=self.week,forecast=deepcopy(asset['forecast']),helperReceipt=helper_receipt,costUSD=amount+prepcost,qualificationResourcesByRole={'producer':assay_producer,'independentVerifier':assay_verifier}))
        asset['qualificationResourcesByRole']={'producer':assay_producer,'independentVerifier':assay_verifier}
        if not self.context_unchanged(asset) or self.week>=asset['expiresWeek'] or asset['forecast']['expectedUses']<1:
            self.graph.retire(self.people['writer'],event['key'],self.week);asset['state']='RETIRED_QUALIFICATION_CONTEXT_CHANGED';return
        try:
            evidence = self.evidence(asset, True); self.graph.register_evidence(self.people['writer'], event['key'], evidence, self.week); self.graph.assess(self.people['assessor'], event['key'], self.week)
            self.graph.validate(self.people['validator_a'], event['key'], self.week); self.graph.validate(self.people['validator_b'], event['key'], self.week); self.graph.admit(self.people['admitter'], event['key'], self.week)
        except Refusal as exc:
            self.graph.retire(self.people['writer'], event['key'], self.week); asset['state'] = 'RETIRED_REVALIDATION_FAILED'; asset['refusal'] = str(exc)

    def run(self):
        for name in ('setup','history'):
            work = self.bundle(name); self.charge(self.cost(work), name, 'enterprise-opening', 'C' if name == 'history' else 'OPERATIONS', work)
            schedule = self.calendar.preview(0, 0, work)
            if schedule: self.calendar.commit(schedule, name)
        runoff=max(self.o.get('collectionDelayWeeks',self.p['buyers']['collectionDelayWeeks']),self.p['buyers']['supportWindowWeeks'])+2
        for week in range(self.horizon+runoff+1):
            self.week = week; self.cash.advance(week*7)
            target = 0 if self.frozen else max(i for i,v in enumerate(self.versions) if v['startWeek'] <= week)
            if target != self.beta_index:
                self.beta_index = target; self.graph.advance_beta(self.people['admitter'], self.beta_descriptor(), week); self.events.append(dict(week=week,type='BETA_UPGRADE',version=target+1))
            due = [x for x in self.pending if x[1]['completionWeek'] <= week]; self.pending = [x for x in self.pending if x[1]['completionWeek'] > week]
            for kind, event in due:
                if kind == 'job': self.finish_job(event)
                elif kind == 'candidate': self.finish_candidate(event)
                elif kind == 'assessment': self.finish_assessment(event)
                elif kind == 'revalidate': self.finish_revalidation(event)
                elif kind == 'maintenance':
                    asset=self.assets[event['key']]; asset['maintenancePending']=False; asset['lastMaintenanceWeek']=week
                else:
                    job = event['job']; public_useful = not event['detected']
                    if event['detected']: self.cash.remedy(job['id'], week*7, delay=0)
                    self.feedback.append(dict(jobId=job['id'], technicalAccepted=True, publicUseful=public_useful, week=week))
                    buyer = self.buyers[job['buyer']]; buyer['trust'] = bounded(buyer['trust']+(.01 if public_useful else -.20))
                    if event['detected']: buyer['spent'][job['week']//52]-=job['priceUSD']
                    elif self.can_retain and week<self.horizon: self.emerge(job)
            self.cash.advance(week*7)
            if week == self.horizon:
                self.horizon_funds=deepcopy(self.cash.funds()); self.events.append(dict(week=week,type='NEW_BUSINESS_HORIZON_CLOSED'))
                for key,asset in self.assets.items():
                    if asset['state']=='ADMITTED': self.graph.retire(self.people['writer'],key,week); asset['state']='RETIRED_AT_HORIZON'
            if week >= self.horizon:
                unsettled=self.pending or any(x['status']=='pending' or (x['warrantyUntil']>=week*7 and x['status']=='collected') for x in self.cash.invoices)
                if unsettled:
                    self.charge(self.p['company']['fixedOperatingUsdWeek'],'settlementRunoffOperations',f'runoff-{week}','OPERATIONS')
                    self.cash.snapshot(week*7); continue
                break
            ops = self.bundle('ops'); amount = self.p['company']['fixedOperatingUsdWeek']+self.cost(ops)
            schedule = self.calendar.preview(week, week % self.p['network']['agentCount'], ops)
            if not self.closed and amount <= self.free() and schedule:
                self.charge(amount, 'weeklyCompleteOperations', f'week-{week}', 'OPERATIONS', ops)
                self.calendar.commit(schedule, f'ops-{week}')
            else:
                if not self.closed:
                    cash_limited=amount>self.free();capacity_limited=not bool(schedule)
                    self.closure_reason='cash_and_capacity' if cash_limited and capacity_limited else ('cash' if cash_limited else 'capacity');self.closure_week=week
                self.closed=True
            self.maintain_assets()
            for buyer in self.buyers:
                if self.u('arrival', week, buyer['id']) < min(1,self.p['buyers']['weeklyOpportunityProbability']*self.o.get('opportunityMultiplier',1)): self.opportunity(buyer)
            self.retention(); self.cash.snapshot(week*7)
        return self.result()

    def result(self):
        cash = self.cash.serialize(); accepted = sum(j['usefulAccepted'] for j in self.jobs); technical = sum(j.get('technicalAccepted',False) for j in self.jobs); false = sum(j.get('technicalAccepted',False) and not j['usefulAccepted'] for j in self.jobs)
        category = {}; ledger = {}
        for bill in cash['bills']:
            category[bill['category']] = category.get(bill['category'],0)+bill['amountMicros']; ledger[bill.get('ledger','FINANCIAL')] = ledger.get(bill.get('ledger','FINANCIAL'),0)+bill['amountMicros']
        for asset in self.assets.values(): asset['realizedDirectNetUSD'] = asset['realizedGrossSavingsUSD']-asset['programCostUSD']
        program_cost=sum(b['amountMicros'] for b in cash['bills'] if b.get('ledger') in ('B','C') and b['ref']!='enterprise-opening')/1e6
        program_net=sum(a['realizedGrossSavingsUSD'] for a in self.assets.values())-program_cost
        summary = dict(seed=self.seed,scenario=self.scenario,profile=self.profile_id,arm=self.arm,policyId=self.policy['id'],accepted=accepted,technicalAccepted=technical,falsePasses=false,
            offers=len(self.offers),orders=len(self.jobs),collectionsUSD=cash['funds']['collected'],completeCostsUSD=cash['funds']['accrued'],completeProfitUSD=cash['funds']['collected']-cash['funds']['accrued'],
            costPerAcceptedUSD=cash['funds']['accrued']/accepted if accepted else None, cashRemainingUSD=cash['funds']['cash'], availableOperatingUSD=cash['funds']['availableOperating'],cashValid=not cash['insolvent'],
            retainedCandidates=sum(x['decision']=='RETAIN' for x in self.decisions),assessedCandidates=sum(x['evaluated'] for x in self.candidates),admittedAssets=sum(x['admittedWeek'] is not None for x in self.assets.values()),assetUses=sum(x['useCount'] for x in self.assets.values()),
            directlyPositiveAssets=sum(x['realizedDirectNetUSD']>0 for x in self.assets.values()),retentionResearchProgramNetResourcesUSD=program_net,retentionResearchProgramCostUSD=program_cost,
            investmentValueBoundary='Direct asset resource savings exclude foregone sales and learning spillovers; complete paired enterprise profit is the primary policy-value estimand. Program total includes every failed B/C attempt.',
            operatingHorizonWeeks=self.horizon,settlementEndWeek=self.week,closed=self.closed,closureReason=self.closure_reason,closureWeek=self.closure_week,actualRevenueUSD=0,actualCompleteCostUSD=None,ledgerCostsMicros=ledger)
        return dict(schema='beyond-beta-world/v1',basis='CONDITIONAL_SIMULATION_WITH_EXECUTED_OFFLINE_GRAPH_GUARDS',summary=summary,policy=self.policy,cash=cash,jobs=self.jobs,offers=self.offers,candidates=self.candidates,assets=list(self.assets.values()),investmentDecisions=self.decisions,
            graph=dict(records=[self.graph.record(key) for key in self.assets],audit=self.graph.audit_log(),publicAuthorities=list(self.graph.authorities.values())),events=self.events,feedback=self.feedback,costCategoriesMicros=category,
            resourceSchedules=self.calendar.records,resourceConsumption=self.resource_consumption,unspentPublicCostHolds=self.holds,pendingEvents=self.pending,horizonFunds=getattr(self,'horizon_funds',None),actualModelCalls=0,actualCompleteCostUSD=None)


def run_world(protocol, policy, scenario, profile, seed, arm):
    return World(protocol, policy, scenario, profile, seed, arm).run()
