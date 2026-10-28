import re
import conventional,reference_oracle

ROLES=('a','b','c','veto')

def normalize(spec):
    if not isinstance(spec,dict) or set(spec)!={'channels','stages'} or spec['channels']!=8:raise ValueError('Network needs channels=8 and stages')
    stages=spec['stages']
    if not isinstance(stages,list) or not 1<=len(stages)<=4:raise ValueError('One to four stages required')
    names=[]
    for p in stages:
        if not isinstance(p,dict) or set(p)!=conventional.FIELDS:raise ValueError('Invalid stage fields')
        if not isinstance(p['name'],str) or not p['name'] or p['name'] in names:raise ValueError('Unique nonempty names required')
        names.append(p['name'])
        local=dict(p,**{role:i for i,role in enumerate(ROLES)});conventional.normalize([local])
    deps={name:[] for name in names}
    for p in stages:
        refs=[p[r] for r in ROLES]
        if any(not isinstance(x,str) for x in refs) or len(set(refs))!=4:raise ValueError('Four distinct source references required')
        for x in refs:
            if re.fullmatch(r'raw:[0-7]',x):continue
            if x.startswith('stage:') and x[6:] in deps:deps[p['name']].append(x[6:])
            else:raise ValueError('Unknown source')
    visiting=set();visited=set();order=[]
    def visit(name):
        if name in visiting:raise ValueError('Cyclic instrument network')
        if name in visited:return
        visiting.add(name)
        for dep in deps[name]:visit(dep)
        visiting.remove(name);visited.add(name);order.append(name)
    for name in names:visit(name)
    return stages,order

def run(spec,trace,oracle=False):
    stages,order=normalize(spec);byname={p['name']:p for p in stages};samples=[conventional.sample(row) for row in trace];outputs={};core=reference_oracle.run if oracle else conventional.run
    for name in order:
        p=byname[name];local=[]
        for t,(raw,rst) in enumerate(samples):
            mask=0
            for k,role in enumerate(ROLES):
                ref=p[role]
                value=(raw>>int(ref[4:]))&1 if ref.startswith('raw:') else (outputs[ref[6:]][t-1] if t else 0)
                mask|=value<<k
            local.append({'events':mask,'rst':rst})
        outputs[name]=core([dict(p,**{role:i for i,role in enumerate(ROLES)})],local)
    return [sum(outputs[p['name']][t]<<i for i,p in enumerate(stages)) for t in range(len(samples))]

def oracle(spec,trace):return run(spec,trace,True)

def verilog(spec,module='conventional_network'):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',module):raise ValueError('Invalid module name')
    stages,_=normalize(spec);lookup={p['name']:i for i,p in enumerate(stages)};parts=[]
    for i,p in enumerate(stages):parts.append(conventional.emit_verilog([dict(p,**{r:k for k,r in enumerate(ROLES)})],f'conv_stage_{i}'))
    lines=[f'module {module}(input wire clk,input wire rst,input wire[7:0] events,output wire[{len(stages)-1}:0] out);']
    for i,p in enumerate(stages):
        inputs=[]
        for role in reversed(ROLES):
            ref=p[role];inputs.append(f'events[{int(ref[4:])}]' if ref.startswith('raw:') else f'out[{lookup[ref[6:]]}]')
        lines.append(f'wire [7:0] local_{i} = {{4\'b0000,{",".join(inputs)}}};')
        lines.append(f'conv_stage_{i} s{i}(clk,rst,local_{i},out[{i}]);')
    return '\n'.join(parts+lines+['endmodule',''])
