from __future__ import annotations
import argparse, csv, hashlib, json, math, platform, runpy, time
from pathlib import Path
import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUTS = ROOT.parents[1] / 'research_inputs'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate(spec):
    length, width, thickness = spec['stock']
    if not all(math.isfinite(x) and x > 0 for x in spec['stock']):
        raise ValueError('Stock dimensions must be finite and positive')
    corner = spec.get('corner_radius', 0)
    if not math.isfinite(corner) or not 0 <= corner < min(length, width)/2:
        raise ValueError('Invalid corner radius')
    for h in spec['holes']:
        if h['kind'] not in ('through', 'counterbore', 'countersink'):
            raise ValueError('Unsupported hole type')
        if not all(math.isfinite(h[k]) for k in ('x', 'y', 'diameter')) or h['diameter'] <= 0:
            raise ValueError('Invalid hole coordinates or diameter')
        outer = h['diameter']
        if h['kind'] == 'counterbore':
            outer = h['counterbore_diameter']
            if not outer >= h['diameter'] or not 0 < h['counterbore_depth'] < thickness:
                raise ValueError('Invalid counterbore')
        if h['kind'] == 'countersink':
            outer = h['countersink_diameter']
            angle = h['included_angle_deg']
            if not outer > h['diameter'] or not 0 < angle < 180:
                raise ValueError('Invalid countersink')
            if (outer-h['diameter'])/(2*math.tan(math.radians(angle/2))) >= thickness:
                raise ValueError('Countersink exceeds stock thickness')
        if abs(h['x'])+outer/2 >= length/2 or abs(h['y'])+outer/2 >= width/2:
            raise ValueError('Hole intersects exterior; outside admitted scope')

def build(spec):
    validate(spec)
    length, width, thickness = spec['stock']
    body = cq.Workplane('XY').box(length, width, thickness)
    if spec.get('corner_radius', 0):
        body = body.edges('|Z').fillet(spec['corner_radius'])
    solid = body.val()
    for h in spec['holes']:
        x, y, r = h['x'], h['y'], h['diameter']/2
        solid = solid.cut(cq.Solid.makeCylinder(r, thickness, (x,y,-thickness/2)))
        if h['kind'] == 'counterbore':
            depth = h['counterbore_depth']
            solid = solid.cut(cq.Solid.makeCylinder(h['counterbore_diameter']/2, depth, (x,y,thickness/2-depth)))
        elif h['kind'] == 'countersink':
            outer = h['countersink_diameter']/2
            depth = (outer-r)/math.tan(math.radians(h['included_angle_deg']/2))
            solid = solid.cut(cq.Solid.makeCone(r,outer,depth,(x,y,thickness/2-depth)))
    return solid.clean()

def analytic_volume(spec):
    length, width, thickness = spec['stock']
    volume = (length*width-(4-math.pi)*spec.get('corner_radius',0)**2)*thickness
    for h in spec['holes']:
        r = h['diameter']/2
        volume -= math.pi*r*r*thickness
        if h['kind'] == 'counterbore':
            volume -= math.pi*((h['counterbore_diameter']/2)**2-r*r)*h['counterbore_depth']
        elif h['kind'] == 'countersink':
            outer = h['countersink_diameter']/2
            depth = (outer-r)/math.tan(math.radians(h['included_angle_deg']/2))
            volume -= math.pi*depth*((outer*outer+outer*r+r*r)/3-r*r)
    return volume

def metrics(solid):
    b = solid.BoundingBox()
    return {'valid':solid.isValid(),'solids':len(solid.Solids()),'volume':solid.Volume(),
            'bbox':[b.xlen,b.ylen,b.zlen],'faces':len(solid.Faces())}

