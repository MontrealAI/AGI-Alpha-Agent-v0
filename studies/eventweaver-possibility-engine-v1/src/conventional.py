import argparse,json,re
from pathlib import Path

FIELDS={'name','a','b','c','veto','l1','u1','l2','u2','deadline'}

def normalize(spec):
    if isinstance(spec,dict):
        if set(spec)-{'patterns','channels'} or 'patterns' not in spec or spec.get('channels',8)!=8: raise ValueError('Only eight channels and a patterns array are supported')
        spec=spec['patterns']
    if not isinstance(spec,list) or not 1<=len(spec)<=4: raise ValueError('One to four patterns required')
    names=set(); result=[]
    for p in spec:
        if not isinstance(p,dict) or set(p)!=FIELDS: raise ValueError('Pattern fields do not match the contract')
        if not isinstance(p['name'],str) or not p['name'] or p['name'] in names: raise ValueError('Unique nonempty pattern names required')
        names.add(p['name'])
        if any(type(p[k]) is not int for k in FIELDS-{'name'}): raise ValueError('Integer channel and lag fields required')
        channels=[p[k] for k in ('a','b','c','veto')]
        if any(not 0<=x<8 for x in channels) or len(set(channels))!=4: raise ValueError('Four distinct channel ids in 0..7 required')
        if not 1<=p['l1']<=p['u1'] or not 1<=p['l2']<=p['u2'] or not p['u1']+p['u2']<=p['deadline']<=20: raise ValueError('Lag/deadline bounds violate contract')
        result.append(dict(p))
    return result

def sample(row):
    if isinstance(row,dict):
        if set(row)-{'events','rst'} or 'events' not in row: raise ValueError('Invalid trace row')
        value=row['events']; reset=row.get('rst',False)
        if type(reset) not in (bool,int) or reset not in (0,1): raise ValueError('Reset must be boolean')
    else: value=row; reset=False
    if type(value) is not int or not 0<=value<256: raise ValueError('Events must be an 8-bit integer')
    return value,bool(reset)

def run(spec,trace):
    ps=normalize(spec); depth=max(p['deadline'] for p in ps); hist=[0]*(depth+1); result=[]
    for row in trace:
        value,reset=sample(row)
        hist=[0]*(depth+1) if reset else [value]+hist[:-1]
        mask=0
        for n,p in enumerate(ps):
            d=p['deadline']
            if not (hist[d]>>p['a'])&1 or any((x>>p['veto'])&1 for x in hist[:d+1]): continue
            ok=any(((hist[d-i]>>p['b'])&1) and ((hist[d-i-j]>>p['c'])&1) for i in range(p['l1'],p['u1']+1) for j in range(p['l2'],p['u2']+1))
            mask|=int(ok)<<n
        result.append(mask)
    return result

def emit_verilog(spec,module='conventional'):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',module): raise ValueError('Invalid module identifier')
    ps=normalize(spec); dmax=max(p['deadline'] for p in ps)
    lines=[f'module {module}(input wire clk,input wire rst,input wire [7:0] events,output wire [{len(ps)-1}:0] out);',f'reg [7:0] history [0:{dmax}];','integer k;','always @(posedge clk) begin',f'  if(rst) begin for(k=0;k<={dmax};k=k+1) history[k]<=8\'b0; end','  else begin',"    history[0]<=events;",f'    for(k=1;k<={dmax};k=k+1) history[k]<=history[k-1];','  end','end']
    for n,p in enumerate(ps):
        d=p['deadline']; paths=[f'(history[{d-i}][{p["b"]}] & history[{d-i-j}][{p["c"]}])' for i in range(p['l1'],p['u1']+1) for j in range(p['l2'],p['u2']+1)]
        veto=' | '.join(f'history[{k}][{p["veto"]}]' for k in range(d+1))
        lines.append(f'assign out[{n}] = history[{d}][{p["a"]}] & ({" | ".join(paths)}) & ~({veto});')
    return '\n'.join(lines+['endmodule',''])

def compile_spec(spec):
    ps=normalize(spec)
    return {'patterns':ps,'verilog':emit_verilog(ps),'method':'independent history-formula RTL','logical_history_bits':8*(max(p['deadline'] for p in ps)+1)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('action',choices=['compile','simulate']); ap.add_argument('--spec',required=True); ap.add_argument('--trace');ap.add_argument('--output',required=True); a=ap.parse_args(); spec=json.loads(Path(a.spec).read_text())
    content=emit_verilog(spec) if a.action=='compile' else json.dumps(run(spec,json.loads(Path(a.trace).read_text())))+'\n'
    Path(a.output).write_text(content)

if __name__=='__main__': main()
