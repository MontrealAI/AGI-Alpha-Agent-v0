"""Frozen, postconfirmation operator counterfactuals; no product-source mutations."""
import argparse, datetime, hashlib, json, pathlib, subprocess, sys, traceback
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'audit'))
import eventweaver, successor, conventional, conventional_network, reference_oracle
import technical_verifier as tv
import successor_verifier as sv
PROTOCOL=ROOT/'protocol/kernel_ablation_v1.json'
FREEZE=ROOT/'protocol/kernel_ablation_freeze.json'
ROLES=('a','b','c','veto')
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def nonzero(outputs):return [{'tick':i,'mask':v} for i,v in enumerate(outputs) if v]
def early(spec,trace):
    out=[];accepted=[set() for p in spec];history=[];last_reset=-1
    for t,row in enumerate(trace):
        mask,rst=eventweaver.sample(row);history.append(mask);value=0
        if rst:
            last_reset=t;accepted=[set() for p in spec];out.append(0);continue
        for j,p in enumerate(spec):
            if not mask&(1<<p['c']):continue
            for a in range(max(last_reset+1,t-p['deadline']),t-p['l1']-p['l2']+1):
                if a in accepted[j] or not history[a]&(1<<p['a']):continue
                if any(history[k]&(1<<p['veto']) for k in range(a,t+1)):continue
                if any(p['l2']<=t-b<=p['u2'] and history[b]&(1<<p['b']) for b in range(a+p['l1'],min(t,a+p['u1'])+1)):
                    accepted[j].add(a);value|=1<<j
        out.append(value)
    return out

def pooled(spec,trace):
    sources=[sorted(set(p[r] for p in spec)) for r in ROLES]
    rows=[]
    for row in trace:
        raw,rst=eventweaver.sample(row)
        rows.append({'events':sum(any(raw&(1<<i) for i in channels)<<k for k,channels in enumerate(sources)),'rst':rst})
    local=[dict(p,**dict(zip(ROLES,range(4)))) for p in spec]
    return eventweaver.run(local,rows)

def disconnected(spec,trace):
    local,bindings=successor.validate(spec);engines=[eventweaver.Engine([p]) for p in local];out=[]
    for row in trace:
        raw,rst=eventweaver.sample(row);value=0
        for j,(engine,refs) in enumerate(zip(engines,bindings)):
            mask=sum((((raw>>i)&1) if kind=='raw' else 0)<<k for k,(kind,i) in enumerate(refs))
            value|=engine.step(mask,rst)<<j
        out.append(value)
    return out

def expression(rule):
    terms=['('+' & '.join(f'{"state" if kind=="state" else "events"}[{i}]' for kind,i in term)+')' for term in rule['any']]
    return f'(~events[{rule["veto"]}] & ('+(' | '.join(terms) or "1'b0")+'))'

def early_rtl(spec):
    ir=eventweaver.compile_spec(spec);n=len(ir['states']);w=len(spec)
    lines=[f'module early_accept(input wire clk,input wire rst,input wire[7:0] events,output reg[{w-1}:0] out);',f'reg[{n-1}:0] state;',f'always @(posedge clk) begin if(rst) begin state <= {n}\'b0; out <= {w}\'b0; end else begin']
    for i,rule in enumerate(ir['transitions']):lines.append(f'state[{i}] <= {expression(rule)};')
    lookup={(s['pattern'],s['coordinates'][0]):i for i,s in enumerate(ir['states']) if s['kind']=='matched'}
    for j in range(w):
        terms=[]
        for (pattern,age),idx in lookup.items():
            if pattern!=j:continue
            previous=lookup.get((j,age-1));exclusion=f' & ~state[{previous}]' if previous is not None else ''
            terms.append(f'({expression(ir["transitions"][idx])}{exclusion})')
        lines.append(f'out[{j}] <= '+(' | '.join(terms) or "1'b0")+';')
    return '\n'.join(lines+['end end','endmodule',''])

def pooled_rtl(spec):
    local=[dict(p,**dict(zip(ROLES,range(4)))) for p in spec]
    lines=[eventweaver.verilog(local,'pooled_core'),f'module pooled_groups(input wire clk,input wire rst,input wire[7:0] events,output wire[{len(spec)-1}:0] out);','wire[7:0] pooled; assign pooled[7:4]=0;']
    for k,r in enumerate(ROLES):lines.append(f'assign pooled[{k}] = '+' | '.join(f'events[{i}]' for i in sorted(set(p[r] for p in spec)))+';')
    return '\n'.join(lines+['pooled_core core(clk,rst,pooled,out);','endmodule',''])

