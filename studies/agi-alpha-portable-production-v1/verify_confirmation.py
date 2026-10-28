# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy, hashlib, importlib.util, json, math, platform, time
from pathlib import Path
import cadquery as cq

ROOT = Path(__file__).resolve().parent

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_constructor():
    path = ROOT / 'src/produce.py'
    spec = importlib.util.spec_from_file_location('frozen_constructor', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def native_reference(case: dict):
    body = cq.Workplane('XY').box(*case['stock'])
    if case['corner_radius']:
        body = body.edges('|Z').fillet(case['corner_radius'])
    for h in case['holes']:
        top = body.faces('>Z').workplane(centerOption='CenterOfBoundBox').pushPoints([(h['x'],h['y'])])
        if h['kind'] == 'through':
            body = top.hole(h['diameter'])
        elif h['kind'] == 'counterbore':
            body = top.cboreHole(h['diameter'],h['counterbore_diameter'],h['counterbore_depth'])
        else:
            body = top.cskHole(h['diameter'],h['countersink_diameter'],h['included_angle_deg'])
    return body.val()

def independent_volume(case: dict) -> float:
    a,b,t = case['stock']
    rounded_corners = (4-math.pi)*case['corner_radius']**2*t
    removals = []
    for hole in case['holes']:
        r = hole['diameter']/2
        removals.append(math.pi*r*r*t)
        if hole['kind'] == 'counterbore':
            R = hole['counterbore_diameter']/2
            removals.append(math.pi*(R*R-r*r)*hole['counterbore_depth'])
        if hole['kind'] == 'countersink':
            R = hole['countersink_diameter']/2
            depth = (R-r)/math.tan(hole['included_angle_deg']*math.pi/360)
            removals.append(math.pi*depth*(R*R+R*r-2*r*r)/3)
    return a*b*t-rounded_corners-math.fsum(removals)

def probes(shape, case: dict) -> list:
    t = case['stock'][2]
    rows=[]
    for h in case['holes']:
        x,y,r=h['x'],h['y'],h['diameter']/2
        outside_bottom=not shape.isInside((x,y,-t*.4),1e-8)
        wall=shape.isInside((x+r*1.08,y,-t*.4),1e-8)
        row={'feature':h['id'],'axis_empty':outside_bottom,'lower_wall_present':wall}
        if h['kind']=='counterbore':
            R=h['counterbore_diameter']/2;z=t/2-h['counterbore_depth']/2
            row['top_recess_empty']=not shape.isInside((x+(r+R)/2,y,z),1e-8)
        if h['kind']=='countersink':
            R=h['countersink_diameter']/2
            d=(R-r)/math.tan(math.radians(h['included_angle_deg']/2))
            row['top_recess_empty']=not shape.isInside((x+r+(R-r)*.65,y,t/2-d*.2),1e-8)
        rows.append(row)
    return rows

def reject_cases(base: dict) -> dict:
    cases={}
    c=copy.deepcopy(base);c['holes'][1]['x']=c['holes'][0]['x'];c['holes'][1]['y']=c['holes'][0]['y'];cases['overlapping hole envelopes']=c
    c=copy.deepcopy(base);c['holes'][0]['x']=c['stock'][0]/2-c['holes'][0]['diameter']/2;cases['hole at exterior boundary']=c
    c=copy.deepcopy(base);c['holes']=[{'id':'corner','kind':'through','x':48,'y':33,'diameter':1}];cases['hole in rounded-corner envelope']=c
    c=copy.deepcopy(base);c['holes'][1]['counterbore_depth']=float('inf');cases['infinite counterbore depth']=c
    c=copy.deepcopy(base);c['holes'][0]['kind']='blind';cases['unsupported blind-hole kind']=c
    c=copy.deepcopy(base);c['stock'][2]=0;cases['zero stock thickness']=c
    return cases

def main() -> None:
    protocol=ROOT/'protocol/FRESH_CONFIRMATION.json'
    data=json.loads(protocol.read_text())
    if digest(ROOT/'src/produce.py')!=data['constructor_sha256']:
        raise SystemExit('REFUSED: constructor changed under the old freeze')
    p=load_constructor();out=ROOT/'results/fresh_confirmation';out.mkdir(parents=True,exist_ok=True)
    result={'protocol_sha256':digest(protocol),'checker_sha256':digest(Path(__file__)),
      'constructor_sha256':data['constructor_sha256'],'python':platform.python_version(),'cadquery':cq.__version__,
      'origin':data['case_origin'],'independence':'Separate code and arithmetic; same OpenCascade kernel and same-session team. No human trial or physical validation.',
      'cases':[],'negative_cases':[],'exploratory_schema_cases':[]}
    started=time.perf_counter()
    for case in data['cases']:
        shape=p.build(case);ref=native_reference(case);folder=out/case['id']
        p.export_case(case,shape,folder)
        back=cq.importers.importStep(str(folder/'part.step')).val()
        m=p.metrics(shape);br=p.metrics(back);expected=independent_volume(case)
        tol=max(1e-6,abs(expected)*1e-8)
        delta=shape.cut(ref).Volume()+ref.cut(shape).Volume()
        pts=probes(shape,case)
        checks={'one_valid_solid':m['valid'] and m['solids']==1,
          'nominal_bbox':all(abs(x-y)<1e-7 for x,y in zip(m['bbox'],case['stock'])),
          'independent_analytic_volume':abs(m['volume']-expected)<=tol,
          'independent_native_geometry':abs(delta)<=tol,
          'step_roundtrip':br['valid'] and br['solids']==1 and abs(br['volume']-expected)<=tol and all(abs(x-y)<1e-7 for x,y in zip(br['bbox'],case['stock'])),
          'feature_probes':all(all(v for k,v in row.items() if k!='feature') for row in pts)}
        result['cases'].append({'id':case['id'],'checks':checks,'accepted':all(checks.values()),'metrics':m,
          'independent_expected_volume':expected,'symmetric_difference_volume':delta,'feature_probes':pts})
    for name,case in reject_cases(data['cases'][0]).items():
        try:
            p.validate(case);refused=False;reason='accepted'
        except (ValueError,KeyError,TypeError) as e:
            refused=True;reason=str(e)
        result['negative_cases'].append({'case':name,'refused':refused,'reason':reason})
    for label in data['exploratory_adversarial_cases']:
        case=copy.deepcopy(data['cases'][0])
        if label=='duplicate feature identifiers':case['holes'][1]['id']=case['holes'][0]['id']
        else:del case['holes'][0]['id']
        try:p.validate(case);refused=False
        except (ValueError,KeyError,TypeError):refused=True
        result['exploratory_schema_cases'].append({'case':label,'refused':refused,'meaning':'Additional semantic admission requirement; not part of original geometry acceptance.'})
    result['wall_seconds']=time.perf_counter()-started
    result['accepted_cases']=sum(x['accepted'] for x in result['cases'])
    result['refused_negative_cases']=sum(x['refused'] for x in result['negative_cases'])
    result['status']='PASS_GEOMETRY_ONLY' if result['accepted_cases']==3 and result['refused_negative_cases']==6 else 'FAIL_FROZEN_CONFIRMATION'
    (out/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','accepted_cases','refused_negative_cases','wall_seconds','exploratory_schema_cases')}))

if __name__=='__main__':main()
