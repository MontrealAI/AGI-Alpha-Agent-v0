from pathlib import Path
import xml.etree.ElementTree as E
from fractions import Fraction as F
import json,hashlib,collections
B=Path('studies/agi-alpha-opportunity-discovery-v4');I=B/'evaluation/protected/inputs';O=B/'expertise/Eplus';q='{http://qifstandards.org/xsd/qif2}';L=lambda t:t.rsplit('}',1)[-1]
a=json.loads((O/'analysis.json').read_text())
for job,file,ids,lo,hi in [('H1','Box_FAIR.qif',set(['14','20','26','32']),F(31,10),F(35,10)),('H2','Cover_FAIR.qif',set(a['H2']['ids']),F(42,10),F(48,10))]:
 rows=[]
 for ev,e in E.iterparse(I/file,events=('end',)):
  if e.tag==q+'DiameterCharacteristicActual' and e.findtext(q+'CharacteristicItemId') in ids:
   rows.append((e.get('id'),F(e.findtext(q+'Value'))))
 low=min(v for i,v in rows);high=max(v for i,v in rows);nfail=sum(not lo<=v<=hi for i,v in rows)
 assert len(rows)==a[job]['count'] and nfail==a[job]['mm_hypothesis_fail_count'] and sum(not lo<=v*1000<=hi for i,v in rows)==a[job]['formal_fail_count']
 print('INDEPENDENT EXACT RATIONAL',job,len(rows),str(low),str(high),'MM FAIL',nfail,'FORMAL FAIL',len(rows))
print('UNIT SCHEMA HASH',hashlib.sha256((B/'instrument/QIF_2_1_Units.xsd').read_bytes()).hexdigest())
for file in ['Box_FAIR.qif','Cover_FAIR.qif']:
 r=E.parse(I/file).getroot();print('UNIT OVERRIDES',file,[(L(e.tag),e.attrib) for e in r.iter() if 'linearUnit' in e.attrib or L(e.tag)=='FileUnits'])
for file in ['Box_incoming.qif','Cover_incoming.qif']:
 r=E.parse(I/file).getroot();print('INCOMING UNITS',file,E.tostring(r.find(q+'FileUnits'),encoding='unicode'))
r=E.parse(I/'Box_incoming.qif').getroot();ix={e.get('id'):e for e in r.iter() if e.get('id')}
mr=ix['604'];print('H4 RESULT',mr.attrib)
for e in mr:
 if L(e.tag) not in ['MeasuredFeatures','MeasuredCharacteristics']:print(E.tostring(e,encoding='unicode'))
print('H4 COMPONENT',E.tostring(ix['528'],encoding='unicode'))
print('H4 FAIL ACTUALS',[(e.get('id'),e.findtext(q+'CharacteristicItemId'),e.findtext(q+'Value'),[n.text for n in e.findall(q+'FeatureActualIds/'+q+'Id')]) for e in mr.iter() if e.findtext(q+'Status/'+q+'CharacteristicStatusEnum')=='FAIL'])
for file,targets in [('Cover_integrated.owl',{'571'}),('Box_integrated.owl',{'29','534','533','604','528'})]:
 r=E.parse(I/file).getroot();inds=[e for e in r if L(e.tag)=='NamedIndividual'];print('GRAPH',file,'INDIVIDUALS',len(inds))
 matches=[]
 for e in inds:
  for n in e:
   if (n.text or '').strip() in targets and L(n.tag).lower()=='id':matches.append(e);break
 print('GRAPH ID MATCHES',len(matches))
 for e in matches:print(E.tostring(e,encoding='unicode'))
 if not matches:
  selected=[e for e in inds if 'PerpendicularityCharacteristicItem_' in next(iter(e.attrib.values()),'')] if file.startswith('Cover') else [e for e in inds if any((n.text or '').strip()=='SIMPLE_HOLE12' for n in e)]
  for e in selected[:3]:print('GRAPH FALLBACK',E.tostring(e,encoding='unicode'))
print('SOURCE IDENTITIES',json.dumps(json.loads((O/'identities.json').read_text())))