def disconnected_rtl(spec):
    code=successor.verilog(spec,'disconnected');_,bindings=successor.validate(spec)
    for j,refs in enumerate(bindings):
        for k,(kind,index) in enumerate(refs):
            if kind=='stage':
                old=f'assign local_{j}[{k}] = out[{index}];';new=f"assign local_{j}[{k}] = 1'b0;"
                if code.count(old)!=1:raise ValueError('Unexpected virtual-wire rendering')
                code=code.replace(old,new)
    return code

def build_mutants(spec,network,folder):
    folder.mkdir(parents=True,exist_ok=True)
    code=early_rtl(spec)+pooled_rtl(spec)+disconnected_rtl(network)
    code+='module ablation_mutants(input wire clk,input wire rst,input wire[7:0] events,output wire[5:0] out);\nearly_accept a(clk,rst,events,out[1:0]);\npooled_groups b(clk,rst,events,out[3:2]);\ndisconnected c(clk,rst,events,out[5:4]);\nendmodule\n'
    (folder/'mutants.v').write_text(code);rel=str(folder.relative_to(ROOT))
    elapsed=tv.yosys(f'read_verilog {rel}/mutants.v; hierarchy -top ablation_mutants; proc; opt; check -assert; write_cxxrtl -g0 {rel}/model.cc',folder/'cxxrtl.log')
    (folder/'driver.cc').write_text('#include "model.cc"\n#include <iostream>\nint main(){cxxrtl_design::p_ablation__mutants top;top.step();unsigned r,e;while(std::cin>>r>>e){top.p_clk.set(false);top.p_rst.set(r);top.p_events.set(e);top.step();top.p_clk.set(true);top.step();top.step();std::cout<<top.p_out.get<unsigned>()<<"\\n";}return 0;}\n')
    inc=ROOT/'.deps/yowasp_yosys/share/include/backends/cxxrtl/runtime'
    compiled=tv.command(['g++','-std=c++17','-O2','-I',str(inc),str(folder/'driver.cc'),'-o',str(folder/'rtl_sim')],folder/'cpp.log')
    return {'cxxrtl_generation_s':elapsed,'native_compile_s':compiled,'rtl_sha256':sha(folder/'mutants.v'),'validation':'Yosys check -assert and CXXRTL execution; these mutants intentionally violate the full contract, and no equivalence claim is made.'}

def run_mutants(folder,traces):
    rows=[]
    for trace in traces:
        rows.append('1 0')
        for row in trace:
            raw,rst=eventweaver.sample(row);rows.append(f'{int(rst)} {raw}')
    r=subprocess.run([str(folder/'rtl_sim')],input='\n'.join(rows)+'\n',text=True,capture_output=True,check=True)
    values=[int(x) for x in r.stdout.splitlines()];out=[];offset=0
    for trace in traces:
        offset+=1;out.append(values[offset:offset+len(trace)]);offset+=len(trace)
    if offset!=len(values):raise ValueError('Mutant RTL output length mismatch')
    return out

def freeze():
    if FREEZE.exists():raise RuntimeError('Refusing to overwrite existing freeze')
    data={'schema':'kernel.ablation.freeze.v1','frozen_at_utc':now(),'protocol_sha256':sha(PROTOCOL),'implementation_sha256':sha(__file__),'run_started':False}
    FREEZE.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data,indent=2))

