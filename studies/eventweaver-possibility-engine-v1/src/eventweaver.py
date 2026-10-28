import argparse
import hashlib
import json
import pathlib
import platform
import sys
import time

FIELDS = ('name', 'a', 'b', 'c', 'veto', 'l1', 'u1', 'l2', 'u2', 'deadline')

def normalize(spec):
    if isinstance(spec, dict):
        if set(spec) - {'patterns', 'channels'}:
            raise ValueError('Specification contains unsupported top-level fields')
        if spec.get('channels', 8) != 8:
            raise ValueError('Exactly eight event channels are supported')
        spec = spec.get('patterns')
    if not isinstance(spec, list) or not 1 <= len(spec) <= 4:
        raise ValueError('One to four patterns are required')
    patterns, names = [], set()
    for raw in spec:
        if not isinstance(raw, dict) or set(raw) != set(FIELDS):
            raise ValueError('Every pattern must contain exactly the declared fields')
        p = dict(raw)
        if not isinstance(p['name'], str) or not p['name'] or p['name'] in names:
            raise ValueError('Pattern names must be nonempty and unique')
        names.add(p['name'])
        if any(type(p[k]) is not int for k in FIELDS[1:]):
            raise ValueError('All channel and time fields must be integers, not booleans')
        channels = [p[k] for k in ('a', 'b', 'c', 'veto')]
        if len(set(channels)) != 4 or not all(0 <= c < 8 for c in channels):
            raise ValueError('Four distinct channel identifiers in 0..7 are required')
        if not (1 <= p['l1'] <= p['u1'] and 1 <= p['l2'] <= p['u2']):
            raise ValueError('Positive ordered lag bounds are required')
        if not p['u1'] + p['u2'] <= p['deadline'] <= 20:
            raise ValueError('Deadline must cover both upper lags and be at most 20')
        patterns.append(p)
    return patterns

def compile_spec(spec):
    patterns = normalize(spec)
    states, transitions, outputs = [], [], []
    for j, p in enumerate(patterns):
        index = {}
        def add(key):
            index[key] = len(states)
            states.append({'pattern': j, 'kind': key[0], 'coordinates': list(key[1:])})
            transitions.append(None)
        for age in range(p['u1']):
            add(('anchor', age))
        for first_gap in range(p['l1'], p['u1'] + 1):
            for age_since_b in range(p['u2']):
                add(('prefix', first_gap, age_since_b))
        for age in range(p['l1'] + p['l2'], p['deadline'] + 1):
            add(('matched', age))
        def term(*parts):
            return list(parts)
        def put(key, terms):
            transitions[index[key]] = {'veto': p['veto'], 'any': terms}
        put(('anchor', 0), [term(['event', p['a']])])
        for age in range(1, p['u1']):
            put(('anchor', age), [term(['state', index[('anchor', age - 1)]])])
        for first_gap in range(p['l1'], p['u1'] + 1):
            put(('prefix', first_gap, 0), [term(['state', index[('anchor', first_gap - 1)]], ['event', p['b']])])
            for age_since_b in range(1, p['u2']):
                put(('prefix', first_gap, age_since_b), [term(['state', index[('prefix', first_gap, age_since_b - 1)]])])
        earliest = p['l1'] + p['l2']
        for age in range(earliest, p['deadline'] + 1):
            terms = []
            if age > earliest:
                terms.append(term(['state', index[('matched', age - 1)]]))
            for first_gap in range(p['l1'], p['u1'] + 1):
                second_gap = age - first_gap
                if p['l2'] <= second_gap <= p['u2']:
                    terms.append(term(['state', index[('prefix', first_gap, second_gap - 1)]], ['event', p['c']]))
            put(('matched', age), terms)
        outputs.append(index[('matched', p['deadline'])])
    canonical = json.dumps({'channels': 8, 'patterns': patterns}, sort_keys=True, separators=(',', ':'))
    return {'schema': 'eventweaver.ir.v1', 'patterns': patterns, 'spec_sha256': hashlib.sha256(canonical.encode()).hexdigest(), 'states': states, 'transitions': transitions, 'outputs': outputs}

def sample(row):
    if type(row) is int:
        events, rst = row, False
    elif isinstance(row, dict) and set(row) <= {'events', 'rst'}:
        events, rst = row.get('events', 0), row.get('rst', False)
        if type(rst) is not bool:
            raise ValueError('rst must be boolean')
    else:
        raise ValueError('Each sample must be an integer mask or events/rst record')
    if type(events) is not int or not 0 <= events < 256:
        raise ValueError('Event masks must be integers in 0..255')
    return events, rst

