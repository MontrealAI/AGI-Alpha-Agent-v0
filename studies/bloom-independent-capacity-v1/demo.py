# SPDX-License-Identifier: Apache-2.0
import argparse
import hashlib
import html
import json
from pathlib import Path
from time import perf_counter_ns,process_time_ns
from core import Graph,Meter,build_operator,canonical,coverage_table,digest,environment_digest,impact_batch,independent_cover_table,policy_digest,reference,verify_operator,world_digest
from generate import make_case
from integration.native_workflow import execute_stages

ROOT = Path(__file__).resolve().parent
_DEMO_ROOT = None

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(canonical(value)+b'\n')
    relative = str(path.relative_to(_DEMO_ROOT)) if _DEMO_ROOT is not None else str(path)
    return {'path':relative,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}

def read_bound(row):
    path = (_DEMO_ROOT/row['path']) if _DEMO_ROOT is not None else Path(row['path'])
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=row['sha256']:
        raise ValueError('stage input changed after acceptance')
    return json.loads(data)

def render_report(path,summary):
    payload = json.dumps(summary,ensure_ascii=True).replace('</','<\\/')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BLOOM ∞ · Every successor must earn its proof</title><style>
:root{color-scheme:dark;--bg:#0b0816;--panel:#171025;--ink:#f3efff;--muted:#bbb1cd;--purple:#b89aff;--green:#8ce5b7;--line:#443352}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,sans-serif}main{max-width:1180px;margin:auto;padding:48px 24px}header{padding:45px 0 35px;border-bottom:1px solid var(--line);background:radial-gradient(ellipse at 78% 20%,#40206766,transparent 58%)}.eyebrow{letter-spacing:.2em;color:var(--purple);font-size:.8rem}h1{font-size:clamp(48px,8vw,95px);line-height:1;margin:15px 0}h2{font-weight:500;font-size:clamp(24px,4vw,40px);line-height:1.2;max-width:850px}p{max-width:850px}.muted{color:var(--muted)}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:15px;margin:28px 0}.card,section{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:22px}.number{font-size:32px;color:var(--green)}.stages{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}.stage{border-left:2px solid var(--purple);padding:15px;background:#21152d}.stage b{color:var(--purple)}select,button{font:inherit;padding:10px 15px;border:1px solid var(--line);border-radius:8px;background:#271a37;color:var(--ink)}table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{border-bottom:1px solid var(--line);padding:12px;text-align:left;vertical-align:top}code{word-break:break-all;font-size:.84rem;color:#d2c3ff}details{margin:16px 0}summary{cursor:pointer;color:var(--purple)}.warning{border-left:3px solid #f6c76e;padding-left:16px}a{color:#cdb4ff}footer{margin-top:36px;color:var(--muted)}.scroll{overflow:auto}button:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #8ce5b7;outline-offset:3px}</style>
<main><header><div class="eyebrow">AGI ALPHA · TRANSFORMATIONAL INTELLIGENCE ∞ · SUCCESSOR Ω</div><h1>BLOOM ∞</h1><h2>Every successor must earn its proof.</h2><p class="muted">A change-impact capability becomes the input to an independently checked coverage plan. Inspect the chosen operator, its exact conditions and the real native execution history.</p></header>
<div class="cards" id="cards"></div><section><h2>From dependency change to a qualified plan</h2><p>Choose a change query to see its affected applications and the successor's minimum-cost coverage plan.</p><label for="query">Change query </label><select id="query"></select><div id="answer"></div><p class="warning">Coverage weights are synthetic. This demonstrates exact supplied-graph reachability and finite coverage, not preserved real-world fault detection or measured test execution.</p></section>
<h2>The connected journey</h2><div class="stages" id="stages"></div><section style="margin-top:24px"><h2>Evidence and boundaries</h2><div id="evidence"></div><details><summary>Inspect complete local receipt</summary><pre style="white-space:pre-wrap;word-break:break-word" id="raw"></pre></details><button id="download">Export this evidence summary</button></section><footer>Local experimental system · No external submission · No financial transaction · Restored history carries no active proof or authority.</footer></main>
<script id="data" type="application/json">__DATA__</script><script>
const d=JSON.parse(document.getElementById('data').textContent);const e=x=>String(x).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
document.getElementById('cards').innerHTML=[['Nodes',d.graph.nodes],['Dependency edges',d.graph.edges],['Qualified operator',d.operator.strategy],['Native stages',d.native.completed_stages.length+'/7']].map(x=>'<div class="card"><div class="muted">'+e(x[0])+'</div><div class="number">'+e(x[1])+'</div></div>').join('');
const q=document.getElementById('query');d.queries.forEach((v,i)=>q.add(new Option((i+1)+'. '+v.join(', '),i)));function show(){const a=d.successor.outputs[+q.value];document.getElementById('answer').innerHTML='<h3>Affected applications</h3><p>'+e(a.affected.join(', ')||'None — terminate normally')+'</p><h3>Successor coverage plan</h3><p>'+e(a.feasible?(a.selected.join(', ')||'No tests required'):'INFEASIBLE — no coverage exists')+'</p><p>Declared synthetic cost: <b>'+e(a.cost===null?'not feasible':a.cost)+'</b></p>';}q.onchange=show;show();
document.getElementById('stages').innerHTML=d.stage_notes.map((x,i)=>'<div class="stage"><b>'+('0'+(i+1)).slice(-2)+' · '+e(x.label)+'</b><p>'+e(x.contribution)+'</p></div>').join('');
document.getElementById('evidence').innerHTML='<p><b>Why this operator:</b> '+e(d.operator.reason)+'</p><p><b>Qualification:</b> '+e(d.operator.qualification)+'</p><p><b>Consumed capability:</b> <code>'+e(d.successor.consumed_operator_sha256)+'</code></p><p><b>Complete native journey:</b> '+e((d.native.total_cpu_ns/1e6).toFixed(2))+' ms CPU; '+e((d.native.total_wall_ns/1e6).toFixed(2))+' ms wall time, including local journal, source checks, execution, backup and restoration.</p><p><b>Restore:</b> stopped; active proofs '+e(d.native.restoration.active_proofs.length)+'; active grants '+e(d.native.restoration.active_grants.length)+'.</p><p class="warning">'+e(d.boundaries.join(' '))+'</p>';
document.getElementById('raw').textContent=JSON.stringify(d,null,2);document.getElementById('download').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(d,null,2)],{type:'application/json'}));a.download='bloom-demo-evidence.json';a.click();URL.revokeObjectURL(a.href)};
</script></html>'''
    path.write_text(page.replace('__DATA__',payload))

def run_demo(output,case_path=None,method='expert'):
    global _DEMO_ROOT
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Choose a new output directory; previous evidence is preserved')
    output.mkdir(parents=True)
    _DEMO_ROOT = output
    case = json.loads(Path(case_path).read_text()) if case_path else make_case(107)
    reference.validate_case(case)
    if any(t['cost']<=0 for t in case['tests']):
        raise ValueError('This experimental policy requires positive test weights')
    case_row = save(output/'case.json',case)
    meter = Meter()
    state = {}
    def identify(inputs):
        return {'case':case_row,'objective':'Exact dependency impact followed by minimum-cost supplied coverage',
            'scope':'public or deterministic nonpersonal graph; no external execution','authority':'none'}
    def learn(inputs):
        binding = inputs['identify']['result']['case']
        observed = read_bound(binding)
        graph = Graph(observed)
        return {'case':binding,'world_sha256':world_digest(observed),'nodes':graph.n,'edges':graph.m,
            'applications':observed['applications'],'limits':'Supplied graph may omit real dependency edges.'}
    def think(inputs):
        prior = inputs['out_learn']['result']
        observed = read_bound(prior['case'])
        options = reference.choose_strategy(observed)
        return {'case':prior['case'],'method':method,'conventional_diagnosis':options,
            'binding_constraint':'repeated impact computation, qualification and retained operator bytes'}
    def design(inputs):
        prior = inputs['out_think']['result']
        observed = read_bound(prior['case'])
        artifact = build_operator(observed,prior['method'],meter)
        row = save(output/'operator.json',artifact)
        state['operator'] = artifact
        return {'case':prior['case'],'operator':row,'strategy':artifact['strategy'],'decisions':meter.decisions}
    def strategise(inputs):
        prior = inputs['out_design']['result']
        observed,artifact = read_bound(prior['case']),read_bound(prior['operator'])
        verdict = meter.call('qualification',verify_operator,observed,artifact,meter)
        state['verdict'] = verdict
        return {'case':prior['case'],'operator':prior['operator'],'qualified':verdict['qualified'],
            'qualification':verdict,'payload_bytes':len(canonical(artifact)),'payload_cap':1048576,
            'world_sha256':world_digest(observed),'policy_sha256':policy_digest(),
            'environment_sha256':environment_digest(),'external_authority':'none'}
    def execute(inputs):
        prior = inputs['out_strategise']['result']
        if not prior['qualified']:
            raise ValueError('operator not qualified')
        observed,artifact = read_bound(prior['case']),read_bound(prior['operator'])
        rows = meter.call('impact_execution',impact_batch,observed,artifact,meter)
        for changed,row in zip(observed.get('queries',[observed['changed']]),rows):
            expected,_ = reference.impact_bfs({**observed,'changed':changed})
            if row['affected']!=expected:
                raise ValueError('impact failed independent final check')
        return {'case':prior['case'],'operator':prior['operator'],'impact':save(output/'impact.json',rows),
                'qualified':True,'consumed_operator_sha256':digest(artifact)}
    def evolve(inputs):
        prior = inputs['out_execute']['result']
        observed,impact = read_bound(prior['case']),read_bound(prior['impact'])
        table = meter.call('successor_construction',coverage_table,observed,meter)
        independent = meter.call('successor_qualification',independent_cover_table,observed)
        if table!=independent:
            raise ValueError('successor failed independent optimum check')
        outputs = [{'affected':r['affected'],**table[r['mask']]} for r in impact]
        successor = {'schema':'bloom-coverage-successor/v1','outputs':outputs,
            'consumed_impact_sha256':prior['impact']['sha256'],'consumed_operator_sha256':prior['consumed_operator_sha256'],
            'own_qualification':'independent exhaustive subset optimum','terminal':'plan exported; no tests executed',
            'financial_status':'no revenue, offer, transaction or execution authority'}
        state['successor'] = successor
        return {'successor':save(output/'successor.json',successor),'qualified':True,
                'next_action':'Review the graph and coverage assumptions before any real test scheduling.'}
    def accepts(artifact):
        return artifact['result'].get('qualified',True) is True
    labels = ['Identify','Out-Learn','Out-Think','Out-Design','Out-Strategise','Out-Execute','Out-Evolve']
    ids = ['identify','out_learn','out_think','out_design','out_strategise','out_execute','out_evolve']
    handlers = [identify,learn,think,design,strategise,execute,evolve]
    stages = [{'id':i,'label':label,'handler':handler,'accept':accepts} for i,label,handler in zip(ids,labels,handlers)]
    source_paths = [ROOT/f for f in ['demo.py','core.py','generate.py','independent/reference.py','integration/native_workflow.py']]
    native = execute_stages(output/'native',stages,mission_id='bloom-dependency-demo-v1',
        objective='Construct qualified impact capacity and use it in an independently checked coverage successor.',
        source_paths=source_paths,bindings={'execution_mode':'synthetic-local','authority':'none','case_sha256':digest(case)})
    if native['receipt']['status']!='completed':
        raise RuntimeError('native journey stopped; inspect native receipt')
    notes = ['Bind the declared graph, user purpose and authority ceiling.',
        'Parse actual dependency direction and expose observability limits.',
        'Compare conventional alternatives against the known query workload.',
        'Construct the chosen graph-specific operator and its certificate.',
        'Independently check exactness, source, world, policy and byte budget.',
        'Execute impact queries and export their independently checked answers.',
        'Consume those answers to construct and verify a distinct coverage plan, then stop.']
    summary = {'title':'BLOOM∞ — Every successor must earn its proof','graph':{'nodes':len(case['nodes']),'edges':len(case['edges'])},
        'queries':case.get('queries',[case['changed']]),'operator':{'strategy':state['operator']['strategy'],
            'reason':meter.decisions[0]['reason'],'qualification':state['verdict']['reason']},
        'successor':state['successor'],'native':native['receipt'],'kernel_metrics':{'phases':meter.phases,'counters':meter.counters},
        'stage_notes':[{'label':label,'contribution':note} for label,note in zip(labels,notes)],
        'boundaries':['Alpha native local dispatcher executed with public test signing material.',
            'Manager/Jobs finite native semantic admission and Fleet external execution are not connected for this new task.',
            'Five Alpha contracts are source-audited; local EVM execution is NOT_RUN because dependencies are absent.',
            'Synthetic coverage weights and zero cash revenue do not establish a profitable enterprise.']}
    save(output/'summary.json',summary)
    render_report(output/'index.html',summary)
    print(json.dumps({'demo':'completed','native_stages':len(native['receipt']['completed_stages']),
        'operator':state['operator']['strategy'],'report':str(output/'index.html'),'authority':'none'}))
    return summary

if __name__ == '__main__':
    p=argparse.ArgumentParser(description='One-command offline BLOOM journey through the actual Alpha dispatcher.')
    p.add_argument('--output',default='runs/bloom-demo')
    p.add_argument('--case',help='optional supplied case JSON; default is deterministic development fixture107')
    p.add_argument('--method',choices=['bloom','expert','reverse'],default='expert')
    a=p.parse_args()
    run_demo(a.output,a.case,a.method)