def run():
    frozen=json.loads(FREEZE.read_text());protocol=json.loads(PROTOCOL.read_text())
    if frozen['protocol_sha256']!=sha(PROTOCOL) or frozen['implementation_sha256']!=sha(__file__):raise RuntimeError('Ablation freeze changed')
    for name,expected in protocol['frozen_dependency_sha256'].items():
        if sha(ROOT/name)!=expected:raise RuntimeError(f'Frozen dependency changed: {name}')
    destination=ROOT/'results/kernel_ablation.json'
    if destination.exists():raise RuntimeError('Refusing to overwrite an existing result; preserve failure and declare amendment')
    report={'schema':'kernel.ablation.results.v1','started_at_utc':now(),'freeze':frozen,'status':'RUNNING','errors':[],'cases':[],'interpretation':{'operator_necessity':'Selected traces require delayed veto, isolated groups and the virtual-event link to satisfy their specified contracts. Removing those capabilities changes an accepted or rejected outcome.','compiler_necessity':'Our compiler is not necessary. An independently implemented conventional RTL design can deliver the same outcomes.','commercial_inference':'No new commercial feasibility, exclusive novelty, expert-agent advantage or willingness to pay is established by these selected semantic counterexamples. The study supports an implemented functional construction, with a conventional alternative.'}}
    folder=ROOT/'results/kernel_ablation';folder.mkdir(parents=True,exist_ok=True)
    try:
        spec=protocol['baseline_patterns'];network=protocol['successor_spec'];fixtures=protocol['fixtures']
        report['baseline_build']=tv.build_rtl(spec,folder/'baseline',proof=False)
        report['successor_build']=sv.build(network,folder/'successor')
        report['mutant_build']=build_mutants(spec,network,folder/'mutants')
        base,_=tv.run_rtl(folder/'baseline',[f['trace'] for f in fixtures[:4]])
        networks,_=tv.run_rtl(folder/'successor',[f['trace'] for f in fixtures[4:]])
        mutant_outputs=run_mutants(folder/'mutants',[f['trace'] for f in fixtures])
        shifts={'delayed_veto':0,'group_isolation':2,'virtual_link':4}
        for i,f in enumerate(fixtures):
            is_network=f['operator_removed']=='virtual_link';trace=f['trace']
            if is_network:
                ours=successor.run(network,trace);cv=conventional_network.run(network,trace);oracle=conventional_network.oracle(network,trace);rtl,cv_rtl=networks[i-4]
                mutant=disconnected(network,trace)
            else:
                ours=eventweaver.run(spec,trace);cv=conventional.run(spec,trace);oracle=reference_oracle.run(spec,trace);rtl,cv_rtl=base[i]
                mutant=(early if f['operator_removed']=='delayed_veto' else pooled)(spec,trace)
            mutant_rtl=[(v>>shifts[f['operator_removed']])&3 for v in mutant_outputs[i]]
            checks={'full_python_oracle_rtl_match':ours==cv==oracle==rtl==cv_rtl,'full_expected_match':nonzero(ours)==f['expected_full_nonzero'],'mutant_python_rtl_match':mutant==mutant_rtl,'mutant_expected_match':nonzero(mutant)==f['expected_ablation_nonzero'],'our_compiler_removed_conventional_rtl_tie':rtl==cv_rtl}
            case={'name':f['name'],'operator_removed':f['operator_removed'],'checks':checks,'full_nonzero':nonzero(ours),'mutant_nonzero':nonzero(mutant),'full_outputs':ours,'mutant_outputs':mutant,'conventional_rtl_outputs':cv_rtl,'mutant_rtl_outputs':mutant_rtl,'contract_discrepancies':[{'tick':t,'full':a,'ablated':b} for t,(a,b) in enumerate(zip(ours,mutant)) if a!=b]}
            report['cases'].append(case)
            if not all(checks.values()):report['errors'].append({'fixture':f['name'],'failed_checks':[k for k,v in checks.items() if not v]})
        report['all_frozen_sources_unchanged']=all(sha(ROOT/name)==expected for name,expected in protocol['frozen_dependency_sha256'].items())
        report['summary']={'fixtures':len(fixtures),'ticks':sum(len(f['trace']) for f in fixtures),'unexpected_errors':len(report['errors']),'compiler_removal_ties':sum(c['checks']['our_compiler_removed_conventional_rtl_tie'] for c in report['cases']),'intended_counterexamples':[c['name'] for c in report['cases'] if c['contract_discrepancies']]}
        report['status']='PASS' if not report['errors'] and report['all_frozen_sources_unchanged'] else 'FAIL'
    except Exception as exc:
        report['status']='FAIL';report['errors'].append({'exception':str(exc),'traceback':traceback.format_exc()})
    report['finished_at_utc']=now();destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','errors','summary') if k in report},indent=2))
    if report['status']!='PASS':sys.exit(1)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['freeze','run']);args=parser.parse_args()
    (freeze if args.action=='freeze' else run)()
