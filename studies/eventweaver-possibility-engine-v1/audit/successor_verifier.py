import argparse,gzip,hashlib,importlib,json,os,random,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'audit'))
import conventional_network,conventional,reference_oracle,successor,eventweaver
from technical_verifier import command,yosys,run_rtl,digest


def network_specs(seed,n):
    rng=random.Random(seed);out=[]
    for i in range(n):
        stages=[]
        for j in range(2+i%3):
            refs=[f'raw:{x}' for x in rng.sample(range(8),4)] if j==0 else [f'stage:s{j-1}']+[f'raw:{x}' for x in rng.sample(range(8),3)]
            u1=rng.randint(1,4);u2=rng.randint(1,4);l1=rng.randint(1,u1);l2=rng.randint(1,u2)
            stages.append(dict(name=f's{j}',**dict(zip(('a','b','c','veto'),refs)),l1=l1,u1=u1,l2=l2,u2=u2,deadline=u1+u2+rng.randint(0,3)))
        if i%2:stages.reverse()
        out.append({'channels':8,'stages':stages})
    return out

def network_traces(spec,seed,n=8,ticks=128):
    rng=random.Random(seed);stages,order=conventional_network.normalize(spec);lookup={p['name']:p for p in stages};out=[]
    for i in range(n):
        rows=[{'events':sum((rng.random()<[.025,.1,.25,.5][i%4])<<b for b in range(8)),'rst':False} for _ in range(ticks)];rows[0]={'events':255,'rst':True}
        if i%2==0:
            for row in rows[1:100]:row['events']=0
            decisions={}
            for name in order:
                p=lookup[name];anchor=2 if p['a'].startswith('raw:') else decisions[p['a'][6:]]+1
                if p['a'].startswith('raw:'):rows[anchor]['events']|=1<<int(p['a'][4:])
                b=anchor+p['l1'];c=b+p['l2'];rows[b]['events']|=1<<int(p['b'][4:]);rows[c]['events']|=1<<int(p['c'][4:]);decisions[name]=anchor+p['deadline']
            if i==2:
                last=lookup[order[-1]];rows[decisions[order[-1]]]['events']|=1<<int(last['veto'][4:])
            if i==4:rows[decisions[order[0]]+1]['rst']=True
        else:
            if i%3==0:rows[64]['rst']=True
        out.append(rows)
    return out

def directed():
    spec=json.loads((ROOT/'protocol/successor_v1.json').read_text())['development_demo'];rows=[{'events':0,'rst':False} for _ in range(40)];rows[0]['rst']=True
    for t,e in [(2,1),(3,2),(4,4),(11,16),(12,32)]:rows[t]['events']=e
    cases=[{'name':'one_interface_tick','spec':spec,'trace':rows,'expected':{9:1,15:2}}]
    for name,t,kind in [('late_veto',15,'veto'),('consumer_anchor_reset',10,'reset'),('producer_decision_reset',9,'reset')]:
        tr=[dict(x) for x in rows]
        if kind=='veto':tr[t]['events']|=64
        else:tr[t]['rst']=True
        cases.append({'name':name,'spec':spec,'trace':tr,'expected':{9:1} if t!=9 else {}})
    rev={'channels':8,'stages':list(reversed(spec['stages']))};cases.append({'name':'non_topological_order','spec':rev,'trace':rows,'expected':{9:2,15:1}})
    def rowset(events):
        tr=[{'events':events.get(t,0),'rst':t==0} for t in range(40)];return tr
    for role,refs,ev,expected in [
        ('B',{'a':'raw:4','b':'stage:heralded_probe','c':'raw:5','veto':'raw:6'},{2:1,3:2,4:4,8:16,11:32},{9:1,13:2}),
        ('C',{'a':'raw:4','b':'raw:5','c':'stage:heralded_probe','veto':'raw:6'},{2:1,3:2,4:4,7:16,8:32},{9:1,12:2}),
        ('veto',{'a':'raw:4','b':'raw:5','c':'raw:6','veto':'stage:heralded_probe'},{2:1,3:2,4:4,7:16,8:32,9:64},{9:1}),
        ('veto_control',{'a':'raw:4','b':'raw:5','c':'raw:6','veto':'stage:heralded_probe'},{7:16,8:32,9:64},{12:2})]:
        sp=json.loads(json.dumps(spec));sp['stages'][1].update(refs);cases.append({'name':'virtual_'+role,'spec':sp,'trace':rowset(ev),'expected':expected})
    chain=json.loads(json.dumps(spec));chain['stages'].append(dict(name='third',a='stage:conditioned_calibration',b='raw:0',c='raw:1',veto='raw:2',l1=1,u1=1,l2=1,u2=1,deadline=3));tr=[dict(x) for x in rows];tr[17]['events']=1;tr[18]['events']=2
    cases.append({'name':'three_stage_chain','spec':chain,'trace':tr,'expected':{9:1,15:2,19:4}})
    return cases

