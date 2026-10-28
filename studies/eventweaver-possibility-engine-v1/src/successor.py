import argparse
import hashlib
import json
import pathlib
import re

import eventweaver

FIELDS = eventweaver.FIELDS
CHANNEL_KEYS = ('a','b','c','veto')
PARENT_SHA256 = '756394972fbda2ee1819f7fa1a0c0cbae0d6bf8fcef959a57de51884bb5b8b73'

def validate(spec):
    if not isinstance(spec,dict) or set(spec) != {'channels','stages'} or type(spec['channels']) is not int or spec['channels'] != 8:
        raise ValueError('Network must declare eight raw channels and a stages list')
    stages = spec['stages']
    if not isinstance(stages,list) or not 1 <= len(stages) <= 4:
        raise ValueError('One to four stages are required')
    names = []
    for p in stages:
        if not isinstance(p,dict) or set(p) != set(FIELDS):
            raise ValueError('Invalid stage fields')
        if not isinstance(p['name'],str) or not p['name'] or p['name'] in names:
            raise ValueError('Stage names must be nonempty and unique')
        names.append(p['name'])
    bindings, local, edges = [], [], []
    for p in stages:
        refs = [p[k] for k in CHANNEL_KEYS]
        if any(not isinstance(x,str) for x in refs) or len(set(refs)) != 4:
            raise ValueError('Each stage requires four distinct source references')
        bound = []
        deps = []
        for ref in refs:
            if re.fullmatch(r'raw:[0-7]',ref):
                bound.append(('raw',int(ref[-1])))
            elif ref.startswith('stage:') and ref[6:] in names:
                idx = names.index(ref[6:])
                bound.append(('stage',idx))
                deps.append(idx)
            else:
                raise ValueError('Unresolved or invalid source reference')
        q = dict(p)
        q.update(dict(zip(CHANNEL_KEYS,range(4))))
        eventweaver.normalize([q])
        local.append(q)
        bindings.append(bound)
        edges.append(deps)
    status = [0]*len(stages)
    def visit(i):
        if status[i] == 1:
            raise ValueError('Directed instrument cycles are unsupported')
        if status[i] == 2:
            return
        status[i] = 1
        for j in edges[i]:
            visit(j)
        status[i] = 2
    for i in range(len(stages)):
        visit(i)
    return local, bindings

def verify_parent():
    path = pathlib.Path(eventweaver.__file__)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != PARENT_SHA256:
        raise ValueError('Retained parent compiler differs from the frozen artifact')
    return actual

class Network:
    def __init__(self,spec):
        verify_parent()
        self.local,self.bindings = validate(spec)
        self.engines = [eventweaver.Engine([p]) for p in self.local]
        self.previous = [0]*len(self.engines)
    def step(self,events=0,rst=False):
        events,rst = eventweaver.sample({'events':events,'rst':rst})
        snapshot = self.previous[:]
        following = []
        for engine,bindings in zip(self.engines,self.bindings):
            mask = sum(((events>>index)&1 if kind=='raw' else snapshot[index])<<slot for slot,(kind,index) in enumerate(bindings))
            following.append(engine.step(mask,rst))
        self.previous = following
        return sum(value<<i for i,value in enumerate(following))

def run(spec,trace):
    network = Network(spec)
    return [network.step(*eventweaver.sample(row)) for row in trace]

def verilog(spec,module_name='successor'):
    verify_parent()
    if not module_name.isidentifier() or not module_name.isascii():
        raise ValueError('Invalid module identifier')
    local,bindings = validate(spec)
    lines=[]
    for i,p in enumerate(local):
        lines.append(eventweaver.verilog([p],f'{module_name}_core_{i}'))
    lines.append(f'module {module_name}(input wire clk,input wire rst,input wire [7:0] events,output wire [{len(local)-1}:0] out);')
    for i in range(len(local)):
        lines.append(f'  wire [7:0] local_{i};')
        lines.append(f'  assign local_{i}[7:4] = 4\'b0;')
        for slot,(kind,index) in enumerate(bindings[i]):
            source=f'events[{index}]' if kind=='raw' else f'out[{index}]'
            lines.append(f'  assign local_{i}[{slot}] = {source};')
        lines.append(f'  {module_name}_core_{i} inst_{i}(.clk(clk),.rst(rst),.events(local_{i}),.out(out[{i}]));')
    lines += ['endmodule','']
    return '\n'.join(lines)

def main():
    parser=argparse.ArgumentParser(description='Compose frozen EventWeaver kernels into an acyclic instrument network')
    parser.add_argument('command',choices=['compile','simulate','inspect'])
    parser.add_argument('--spec',required=True,type=pathlib.Path)
    parser.add_argument('--trace',type=pathlib.Path)
    parser.add_argument('--output',type=pathlib.Path)
    args=parser.parse_args()
    spec=json.loads(args.spec.read_text())
    if args.command=='compile':
        content=verilog(spec)
    elif args.command=='simulate':
        if args.trace is None:parser.error('--trace is required')
        content=json.dumps({'outputs':run(spec,json.loads(args.trace.read_text()))},indent=2)+'\n'
    else:
        local,bindings=validate(spec)
        content=json.dumps({'parent_sha256':verify_parent(),'stages':len(local),'interface_delay_ticks':1,'state_bits':sum(len(eventweaver.compile_spec([p])['states']) for p in local),'bindings':bindings},indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(content)
    else:
        print(content,end='')

if __name__=='__main__':main()