class Engine:
    def __init__(self, spec):
        self.ir = compile_spec(spec)
        self.state = [False] * len(self.ir['states'])
        self.ticks = 0
    def step(self, events=0, rst=False):
        events, rst = sample({'events': events, 'rst': rst})
        if rst:
            self.state = [False] * len(self.state)
        else:
            old = self.state
            bits = [bool(events & (1 << c)) for c in range(8)]
            self.state = [not bits[rule['veto']] and any(all(old[i] if kind == 'state' else bits[i] for kind, i in term) for term in rule['any']) for rule in self.ir['transitions']]
        self.ticks += 1
        return sum(int(self.state[i]) << j for j, i in enumerate(self.ir['outputs']))
    def reset(self):
        self.state = [False] * len(self.state)
        self.ticks = 0

def run(spec, trace):
    engine = Engine(spec)
    return [engine.step(*sample(row)) for row in trace]

def verilog(spec, module_name='eventweaver'):
    if not module_name.isidentifier() or not module_name.isascii():
        raise ValueError('Invalid Verilog module name')
    ir = compile_spec(spec)
    n, width = len(ir['states']), len(ir['patterns'])
    lines = [f'module {module_name}(input wire clk, input wire rst, input wire [7:0] events, output wire [{width-1}:0] out);', f'  reg [{n-1}:0] state;', '  always @(posedge clk) begin', f"    if (rst) state <= {n}'b0;", '    else begin']
    for target, rule in enumerate(ir['transitions']):
        terms = ['(' + ' & '.join(f'{"state" if kind == "state" else "events"}[{i}]' for kind, i in term) + ')' for term in rule['any']]
        expr = ' | '.join(terms) or "1'b0"
        lines.append(f"      state[{target}] <= ~events[{rule['veto']}] & ({expr});")
    lines += ['    end', '  end']
    lines += [f'  assign out[{j}] = state[{i}];' for j, i in enumerate(ir['outputs'])]
    lines += ['endmodule', '']
    return '\n'.join(lines)

def cxx(spec):
    ir = compile_spec(spec)
    n = len(ir['states'])
    lines = ['#include <array>', '#include <cstdint>', '#include <iostream>', 'int main() {', f'  std::array<bool,{n}> s{{}}, next{{}};', '  unsigned events, rst;', '  while (std::cin >> events >> rst) {', '    if (events > 255 || rst > 1) return 2;', '    if (rst) s.fill(false);', '    else {']
    for target, rule in enumerate(ir['transitions']):
        terms = ['(' + ' && '.join(f's[{i}]' if kind == 'state' else f'(events & {1 << i}u)' for kind, i in term) + ')' for term in rule['any']]
        expr = ' || '.join(terms) or 'false'
        lines.append(f"      next[{target}] = !(events & {1 << rule['veto']}u) && ({expr});")
    lines += ['      s = next;', '    }', '    unsigned out = 0;']
    lines += [f'    out |= static_cast<unsigned>(s[{i}]) << {j};' for j, i in enumerate(ir['outputs'])]
    lines += ["    std::cout << out << '\\n';", '  }', '}', '']
    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser(description='EventWeaver: compile bounded temporal event contracts into synchronous RTL and executable logic')
    subs = parser.add_subparsers(dest='command', required=True)
    for name in ['compile', 'simulate', 'inspect']:
        p = subs.add_parser(name)
        p.add_argument('--spec', required=True, type=pathlib.Path)
        p.add_argument('--output', type=pathlib.Path)
        if name == 'compile':
            p.add_argument('--format', choices=['verilog', 'ir', 'cxx'], default='verilog')
            p.add_argument('--module', default='eventweaver')
        elif name == 'simulate':
            p.add_argument('--trace', required=True, type=pathlib.Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    if args.command == 'compile':
        result = verilog(spec, args.module) if args.format == 'verilog' else cxx(spec) if args.format == 'cxx' else json.dumps(compile_spec(spec), indent=2) + '\n'
    elif args.command == 'simulate':
        trace = json.loads(args.trace.read_text())
        result = json.dumps({'spec_sha256': compile_spec(spec)['spec_sha256'], 'outputs': run(spec, trace)}, indent=2) + '\n'
    else:
        ir = compile_spec(spec)
        result = json.dumps({'spec_sha256': ir['spec_sha256'], 'patterns': len(ir['patterns']), 'state_bits': len(ir['states']), 'transitions': len(ir['transitions']), 'output_bits': len(ir['outputs']), 'max_deadline': max(p['deadline'] for p in ir['patterns']), 'python': platform.python_version()}, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result)
    else:
        sys.stdout.write(result)

if __name__ == '__main__':
    main()