def invalid():
    spec=json.loads((ROOT/'protocol/successor_v1.json').read_text())['development_demo'];bad=[]
    for field,value in [('a','stage:missing'),('a','stage:heralded_probe'),('a','raw:8'),('a','raw:00'),('b','raw:0')]:
        x=json.loads(json.dumps(spec));x['stages'][0][field]=value;bad.append(x)
    x=json.loads(json.dumps(spec));x['stages'][0]['a']='stage:conditioned_calibration';bad.append(x)
    x=json.loads(json.dumps(spec));x['stages'][1]['name']='heralded_probe';bad.append(x)
    bad.extend([{'channels':8,'stages':[]},{'channels':9,'stages':spec['stages']}]);return bad

def build(spec,folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);n=len(spec['stages']);depth=sum(p['deadline']+1 for p in spec['stages'])+2
    (folder/'successor.v').write_text(successor.verilog(spec));(folder/'conventional_network.v').write_text(conventional_network.verilog(spec))
    (folder/'comparison.v').write_text(f'module comparison(input wire clk,input wire rst,input wire[7:0] events,output wire[{n-1}:0] ew,output wire[{n-1}:0] cv,output wire eq);\nsuccessor a(clk,rst,events,ew);\nconventional_network b(clk,rst,events,cv);\nassign eq=(ew==cv);\nendmodule\n')
    rel=str(folder.relative_to(ROOT));read=f'read_verilog {rel}/successor.v {rel}/conventional_network.v {rel}/comparison.v; hierarchy -top comparison; '
    metrics={'cxxrtl_generation_s':yosys(read+f'proc; opt; check -assert; write_cxxrtl -g0 {rel}/model.cc',folder/'cxxrtl.log')}
    (folder/'driver.cc').write_text('#include "model.cc"\n#include <iostream>\nint main(){cxxrtl_design::p_comparison top;top.step();unsigned e,r;while(std::cin>>r>>e){top.p_clk.set(false);top.p_rst.set(r);top.p_events.set(e);top.step();top.p_clk.set(true);top.step();top.step();std::cout<<top.p_ew.get<unsigned>()<<" "<<top.p_cv.get<unsigned>()<<"\\n";}return 0;}\n')
    inc=ROOT/'.deps/yowasp_yosys/share/include/backends/cxxrtl/runtime';metrics['native_compile_s']=command(['g++','-std=c++17','-O2','-I',str(inc),str(folder/'driver.cc'),'-o',str(folder/'rtl_sim')],folder/'cpp.log')
    metrics['proof_s']=yosys(read+f'prep -top comparison -flatten; memory_map; opt; sat -seq {depth} -set-at 1 rst 1 -prove-skip 1 -prove eq 1 -verify -set-def-inputs -show-inputs -show-outputs',folder/'equivalence.log',240);metrics['depth']=depth;metrics['proof']='PASS' if 'SUCCESS!' in (folder/'equivalence.log').read_text() else 'UNRECOGNIZED'
    if metrics['proof']!='PASS':raise RuntimeError('No proof-success marker')
    return metrics

def library_run(folder,spec,traces):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    for name in ['eventweaver.py','successor.py']:
        shutil.copy2(ROOT/'src'/name,folder/name)
        if digest(ROOT/'src'/name)!=digest(folder/name):raise RuntimeError('Ordinary library differs')
    payload=json.dumps({'spec':spec,'traces':traces})
    script='import sys,json;sys.path.insert(0,sys.argv[1]);import successor;d=json.load(sys.stdin);json.dump([successor.run(d["spec"],t) for t in d["traces"]],sys.stdout)'
    st=time.perf_counter();r=subprocess.run([sys.executable,'-c',script,str(folder)],input=payload,text=True,capture_output=True,check=True);return json.loads(r.stdout),time.perf_counter()-st

