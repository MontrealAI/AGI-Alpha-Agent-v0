import argparse,gzip,hashlib,importlib,json,os,random,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import conventional,reference_oracle


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def specs_for(seed,n):
    rng=random.Random(seed); specs=[]
    for index in range(n):
        ps=[]
        for j in range(1+index%4):
            a,b,c,v=rng.sample(range(8),4);u1=rng.randint(1,8);u2=rng.randint(1,20-u1);l1=rng.randint(1,u1);l2=rng.randint(1,u2);d=rng.randint(u1+u2,20)
            ps.append(dict(name=f'p{j}',a=a,b=b,c=c,veto=v,l1=l1,u1=u1,l2=l2,u2=u2,deadline=d))
        specs.append(ps)
    return specs

def traces_for(spec,seed,n=32,ticks=256):
    rng=random.Random(seed);result=[]
    for k in range(n):
        density=[.03,.10,.25,.65][k%4]
        rows=[{'events':sum((rng.random()<density)<<j for j in range(8)),'rst':False} for _ in range(ticks)]
        rows[0]={'events':255,'rst':True}
        for r in [ticks//2,ticks-24]:
            if k%3==0:rows[r]={'events':rng.randrange(256),'rst':True}
        if k%4<3:
            p=spec[k%len(spec)];a=5;b=a+(p['l1'] if k%2 else p['u1']);c=b+(p['l2'] if k%2 else p['u2'])
            for t in range(1,1+max(x['deadline'] for x in spec)+25):rows[t]={'events':0,'rst':False}
            rows[a]['events']|=1<<p['a'];rows[b]['events']|=1<<p['b'];rows[c]['events']|=1<<p['c']
            if k%4==2:rows[a+p['deadline']]['events']|=1<<p['veto']
        result.append(rows)
    return result

def directed_cases():
    spec=json.loads((ROOT/'protocol/technical_v1.json').read_text())['first_demo'];cases=[]
    def one(name,events,resets=(),sp=spec):
        rows=[{'events':events.get(t,0),'rst':t in resets} for t in range(40)];cases.append({'name':name,'spec':sp,'trace':rows})
    for i,p in enumerate(spec):
        for b_lag in sorted({p['l1'],p['u1']}):
            for c_lag in sorted({p['l2'],p['u2']}):
                a=2;b=a+b_lag;c=b+c_lag
                ev={a:1<<p['a'],b:1<<p['b'],c:1<<p['c']}
                one(f'p{i}_inclusive_{b_lag}_{c_lag}',ev,[0])
                for vt in [a,a+p['deadline']-1,a+p['deadline']]:
                    ve=dict(ev);ve[vt]=ve.get(vt,0)|(1<<p['veto']);one(f'p{i}_veto_{b_lag}_{c_lag}_{vt}',ve,[0])
        p1=dict(p);p1['name']='tight';p1['l1']=p1['u1']=2;p1['l2']=p1['u2']=2;p1['deadline']=6
        for bl,cl in [(1,2),(3,2),(2,1),(2,3),(2,2)]:
            ev={2:1<<p1['a'],2+bl:1<<p1['b'],2+bl+cl:1<<p1['c']};one(f'tight_lags_{i}_{bl}_{cl}',ev,[0],[p1])
    one('all_channels_simultaneous',{t:255 for t in range(1,25)},[0])
    one('group_isolation_missing_B',{2:1,3:32,4:4},[0])
    one('reset_cancels_pending',{2:1,3:2,4:4},[0,5])
    one('reset_dominates_complete_mask',{2:255,3:2,4:4},[0,2])
    one('post_reset_clean_match',{2:1,3:2,4:4,8:1,9:2,10:4},[0,5])
    one('overlapping_anchors',{2:1,3:3,4:6,5:4},[0])
    one('multiple_paths_single_pulse',{2:1,3:2,4:6,5:6,6:4},[0])
    one('zero_masks_advance_time',{2:1,3:2,4:4},[0])
    one('irrelevant_channels',{2:129,3:130,4:132},[0])
    shared=[dict(spec[0]),dict(spec[0],name='shared_different_bound',l1=2,u1=2,l2=2,u2=2,deadline=9)]
    one('shared_channels_independent_deadlines',{2:1,4:2,6:4},[0],shared)
    return cases

def invalid_specs():
    p=json.loads((ROOT/'protocol/technical_v1.json').read_text())['first_demo'][0]
    return [[],[p]*5,[p,p],[dict(p,l1=0)],[dict(p,a=8)],[dict(p,b=p['a'])],[dict(p,l2=-1)],[dict(p,deadline=21)],[dict(p,u1=9,deadline=7)],[dict(p,l1=True)],[dict(p,l1='1')],[dict(p,unknown=1)],{k:v for k,v in p.items() if k!='c'},{'channels':9,'patterns':[p]}]

def timed_run(fn,spec,trace):
    wall=time.perf_counter();cpu=time.process_time();out=fn(spec,trace);return out,{'wall_s':time.perf_counter()-wall,'cpu_s':time.process_time()-cpu}

def command(args,outfile,timeout=180):
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'.deps')+os.pathsep+env.get('PYTHONPATH','');env['YOWASP_CACHE_DIR']=str(ROOT/'.cache/yowasp')
    start=time.perf_counter();r=subprocess.run(args,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout);Path(outfile).write_text(r.stdout)
    if r.returncode:raise RuntimeError(f'Command failed {r.returncode}; preserved log {outfile}')
    return time.perf_counter()-start

