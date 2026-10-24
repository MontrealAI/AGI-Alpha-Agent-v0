# SPDX-License-Identifier: Apache-2.0
"""Presentation and explicitly hypothetical sensitivity; no confirmatory reanalysis.

Consumes the frozen analysis output. This file is outside the preregistered
scientific source inventory and does not select, alter, or rerun missions.
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / 'results/holdout-01/analysis/summary.json').read_text())
M = S['measuredCampaign']
L = {(r['condition'], r['method']): r for r in S['summary']}
P = next(r for r in S['contrasts'] if r['interpretation'] == 'primary')
def mean(c, m, k='utility'):
    return L[c, m][k]['mean']
def f(x, digits=2):
    return f'{x:,.{digits}f}'
def pct(x):
    return f'{100*x:.1f}'
def macro(name, body):
    return '\\newcommand{\\' + name + '}{%\n' + body + '\n}\n'
def cpu(v):
    return (v.get('user', 0) + v.get('system', 0)) / 1e6

assert S['rows'] == 21504 and S['pairedMissions'] == 3072
assert not S['exactChecks']['cloneMismatches']
assert not S['exactChecks']['stationaryModelObjectiveMismatches']
conditions = M['scenarios']
methods = M['methods']
names = {'idea':'Conservative', 'greedy':'Greedy', 'disclosed':'Disclosed',
         'verified':'Verified', 'clone':'Complete clone', 'expert':'Exact expert',
         'adaptive-expert':'Adaptive expert'}
labels = {'ordinary':'Ordinary', 'capacity-doubled':'Doubled capacity',
          'tight-validity':'Short validity', 'measurement-drift':'Measurement drift',
          'demand-drift':'Demand drift', 'reliability-failure':'Slot failures',
          'cheap-calibration':'Zero-duration calibration', 'expensive-evidence':'Repeated inspection'}
parent_cpu = cpu(M['parentCpuMicros'])
worker_cpu = sum(cpu(w['cpu']) for w in M['workers'].values())
parts = []
parts.append(macro('HeadlineResult',
    f"Shared calibration increases ordinary useful output by {pct(P['relativeUtilityDifference'])}\\%. "
    "The complete copy matches every mission. Conventional scheduling also obtains the benefit; "
    "under drift, fresh recalibration wins. What survives is a reusable capability, "
    "with no demonstrated exclusive output premium."))
parts.append(macro('AbstractResults',
    f"Ordinary useful output rises from {f(mean('ordinary','idea'))} to {f(mean('ordinary','verified'))} "
    f"synthetic units per mission: {pct(P['relativeUtilityDifference'])}\\% "
    f"(paired 95\\% interval {pct(P['relativeUtilityDifferenceCI95'][0])}--{pct(P['relativeUtilityDifferenceCI95'][1])}\\%). "
    "The complete clone matches all 3,072 plans and outcomes; an independently written expert "
    "matches the stationary-model optimum. The greedy competitor ties ordinary output with lower "
    "measured computing cost. Hidden drift reverses the baseline benefit, and delayed diagnostics "
    "let the adaptive competitor improve the next decision."))
parts.append(macro('MainResults',
    f"The campaign completed all 3,072 worlds and 21,504 method records, with {M['totals']['methodFailures']} "
    f"method noncompletions. Ordinary mean useful output is {f(mean('ordinary','verified'))} for the "
    f"verified artifact and {f(mean('ordinary','idea'))} for the conservative baseline. The paired "
    f"difference is {f(P['utilityDifference'])} units (95\\% cluster-bootstrap interval "
    f"{f(P['utilityDifferenceCI95'][0])}--{f(P['utilityDifferenceCI95'][1])}), or "
    f"{pct(P['relativeUtilityDifference'])}\\% ({pct(P['relativeUtilityDifferenceCI95'][0])}--"
    f"{pct(P['relativeUtilityDifferenceCI95'][1])}\\%). This exceeds the predeclared 5\\% "
    "practical margin against that restriction.\n\n"
    "There are zero complete-copy plan/outcome mismatches and zero independent-expert "
    "stationary-model objective mismatches. Disclosed and verified native planning yield the "
    "same productive outcomes; the extra evidence machinery is not awarded utility. "
    "The conventional greedy policy also ties ordinary useful output. These comparisons defeat "
    "an exclusive-performance interpretation of the primary improvement.\n\n"
    "Doubled capacity, one-tick validity and zero-duration calibration eliminate the ordinary "
    "restriction's output gap. The result depends on the actual bottleneck: removing or changing "
    "that bottleneck removes the measured advantage over the ablation."))
table = [r'\begin{table}[H]\small\renewcommand{\arraystretch}{1.13}',
         r'\begin{tabularx}{\textwidth}{@{}Xrrrr@{}}\toprule',
         r'Condition & Conservative & Verified$^{*}$ & Greedy & Adaptive\\\midrule']
for condition in conditions:
    table.append(labels[condition] + ' & ' + ' & '.join(f(mean(condition, m)) for m in ['idea','verified','greedy','adaptive-expert']) + r'\\')
table += [r'\bottomrule\end{tabularx}',
          r'\caption{Mean true useful output in synthetic units. Each entry averages 384 missions in 32 seed clusters. $^{*}$The complete clone, disclosed planner and stationary exact expert have the same mean output; raw exact predicates and all method-specific intervals remain in the machine-readable analysis. These policies are counterfactual alternatives, not additive production.}',
          r'\end{table}']
parts.append(macro('ResultsTable', '\n'.join(table)))
drift = next(x for x in S['contrasts'] if x['condition']=='measurement-drift' and x['reference']=='adaptive-expert')
parts.append(macro('DriftResults',
    f"Under measurement drift, the verified artifact earns {f(mean('measurement-drift','verified'))} "
    f"units per mission versus {f(mean('measurement-drift','idea'))} for conservative recalibration "
    f"and {f(mean('measurement-drift','adaptive-expert'))} for the adaptive expert. The verified-minus-adaptive "
    f"difference is {f(drift['utilityDifference'])} units (descriptive interval "
    f"{f(drift['utilityDifferenceCI95'][0])} to {f(drift['utilityDifferenceCI95'][1])}). "
    "The native proof remains correct about its stationary model while two later-slot measurements "
    "are wrong. More complete internal verification does not make that model physically true.\n\n"
    "The adaptive expert receives no earlier private warning. At the first epoch it has the "
    "same stationary prior; subsequent recovery uses the prior epoch's public delayed bias profile. "
    "The conservative policy has the highest full-horizon output by paying for fresh calibration. "
    "The adaptive expert ties it in epochs two through twelve but cannot recover its first-epoch loss. "
    "This unfavorable result identifies the assumption that fails, rather than treating lost output as an outlier.\n\n"
    f"The greedy comparator earns {f(mean('measurement-drift','greedy'))} units without observing future drift: "
    "it places a high-value sample first, before the hidden shift. For seed 101's first epoch, job weights "
    "are 7, 11, 13 and 13. The native and stationary exact plans place weight 11 in the surviving first "
    "measurement slot; greedy places weight 13 there. Both optimize the nominal stationary objective. "
    "Different optimal-model tie breaking can therefore matter after the model fails. Under random "
    "slot failures, greedy's slightly higher sample mean is a descriptive fluctuation, not an established "
    "reliability advantage."))
parts.append(macro('ComputeResults',
    f"In ordinary operation, the verified native service uses {f(mean('ordinary','verified','accountedRowCpuMs'),3)} "
    f"ms of attributed CPU per mission, compared with {f(mean('ordinary','expert','accountedRowCpuMs'),3)} ms "
    f"for the exact expert and {f(mean('ordinary','greedy','accountedRowCpuMs'),3)} ms for the signed greedy service. "
    "All three have the same ordinary useful output. These descriptive timings include the common "
    "external evaluator and receipt-service setup where present; they do not include unknown authoring labor.\n\n"
    f"Copying {M['copying']['sourceFiles']} files ({M['copying']['sourceBytes']:,} bytes) took "
    f"{f(M['copying']['wallMs'],3)} ms on the prepared host. The copied worker's startup/import took "
    f"{f(M['copying']['importStartupMs'],3)} ms; its evidence-module import took "
    f"{f(M['copying']['evidenceImportMs'],3)} ms. Fresh complete execution then matched every mission. "
    "These are measured software operations, not a measured time for an outside organization to acquire "
    "equipment, understand the work, or enter a market."))
ct = [r'\begin{table}[H]\small\renewcommand{\arraystretch}{1.13}',
      r'\begin{tabularx}{\textwidth}{@{}Xrrrr@{}}\toprule',
      r'Ordinary policy & CPU, ms & Calibrations & Samples & Receipt, bytes\\\midrule']
for method in methods:
    ct.append(names[method] + ' & ' + f(mean('ordinary',method,'accountedRowCpuMs'),3) + ' & ' +
              f(mean('ordinary',method,'calibrationAcquisitions'),1) + ' & ' +
              f(mean('ordinary',method,'sampleAcquisitions'),1) + ' & ' +
              f(mean('ordinary',method,'receiptBytes'),0) + r'\\')
ct += [r'\bottomrule\end{tabularx}',
       r'\caption{Per-mission means. Each policy has a four-tick contested horizon plus four auxiliary diagnostic acquisitions outside it. Receipt bytes omit native completion/model exports, retained separately. CPU is measured; acquisition counts are simulated.}',
       r'\end{table}',
       f"The confirmation's measured process total is {f(parent_cpu+worker_cpu,3)} CPU seconds "
       f"({f(parent_cpu,3)} parent and {f(worker_cpu,3)} across both native workers), over "
       f"{f(M['wallMs']/1000,3)} wall seconds. The runner's recorded raw/ledger/completion storage is "
       f"{M['storageBytes']:,} bytes. These totals cover all tested alternatives and shared harness work; "
       "they are not the resource bill of one deployed policy. Each policy's counterfactual horizon "
       "contains 12,288 auxiliary diagnostic acquisitions. It would be incorrect to present the sum "
       "over seven policies as physical laboratory production."]
parts.append(macro('CostTable', '\n'.join(ct)))

def read(relative):
    return json.loads((ROOT/relative).read_text())
verification=read('evidence/holdout-independent-audit-cost.json')
analysis_cost=read('evidence/holdout-analysis-resources.json')
nominal_cost=read('evidence/holdout-nominal-bound-audit-cost.json')
native_cost=read('evidence/retained-completion-audit-resources.json')
evm_cost=read('../contracts-audit/tests/contracts/evidence/writer10-contract-results.json')['costs']
graph_cost=read('../contracts-audit/lifecycle/lifecycle-evidence.json')['costs']
accounted_runs=[
    {'run':'Confirmation campaign','cpuSeconds':parent_cpu+worker_cpu,'wallSeconds':M['wallMs']/1000,'evidence':'results/holdout-01/metrics.json'},
    {'run':'Independent replay/signatures/ledgers','cpuSeconds':verification['totalCpuSeconds'],'wallSeconds':verification['elapsedSeconds'],'evidence':'evidence/holdout-independent-audit-cost.json'},
    {'run':'48 retained native completions','cpuSeconds':native_cost['cpuSeconds'],'wallSeconds':native_cost['wallSeconds'],'evidence':'evidence/retained-completion-audit-resources.json'},
    {'run':'Closed-form objective audit','cpuSeconds':nominal_cost['userCpuSeconds']+nominal_cost['systemCpuSeconds'],'wallSeconds':nominal_cost['elapsedSeconds'],'evidence':'evidence/holdout-nominal-bound-audit-cost.json'},
    {'run':'Frozen statistical analysis','cpuSeconds':analysis_cost['cpuSeconds'],'wallSeconds':analysis_cost['wallSeconds'],'evidence':'evidence/holdout-analysis-resources.json'},
    {'run':'Local EVM and registry demonstration','cpuSeconds':(evm_cost['cpuUserMs']+evm_cost['cpuSystemMs'])/1000,'wallSeconds':evm_cost['wallMs']/1000,'evidence':'../contracts-audit/tests/contracts/evidence/writer10-contract-results.json'},
    {'run':'Published dispatcher graph','cpuSeconds':graph_cost['cpuMicroseconds']/1e6,'wallSeconds':graph_cost['wallMicroseconds']/1e6,'evidence':'../contracts-audit/lifecycle/lifecycle-evidence.json'},
    {'run':'Separate Node development cases','cpuSeconds':0.676216,'wallSeconds':0.487965,'evidence':'../contracts-audit/lifecycle/development-case.json'},
]
additional=[r'\begin{table}[H]\small\renewcommand{\arraystretch}{1.1}',
    r'\begin{tabularx}{\textwidth}{@{}Xrr@{}}\toprule',
    r'Separately recorded execution & CPU seconds & Wall seconds\\\midrule']
for row in accounted_runs:
    additional.append(row['run']+' & '+f(row['cpuSeconds'],3)+' & '+f(row['wallSeconds'],3)+r'\\')
additional += [r'\bottomrule\end{tabularx}',
    r'\caption{Additional verification and mechanism costs are visible. Per-method CPU is already inside the campaign total and is not added again. Wall durations can overlap and are not summed as total elapsed time. Each lane retains its exact timer boundaries.}',r'\end{table}',
    f"The listed, distinct executions account for {f(sum(r['cpuSeconds'] for r in accounted_runs),3)} CPU seconds. "
    "This is not a full research or deployment cost: dependency download/compilation, earlier development, "
    "native-route execution, authoring, layout and some process startup were not completely metered. "
    "The archive records these exclusions rather than assigning them a zero price."]
parts.append(macro('AdditionalCosts','\n'.join(additional)))
evidence=ROOT/'evidence';evidence.mkdir(exist_ok=True)
(evidence/'measured-run-cost-ledger.json').write_text(json.dumps({
    'schema':'nova-seeds-measured-runs/v1','runs':accounted_runs,
    'sumOfListedCpuSeconds':sum(r['cpuSeconds'] for r in accounted_runs),
    'totalElapsedNotSummed':True,'fullCostEstablished':False,
    'unmetered':['dependency download/compilation','earlier development','native-route execution','authoring','layout','some startup','human effort','physical equipment','opportunity cost']},indent=2)+'\n')

# Illustrative accounting only: values are not price forecasts or willingness to pay.
assumptions = [
    dict(name='output-only', value=1, calibration=0, sample=0, diagnostic=0, cpu_hour=0, omitted_delta=0),
    dict(name='balanced-acquisitions', value=1, calibration=1, sample=1, diagnostic=1, cpu_hour=1, omitted_delta=0),
    dict(name='expensive-sample', value=1, calibration=1, sample=20, diagnostic=1, cpu_hour=1, omitted_delta=0),
    dict(name='additional-omitted-cost', value=1, calibration=1, sample=1, diagnostic=1, cpu_hour=1, omitted_delta=10),
    dict(name='compute-only', value=0, calibration=0, sample=0, diagnostic=0, cpu_hour=100, omitted_delta=0),
]
sens=[]
for condition in conditions:
    for other in [m for m in methods if m!='verified']:
        d={k:mean(condition,'verified',k)-mean(condition,other,k) for k in
           ['utility','calibrationAcquisitions','sampleAcquisitions','diagnosticAcquisitions','accountedRowCpuMs']}
        for a in assumptions:
            cost=(a['calibration']*d['calibrationAcquisitions']+a['sample']*d['sampleAcquisitions']+
                  a['diagnostic']*d['diagnosticAcquisitions']+a['cpu_hour']*d['accountedRowCpuMs']/3600000+a['omitted_delta'])
            sens.append(dict(condition=condition, comparator=other, assumption=a['name'],
                utility_delta=d['utility'], modeled_cost_delta=cost,
                modeled_surplus_delta=a['value']*d['utility']-cost,
                break_even_value_per_utility=(cost/d['utility'] if d['utility']>0 else None),
                **{k:v for k,v in a.items() if k!='name'}))
evidence=ROOT/'evidence';evidence.mkdir(exist_ok=True)
with (evidence/'hypothetical-sensitivity.csv').open('w',newline='') as stream:
    w=csv.DictWriter(stream,fieldnames=list(sens[0]));w.writeheader();w.writerows(sens)
(evidence/'hypothetical-sensitivity.json').write_text(json.dumps({
    'schema':'nova-seeds-hypothetical-sensitivity/v1',
    'status':'ASSUMED_PRICES_NOT_OBSERVED_CASH_OR_MARKET_DEMAND',
    'unit':'arbitrary illustrative monetary unit; no actual quote',
    'unknowns':['labor','opportunity cost','real instrument cost','energy','liability','commercial demand'],
    'assumptions':assumptions,'comparisons':sens},indent=2)+'\n')
ordinary=[r for r in sens if r['condition']=='ordinary' and r['comparator']=='idea']
balanced=next(x for x in ordinary if x['assumption']=='balanced-acquisitions')
expensive=next(x for x in ordinary if x['assumption']=='expensive-sample')
omitted=next(x for x in ordinary if x['assumption']=='additional-omitted-cost')
parts.append(macro('SensitivityResults',
    f"For an explicitly hypothetical ordinary mission, assign value 1 per useful unit, price 1 per "
    "calibration and sample, and price 1 per CPU hour. The verified-minus-conservative modeled surplus "
    f"is {f(balanced['modeled_surplus_delta'])} arbitrary monetary units. Increasing only the sample "
    f"price to 20 changes it to {f(expensive['modeled_surplus_delta'])}; alternatively, adding 10 units "
    f"of otherwise omitted cost changes it to {f(omitted['modeled_surplus_delta'])}. These reversals "
    "show the dependence on unobserved resource valuations. No price in this calculation is a market "
    "quote or a measured willingness to pay. The archive retains all 240 condition/comparator/assumption "
    "combinations, including negative output differences and undefined positive-output break-even values."))
parts.append(macro('LifecycleResults',
    "The separately executed published-runtime bridge completes 16 actual pure callbacks across "
    "two eight-job graphs, all seven lifecycle families, 24 negative controls and 121 verified journal "
    "events. Fresh second-epoch world evidence, mission, institution, environment, release, authorization "
    "and reservations are required. Zero production grants are issued. The development-case Node work "
    "uses 487.965 ms wall and 676.216 ms CPU; the Python graph uses 3.185404 s wall and 3.020314 s CPU. "
    "Those are single-run measurements under concurrent host activity, with the documented timing exclusions."))
claims=[
    dict(claim='Operational restriction removal helps in ordinary worlds',status='SUPPORTED_IN_SIMULATION',
         evidence='results/holdout-01/analysis/summary.json:contrasts[interpretation=primary]',cost='one fewer calibration; one additional attempted sample per ordinary mission',limit='four jobs; four ticks; synthetic priorities and exact calibration'),
    dict(claim='Exclusive output advantage survives complete copying',status='NOT_SUPPORTED',
         evidence='exactChecks.cloneMismatches:0/3072',cost='copying and complete fresh execution measured',limit='same-host existence witness; independent human rebuild time unknown'),
    dict(claim='Native framework outperforms competent conventional planning',status='NOT_SUPPORTED',
         evidence='ordinary greedy/expert equality; accounted CPU in means.csv',cost='native service uses more CPU in ordinary worlds',limit='small finite model; no scale claim'),
    dict(claim='Model proof guarantees useful physical output',status='REFUTED_IN_DRIFT_CONTROL',
         evidence='measurement-drift rows and signed-falsehood control',cost='failed samples consume capacity; adaptive uses delayed diagnostics',limit='physical truth trusted synthetic world; no sensor attestation'),
    dict(claim='NFT adds productive output in this binding interface',status='NO_MEASURED_INCREMENT',
         evidence='../contracts-audit/tests/contracts/evidence/writer10-contract-results.json',cost='local gas and signed-registry CPU/bytes retained separately',limit='structurally equal allocator output; escrow/public consensus not compared'),
    dict(claim='Confidential disclosure can preserve equal authorized inputs',status='IMPLEMENTED_FUNCTIONAL_CONTROL',
         evidence='evidence/disclosure-controls.json',cost='AES-GCM payload/CPU recorded; rights restricted equally',limit='public synthetic generator; no secrecy claim or novel primitive'),
    dict(claim='All four repositories deploy the new instrument mission',status='NOT_IMPLEMENTED_OR_QUALIFIED',
         evidence='../foundations/evidence/integration-map.json and ../contracts-audit/lifecycle/lifecycle-evidence.json',cost='source custody and local calls recorded',limit='actual supported native mission differs; no external Fleet worker'),
    dict(claim='Commercial profit or durable private rents established',status='UNKNOWN_NOT_ESTABLISHED',
         evidence='analysis monetary nulls and hypothetical-sensitivity.csv',cost='actual customer revenue zero; human/physical/demand costs unknown',limit='no observed market; modeled prices not proceeds'),
]
(evidence/'claim-evidence-cost-ledger.json').write_text(json.dumps({'schema':'nova-seeds-claim-ledger/v1','claims':claims},indent=2)+'\n')
cl=[r'\begingroup\small\begin{longtable}{@{}>{\raggedright\arraybackslash}p{0.29\textwidth}>{\raggedright\arraybackslash}p{0.30\textwidth}>{\raggedright\arraybackslash}p{0.35\textwidth}@{}}',
    r'\toprule Claim & Evidence/status & Cost and limit\\\midrule\endhead',
    r'Ordinary restriction removal helps & Paired primary comparison; supported in simulation & Extra sample replaces a calibration; supplied utility is not willingness to pay.\\',
    r'Exclusive output survives copying & Not supported: complete clone matches all missions & Actual copy and execution charged; human reconstruction time unknown.\\',
    r'Framework beats sufficient conventional planning & Not supported: ordinary output ties; native CPU is higher & Same signed service available to competitors; no scalability finding.\\',
    r'Proof guarantees real usefulness & Refuted by model-valid drift failures and signed falsehood & Failed work still consumes resources; no trusted hardware.\\',
    r'NFT improves instrument output & No measured increment in the binding-interface control & Local gas and registry CPU are different units; escrow not reproduced.\\',
    r'Confidentiality equals productive superiority & Not supported; AES-GCM control only & Equal authorized plaintext; public synthetic workloads are not secret.\\',
    r'All native integrations admit the new mission & Unqualified/unavailable & Existing supported mission and local published graph only; no live Fleet execution.\\',
    r'Full-cost profitability or permanent capture & Unknown; no observed customer revenue & Human, physical, liability and demand costs unmeasured.\\',
    r'\bottomrule\end{longtable}\endgroup']
parts.append(macro('ClaimLedger','\n'.join(cl)))
freeze=ROOT/'protocol/source-freeze.json'
freeze_sha=hashlib.sha256(freeze.read_bytes()).hexdigest()
inventory=json.loads(freeze.read_text())['sourceInventoryHash']
parts.append(macro('FreezeIdentity',
    'Source inventory SHA-256:\\par\\noindent{\\small\\texttt{'+inventory+'}}\\par '
    'Protocol/source/analysis freeze SHA-256:\\par\\noindent{\\small\\texttt{'+freeze_sha+'}}\\par '
    'Both were preserved and publicly registered in issue \\#4850 before the confirmation. '
    'The final archive manifest records the canonical PDF digest and every payload member.'))
(ROOT/'paper/generated.tex').write_text('% Generated only from frozen analysis and separately labelled controls.\n'+'\n'.join(parts))
(evidence/'accounting-summary.json').write_text(json.dumps({
    'schema':'nova-seeds-accounting-summary/v1','parentCpuSeconds':parent_cpu,'nativeWorkersCpuSeconds':worker_cpu,
    'confirmationCpuSeconds':parent_cpu+worker_cpu,'confirmationWallSeconds':M['wallMs']/1000,
    'runnerStorageBytes':M['storageBytes'],'diagnosticsPerCounterfactualPolicy':3072*4,
    'actualCustomerRevenue':0,'fullCostProfit':None,'unknownHumanAndPhysicalCost':True,
    'copying':M['copying'],'sourceInventoryHash':inventory},indent=2)+'\n')
binding={'schema':'nova-seeds-confirmation-binding/v1','sourceInventoryHash':inventory,
         'analysisSha256':hashlib.sha256((ROOT/'results/holdout-01/analysis/summary.json').read_bytes()).hexdigest(),
         'rawSha256':S['rawSha256'],'ledgerSha256':S['ledgerSha256'],'worlds':S['pairedMissions'],'records':S['rows'],
         'cloneMismatches':len(S['exactChecks']['cloneMismatches']),'primary':P,'physicalResource':'synthetic',
         'productionAuthority':'none','monetaryProfit':None}
(evidence/'confirmation-binding-summary.json').write_text(json.dumps(binding,indent=2)+'\n')
print(json.dumps({'generated':'paper/generated.tex','sensitivityRows':len(sens),'claims':len(claims),
                  'cpuSeconds':parent_cpu+worker_cpu,'wallSeconds':M['wallMs']/1000},indent=2))