def campaign(mode,seed=None):
    outdir=ROOT/'results'/f'successor_{mode}';outdir.mkdir(parents=True,exist_ok=True)
    if mode=='confirmation':
        if not (ROOT/'protocol/successor_freeze.json').exists():raise RuntimeError('No successor freeze')
        if seed is None:raise ValueError('Fresh seed needed')
        specs=network_specs(seed,6);seeds=[seed+i*100003 for i in range(6)];count=8
    else:
        specs=network_specs(6619,2);seeds=[6619,7727];count=4
    (outdir/'specifications.json').write_text(json.dumps({'seed':seed,'networks':specs,'trace_seeds':seeds},indent=2));records=[];metrics=[];failures=[]
    for i,(spec,s) in enumerate(zip(specs,seeds)):
        traces=network_traces(spec,s,count);folder=outdir/f'network_{i:02d}';metric=build(spec,folder);rtl,runtime=run_rtl(folder,traces);library,libtime=library_run(outdir/'ordinary_library',spec,traces);metric.update(network=i,traces=count,rtl_run_wall_s=runtime,library_subprocess_wall_s=libtime)
        for k,trace in enumerate(traces):
            st=time.perf_counter();expected=conventional_network.oracle(spec,trace);oracle_time=time.perf_counter()-st;st=time.perf_counter();cv=conventional_network.run(spec,trace);conventional_time=time.perf_counter()-st;st=time.perf_counter();ew=successor.run(spec,trace);successor_time=time.perf_counter()-st;er,cr=rtl[k];ok=expected==cv==ew==er==cr==library[k]
            rec={'network_index':i,'trace_index':k,'trace':trace,'oracle':expected,'conventional':cv,'successor':ew,'successor_rtl':er,'conventional_rtl':cr,'ordinary_library':library[k],'pass':ok,'oracle_wall_s':oracle_time,'conventional_wall_s':conventional_time,'successor_wall_s':successor_time};records.append(rec)
            if not ok:failures.append({'network':i,'trace':k})
        metrics.append(metric);(outdir/'progress.json').write_text(json.dumps(metrics,indent=2))
    directed_results=[];cases=directed();groups={}
    for i,case in enumerate(cases):groups.setdefault(json.dumps(case['spec'],sort_keys=True),[]).append(i)
    for group_index,(sp,indices) in enumerate(groups.items()):
        folder=outdir/f'directed_{group_index:02d}';metric=build(json.loads(sp),folder);rtl,_=run_rtl(folder,[cases[i]['trace'] for i in indices])
        for position,i in enumerate(indices):
            case=cases[i];spec=case['spec'];trace=case['trace'];expected=[case['expected'].get(t,0) for t in range(len(trace))];cv=conventional_network.run(spec,trace);oracle=conventional_network.oracle(spec,trace);ew=successor.run(spec,trace);er,cr=rtl[position];ok=expected==cv==oracle==ew==er==cr
            directed_results.append(dict(case,expected_list=expected,conventional=cv,oracle=oracle,successor=ew,successor_rtl=er,conventional_rtl=cr,pass_test=ok,metrics=metric))
            if not ok:failures.append({'directed':case['name']})
    bad=[]
    for i,spec in enumerate(invalid()):
        row={'index':i,'spec':spec}
        for name,fn in [('conventional',conventional_network.normalize),('successor',successor.verilog)]:
            try:fn(spec);row[name]='ACCEPTED_INVALID'
            except (ValueError,TypeError,KeyError,AssertionError):row[name]='REJECTED'
        if any(row[k]!='REJECTED' for k in ['conventional','successor']):failures.append({'invalid':i,'detail':row})
        bad.append(row)
    parent_rejection=False
    try:eventweaver.compile_spec(json.loads((ROOT/'protocol/successor_v1.json').read_text())['development_demo']['stages'])
    except (ValueError,TypeError):parent_rejection=True
    if not parent_rejection:failures.append({'parent':'Accepted virtual-channel grammar'})
    (outdir/'traces.jsonl.gz').write_bytes(gzip.compress(('\n'.join(json.dumps(x,sort_keys=True,separators=(',',':')) for x in records)+'\n').encode(),mtime=0));(outdir/'directed.json').write_text(json.dumps(directed_results,indent=2));(outdir/'invalid.json').write_text(json.dumps(bad,indent=2));(outdir/'failures.json').write_text(json.dumps(failures,indent=2))
    summary={'mode':mode,'seed':seed,'networks':len(specs),'traces':len(records),'ticks':sum(len(r['trace']) for r in records),'accepted_traces':sum(r['pass'] for r in records),'positive_stage_outputs':sum(x.bit_count() for r in records for x in r['oracle']),'directed_cases':len(directed_results),'invalid_specs':len(bad),'parent_rejects_virtual_channels':parent_rejection,'same_artifact_library_tie':all(r['successor']==r['ordinary_library'] for r in records),'functional_conventional_tie':all(r['successor']==r['conventional'] for r in records),'failures':failures,'metrics':metrics,'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'src/eventweaver.py',ROOT/'src/successor.py',ROOT/'src/conventional_network.py',Path(__file__)]},'limitations':'Different grammar and compositional mission, not learned weights; conventional and ordinary-library ties retained; functional RTL only, no physical timing.'}
    (outdir/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k not in ['metrics','source_sha256']},indent=2));return summary

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['development','confirmation'],default='development');ap.add_argument('--seed',type=int);a=ap.parse_args();s=campaign(a.mode,a.seed)
    if s['failures']:sys.exit(1)

if __name__=='__main__':main()