def yosys(script,log,timeout=180):return command([sys.executable,'-c','import yowasp_yosys; yowasp_yosys._run_yosys_argv()','-Q','-T','-p',script],log,timeout)

def ew_verilog(spec):
    m=importlib.import_module('eventweaver');obj=m.compile_spec(spec)
    if isinstance(obj,dict):
        for key in ['verilog','rtl']:
            if key in obj:return obj[key]
    for key in ['verilog','rtl']:
        if hasattr(obj,key):
            v=getattr(obj,key);return v() if callable(v) else v
    if hasattr(m,'verilog'):return m.verilog(spec)
    if hasattr(m,'emit_verilog'):return m.emit_verilog(spec)
    raise TypeError('No recognized EventWeaver RTL return')

def build_rtl(spec,folder,proof=True):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);n=len(spec);d=max(p['deadline'] for p in spec)
    (folder/'eventweaver.v').write_text(ew_verilog(spec));(folder/'conventional.v').write_text(conventional.emit_verilog(spec))
    wrapper=f'''module comparison(input wire clk,input wire rst,input wire[7:0] events,output wire[{n-1}:0] ew,output wire[{n-1}:0] cv,output wire eq);
eventweaver a(clk,rst,events,ew);
conventional b(clk,rst,events,cv);
assign eq=(ew==cv);
endmodule
'''
    (folder/'comparison.v').write_text(wrapper);rel=str(folder.relative_to(ROOT));read=f'read_verilog {rel}/eventweaver.v {rel}/conventional.v {rel}/comparison.v; hierarchy -top comparison; '
    metrics={'cxxrtl_generation_s':yosys(read+f'proc; opt; check -assert; write_cxxrtl -g0 {rel}/model.cc',folder/'cxxrtl.log')}
    driver='#include "model.cc"\n#include <iostream>\nint main(){cxxrtl_design::p_comparison top; top.step();unsigned e,r;while(std::cin>>r>>e){top.p_clk.set(false);top.p_rst.set(r);top.p_events.set(e);top.step();top.p_clk.set(true);top.step();std::cout<<top.p_ew.get<unsigned>()<<" "<<top.p_cv.get<unsigned>()<<"\\n";}return 0;}\n'
    (folder/'driver.cc').write_text(driver);include=ROOT/'.deps/yowasp_yosys/share/include/backends/cxxrtl/runtime'
    metrics['cxxrtl_native_compile_s']=command(['g++','-std=c++17','-O2','-I',str(include),str(folder/'driver.cc'),'-o',str(folder/'rtl_sim')],folder/'cpp.log')
    if proof:
        metrics['bounded_equivalence_depth']=d+2
        metrics['bounded_equivalence_s']=yosys(read+f'prep -top comparison -flatten; memory_map; opt; sat -seq {d+2} -set-at 1 rst 1 -prove-skip 1 -prove eq 1 -verify -set-def-inputs -show-inputs -show-outputs',folder/'equivalence.log')
        metrics['proof_status']='PASS' if 'SUCCESS!' in (folder/'equivalence.log').read_text() else 'UNRECOGNIZED'
        if metrics['proof_status']!='PASS':raise RuntimeError('No explicit proof success marker')
    return metrics

def run_rtl(folder,traces):
    rows=[]
    for trace in traces:
        rows.append('1 0')
        for row in trace:
            ev,rst=conventional.sample(row);rows.append(f'{int(rst)} {ev}')
    start=time.perf_counter();r=subprocess.run([str(Path(folder)/'rtl_sim')],input='\n'.join(rows)+'\n',text=True,capture_output=True,check=True);wall=time.perf_counter()-start
    pairs=[tuple(map(int,line.split())) for line in r.stdout.splitlines()];result=[];offset=0
    for trace in traces:
        offset+=1;chunk=pairs[offset:offset+len(trace)];offset+=len(trace);result.append(([x[0] for x in chunk],[x[1] for x in chunk]))
    if offset!=len(pairs):raise ValueError('RTL trace length mismatch')
    return result,wall