def export_case(spec, solid, folder):
    folder.mkdir(parents=True,exist_ok=True)
    cq.exporters.export(solid,str(folder/'part.step'))
    cq.exporters.export(solid,str(folder/'part.stl'),tolerance=0.02,angularTolerance=0.1)
    cq.exporters.export(solid,str(folder/'part.svg'),opt={'width':900,'height':600,'showAxes':False,'showHidden':False})
    (folder/'feature_program.json').write_text(json.dumps(spec,indent=2)+'\n')
    with (folder/'features.csv').open('w',newline='') as f:
        fields=['id','kind','x','y','diameter','counterbore_diameter','counterbore_depth','countersink_diameter','included_angle_deg','source_units','physical_tolerance','material','machine_release']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for h in spec['holes']:
            writer.writerow({**h,'source_units':spec['source_units'],'physical_tolerance':'UNSPECIFIED','material':'UNSPECIFIED','machine_release':'NO'})

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--program',type=Path,default=ROOT/'src/feature_program.json')
    p.add_argument('--source-dir',type=Path,default=DEFAULT_INPUTS)
    p.add_argument('--output',type=Path,default=ROOT/'results/construction_v1')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    program=json.loads(a.program.read_text())
    manifest=json.loads((a.source_dir/'SOURCE_MANIFEST.json').read_text())
    for r in manifest['files']:
        if sha(a.source_dir/r['path']) != r['sha256']:
            raise ValueError('Changed frozen input: '+r['path'])
    report={'schema':'construction-report-v1','status':'supporting conventional deliverable',
            'cadquery':cq.__version__,'python':platform.python_version(),
            'program_sha256':sha(a.program),'constructor_sha256':sha(__file__),
            'source_manifest_sha256':sha(a.source_dir/'SOURCE_MANIFEST.json'),
            'shared_kernel_limitation':'Both constructions and Boolean comparison use OpenCascade; analytic volume is separate arithmetic.',
            'cost':'Token billing and complete human-equivalent effort unknown; no commercial delivery or receipt.',
            'cases':[]}
    for spec in program['cases']:
        started=time.perf_counter();candidate=build(spec);construction_seconds=time.perf_counter()-started
        started=time.perf_counter();reference=runpy.run_path(str(a.source_dir/spec['source_file']),init_globals={'show_object':lambda *x,**k:None})['result'].val();reference_seconds=time.perf_counter()-started
        folder=a.output/spec['id'];export_case(spec,candidate,folder)
        back=cq.importers.importStep(str(folder/'part.step')).val()
        cm,rm,bm=metrics(candidate),metrics(reference),metrics(back)
        expected=analytic_volume(spec);tol=max(1e-6,1e-8*abs(expected))
        symmetric_difference=candidate.cut(reference).Volume()+reference.cut(candidate).Volume()
        checks={'one_valid_solid':cm['valid'] and cm['solids']==1,
                'nominal_bbox':all(abs(x-y)<1e-7 for x,y in zip(cm['bbox'],spec['stock'])),
                'analytic_volume':abs(cm['volume']-expected)<=tol,
                'reference_volume':abs(cm['volume']-rm['volume'])<=tol,
                'reference_symmetric_difference':abs(symmetric_difference)<=tol,
                'step_roundtrip':bm['valid'] and bm['solids']==1 and abs(bm['volume']-cm['volume'])<=tol and all(abs(x-y)<1e-7 for x,y in zip(bm['bbox'],cm['bbox']))}
        row={'id':spec['id'],'source':spec['source_file'],'constructed':cm,'reference':rm,'step_roundtrip':bm,
             'analytic_volume':expected,'symmetric_difference_volume':symmetric_difference,
             'acceptance_volume_tolerance':tol,'checks':checks,'accepted':all(checks.values()),
             'construction_seconds':construction_seconds,'reference_seconds':reference_seconds,
             'timing_is_not_a_performance_experiment':True,
             'artifacts':{x.name:{'bytes':x.stat().st_size,'sha256':sha(x)} for x in folder.iterdir() if x.is_file()}}
        report['cases'].append(row)
        (a.output/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
    report['accepted_cases']=sum(x['accepted'] for x in report['cases']);report['case_count']=len(report['cases'])
    (a.output/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'accepted_cases':report['accepted_cases'],'case_count':report['case_count'],'report':str(a.output/'acceptance.json')}))
    if report['accepted_cases']!=report['case_count']:raise SystemExit(1)

if __name__=='__main__':main()
