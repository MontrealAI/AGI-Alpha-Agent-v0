import hashlib
import importlib.metadata
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from eventweaver import compile_spec, cxx, run, verilog

def main():
    os.chdir(ROOT)
    demo = ROOT / 'data/demo'
    result = ROOT / 'results/synthesis'
    result.mkdir(parents=True, exist_ok=True)
    spec = json.loads((demo/'spec.json').read_text())
    trace = json.loads((demo/'trace.json').read_text())
    expected = json.loads((demo/'expected.json').read_text())['outputs']
    start = time.perf_counter()
    ir = compile_spec(spec)
    rtl = verilog(spec)
    (demo/'eventweaver.v').write_text(rtl)
    (demo/'eventweaver.cpp').write_text(cxx(spec))
    (demo/'ir.json').write_text(json.dumps(ir, indent=2)+'\n')
    compile_seconds = time.perf_counter()-start
    assert run(spec, trace) == expected
    compiler = shutil.which('g++')
    cxx_result = {'status':'NOT_RUN', 'reason':'g++ unavailable'}
    if compiler:
        start = time.perf_counter()
        cp = subprocess.run([compiler,'-O2','-std=c++17',str(demo/'eventweaver.cpp'),'-o',str(result/'eventweaver_demo')], capture_output=True, text=True, check=True)
        build_seconds = time.perf_counter()-start
        stdin = ''.join(f"{row['events']} {int(row['rst'])}\n" for row in trace)
        completed = subprocess.run([str(result/'eventweaver_demo')],input=stdin,capture_output=True,text=True,check=True)
        actual = [int(x) for x in completed.stdout.split()]
        assert actual == expected
        cxx_result = {'status':'PASS','ticks':len(trace),'build_seconds':build_seconds,'compiler':subprocess.check_output([compiler,'--version'],text=True).splitlines()[0]}
    local_yosys = ROOT/'.deps/bin/yowasp-yosys'
    yosys = str(local_yosys) if local_yosys.exists() else shutil.which('yowasp-yosys') or shutil.which('yosys')
    synth = {'status':'NOT_RUN','reason':'Yosys unavailable'}
    if yosys:
        env = dict(os.environ)
        env['PYTHONPATH'] = str(ROOT/'.deps') + os.pathsep + env.get('PYTHONPATH','')
        env['YOWASP_CACHE_DIR'] = str(ROOT/'.cache/yowasp')
        cmds = 'read_verilog data/demo/eventweaver.v; hierarchy -check -top eventweaver; proc; opt; check -assert; tee -o results/synthesis/rtl_statistics.json stat -json; synth -top eventweaver; check -assert; tee -o results/synthesis/generic_statistics.json stat -json; write_json results/synthesis/eventweaver_netlist.json'
        start = time.perf_counter()
        cp = subprocess.run([yosys,'-Q','-T','-l','results/synthesis/eventweaver_yosys.log','-p',cmds],capture_output=True,text=True,env=env)
        seconds = time.perf_counter()-start
        if cp.returncode:
            (result/'failure.txt').write_text(cp.stdout+'\n'+cp.stderr)
            raise RuntimeError('Yosys failed; see results/synthesis/failure.txt')
        stats = json.loads((result/'generic_statistics.json').read_text())['design']
        if any('LATCH' in cell.upper() for cell in stats['num_cells_by_type']):
            raise RuntimeError('Unexpected latch in synthesized design')
        synth = {'status':'PASS','seconds':seconds,'version':subprocess.check_output([yosys,'-V'],text=True,env=env).strip(),'generic_cells':stats['num_cells'],'cells_by_type':stats['num_cells_by_type'],'no_latches':True,'no_unresolved_modules':stats['num_submodules']==0,'technology':'generic logic, not physical area/timing/power','command':cmds}
    source=ROOT/'src/eventweaver.py'
    report={'edition':'EventWeaver construction v1','spec_sha256':ir['spec_sha256'],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'python':platform.python_version(),'patterns':len(ir['patterns']),'state_bits':len(ir['states']),'compile_seconds':compile_seconds,'python_demo':{'status':'PASS','ticks':len(trace),'accepted_output_bits':sum(x.bit_count() for x in expected),'nonzero_outputs':[{'tick':i,'mask':x} for i,x in enumerate(expected) if x]},'generated_cpp_demo':cxx_result,'synthesis':synth,'limits':['No physical hardware or vendor link integration tested','No measured Fmax, power, calibrated timing or optical data','Independent oracle and formal results are reported by audit workstream','Measured compile times are a single local environment, not inference or human engineering time']}
    (ROOT/'results/construction.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