def run_campaign(mode,seed=None,rtl=False,proof=False):
    ew=importlib.import_module('eventweaver');outdir=ROOT/'results'/('technical_'+mode);outdir.mkdir(parents=True,exist_ok=True);records=[];metrics=[];failures=[];invalid=[]
    if mode=='confirmation':
        if seed is None:raise ValueError('Fresh seed required after freeze')
        lock=ROOT/'protocol/development_freeze.json'
        if not lock.exists():raise RuntimeError('No development freeze; refusing fresh confirmation')
        n=24;count=32;specs=specs_for(seed,n);seeds=[seed+100003*i for i in range(n)]
    else:
        prescribed=json.loads((ROOT/'protocol/technical_v1.json').read_text())['development_seeds'];specs=[specs_for(s,4)[i] for i,s in enumerate(prescribed)];seeds=prescribed;count=8
    (outdir/'specifications.json').write_text(json.dumps({'mode':mode,'seed':seed,'specs':specs,'trace_seeds':seeds},indent=2))
    for i,(spec,s) in enumerate(zip(specs,seeds)):
        traces=traces_for(spec,s,count);group={'spec_index':i,'patterns':len(spec),'traces':len(traces),'ticks_per_trace':256,'seed':s}
        folder=outdir/f'spec_{i:02d}'
        if rtl:
            group.update(build_rtl(spec,folder,proof));rtl_out,rt=run_rtl(folder,traces);group['rtl_run_wall_s']=rt
        totals={key:0. for key in ['oracle_wall_s','conventional_wall_s','eventweaver_wall_s']}
        for k,trace in enumerate(traces):
            expected,t=timed_run(reference_oracle.run,spec,trace);totals['oracle_wall_s']+=t['wall_s'];cv,t=timed_run(conventional.run,spec,trace);totals['conventional_wall_s']+=t['wall_s'];actual,t=timed_run(ew.run,spec,trace);totals['eventweaver_wall_s']+=t['wall_s']
            pass_now=expected==cv==actual;rec={'spec_index':i,'trace_index':k,'trace':trace,'oracle':expected,'conventional':cv,'eventweaver':actual}
            if rtl:
                er,cr=rtl_out[k];rec.update(eventweaver_rtl=er,conventional_rtl=cr);pass_now=pass_now and er==cr==expected
            rec['pass']=pass_now;records.append(rec)
            if not pass_now:failures.append({'spec_index':i,'trace_index':k,'record_index':len(records)-1})
        group.update(totals);group['accepted_traces']=sum(r['pass'] for r in records if r['spec_index']==i);metrics.append(group)
        (outdir/'progress.json').write_text(json.dumps(metrics,indent=2))
    directed=[]
    for case in directed_cases():
        expected=reference_oracle.run(case['spec'],case['trace']);cv=conventional.run(case['spec'],case['trace']);actual=ew.run(case['spec'],case['trace']);ok=expected==cv==actual;directed.append(dict(case,oracle=expected,conventional=cv,eventweaver=actual,pass_test=ok))
        if not ok:failures.append({'directed_case':case['name']})
    for i,spec in enumerate(invalid_specs()):
        row={'index':i,'spec':spec}
        for name,func in [('conventional',conventional.compile_spec),('eventweaver',ew.compile_spec)]:
            try:func(spec);row[name]='ACCEPTED_INVALID'
            except (ValueError,TypeError,KeyError,AssertionError):row[name]='REJECTED'
        if any(row[k]!='REJECTED' for k in ['conventional','eventweaver']):failures.append({'invalid_case':i,'result':row})
        invalid.append(row)
    packed='\n'.join(json.dumps(r,separators=(',',':'),sort_keys=True) for r in records)+'\n';(outdir/'traces.jsonl.gz').write_bytes(gzip.compress(packed.encode(),mtime=0));(outdir/'directed.json').write_text(json.dumps(directed,indent=2));(outdir/'invalid.json').write_text(json.dumps(invalid,indent=2));(outdir/'failures.json').write_text(json.dumps(failures,indent=2))
    sources={str(p.relative_to(ROOT)):{'sha256':digest(p),'bytes':p.stat().st_size,'lines':len(p.read_text().splitlines())} for p in [ROOT/'src/conventional.py',ROOT/'src/reference_oracle.py',ROOT/'src/eventweaver.py',Path(__file__)]}
    summary={'mode':mode,'seed':seed,'specifications':len(specs),'traces':len(records),'ticks':sum(len(r['trace']) for r in records),'predicate_tick_decisions':sum(len(r['trace'])*len(specs[r['spec_index']]) for r in records),'accepted_traces':sum(r['pass'] for r in records),'positive_predicate_outputs':sum(x.bit_count() for r in records for x in r['oracle']),'directed_cases':len(directed),'invalid_specs':len(invalid),'failures':failures,'rtl_executed':rtl,'bounded_proofs_executed':proof,'metrics':metrics,'source_metrics':sources,'scope':'Functional logical-bin semantics only; no physical hardware, timing or calibration. Independent AI-assisted comparator, not a human study.'}
    (outdir/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k not in ['metrics','source_metrics']},indent=2));return summary

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['development','confirmation'],default='development');ap.add_argument('--seed',type=int);ap.add_argument('--rtl',action='store_true');ap.add_argument('--proof',action='store_true');a=ap.parse_args();summary=run_campaign(a.mode,a.seed,a.rtl,a.proof)
    if summary['failures']:sys.exit(1)

if __name__=='__main__':main()
