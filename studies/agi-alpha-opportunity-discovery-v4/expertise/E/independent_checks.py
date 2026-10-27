from pathlib import Path
from collections import Counter
from decimal import Decimal as D
import xml.etree.ElementTree as ET
import hashlib,json
B=Path('studies/agi-alpha-opportunity-discovery-v4');I=B/'evaluation/protected/inputs';O=B/'expertise/E';N={'q':'http://qifstandards.org/xsd/qif2'}
def tag(e):return e.tag.rsplit('}',1)[-1]
def compact(e):return {'tag':tag(e),**e.attrib,'text':(e.text or '').strip(),'children':[compact(c) for c in e]}
lines=[]
def emit(label,x):lines.append(label+' '+json.dumps(x,ensure_ascii=False))
for name in ['Box_FAIR.qif','Box_incoming.qif','Cover_FAIR.qif','Cover_incoming.qif']:
 r=ET.parse(I/name).getroot();ix={e.get('id'):e for e in r.iter() if e.get('id')}
 emit('UNIT OVERRIDES '+name,[(tag(e),e.get('id'),e.attrib) for e in r.iter() if any('unit' in a.lower() for a in e.attrib)])
 if 'incoming' in name:
  target='3.3' if name.startswith('Box') else '4.5';featureitems=[]
  for e in r.iter():
   if tag(e)!='CylinderFeatureItem':continue
   n=ix[e.findtext('q:FeatureNominalId',namespaces=N)];d=ix[n.findtext('q:FeatureDefinitionId',namespaces=N)]
   if d.findtext('q:Diameter',namespaces=N)==target:featureitems.append(e.get('id'))
  emit('INCOMING NOMINAL DIAMETER FAMILY '+name,{'diameter_mm':target,'feature_items':featureitems,'count':len(featureitems)})
for name, ids in [('Box_integrated.owl',{'29','28'}),('Cover_integrated.owl',{'23'})]:
 r=ET.parse(I/name).getroot();nodes={e.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about'):e for e in r if e.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')};hits={uri:e for uri,e in nodes.items() if any(tag(c)=='_id' and c.text in ids for c in e)}
 for uri,e in hits.items():
  emit('GRAPH FEATURE '+name,compact(e));refs=[n for n in nodes.values() if any(uri in c.attrib.values() for c in n)];emit('GRAPH REVERSE '+uri,[compact(n) for n in refs][:8])
# Independent arithmetic: compare decimal expressions with integer micrometre equivalents under hypothesis.
for label,low,high in [('h1',3100,3500),('h2',4200,4800)]:
 rows=json.loads((O/(label+'_verified_values.json')).read_text());verdicts=[low<=int(D(row['value'])*1000)<=high for row in rows];assert verdicts==[row['pass_mm_hypothesis'] for row in rows];emit('INTEGER CROSSCHECK',{'family':label,'count':len(rows),'pass':sum(verdicts)})
# Read-only CAD checks are corroboration of nominal size, not source-to-specimen registration.
try:
 from OCP.STEPControl import STEPControl_Reader
 from OCP.IFSelect import IFSelect_RetDone
 from OCP.TopExp import TopExp_Explorer
 from OCP.TopAbs import TopAbs_FACE
 from OCP.TopoDS import TopoDS
 from OCP.BRepAdaptor import BRepAdaptor_Surface
 from OCP.GeomAbs import GeomAbs_Cylinder
 for name,radius in [('Box_AP242.STP',1.65),('Cover_AP242.STP',2.25)]:
  reader=STEPControl_Reader();status=reader.ReadFile(str(I/name));assert status==IFSelect_RetDone;reader.TransferRoots();shape=reader.OneShape();xp=TopExp_Explorer(shape,TopAbs_FACE);hits=[];face=0
  while xp.More():
   face+=1;surf=BRepAdaptor_Surface(TopoDS.Face_s(xp.Current()))
   if surf.GetType()==GeomAbs_Cylinder:
    c=surf.Cylinder()
    if abs(c.Radius()-radius)<1e-7:
     p=c.Location();d=c.Axis().Direction();hits.append({'explorer_face':face,'radius':c.Radius(),'axis_point':[p.X(),p.Y(),p.Z()],'direction':[d.X(),d.Y(),d.Z()]})
   xp.Next()
  emit('CAD CYLINDERS '+name,{'query_radius':radius,'faces':hits})
except Exception as e:emit('CAD CHECK ERROR',{'type':type(e).__name__,'message':str(e)})
log='\n'.join(lines);(O/'independent_checks.log').write_text(log);print(log)
