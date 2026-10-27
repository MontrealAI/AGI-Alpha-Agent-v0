from pathlib import Path
import xml.etree.ElementTree as E
from decimal import Decimal as D
import hashlib,json,csv,collections,difflib
B=Path('studies/agi-alpha-opportunity-discovery-v4');I=B/'evaluation/protected/inputs';O=B/'expertise/Eplus';Q={'q':'http://qifstandards.org/xsd/qif2'}
L=lambda t:t.rsplit('}',1)[-1]
def read(n):
 r=E.parse(I/n).getroot(); return r,{e.get('id'):e for e in r.iter() if e.get('id')},{c:e for e in r.iter() for c in e}
def txt(e,p):return e.findtext(p,namespaces=Q)
def flat(e):return {'tag':L(e.tag),'id':e.get('id'),'leaves':[(L(n.tag),(n.text or '').strip(),n.attrib) for n in e.iter() if not len(n)]}
def chain(ix,id):
 it=ix[id];no=ix[txt(it,'q:CharacteristicNominalId')];de=ix[txt(no,'q:CharacteristicDefinitionId')];return it,no,de
def interval(ix,id):
 it,no,de=chain(ix,id);t=D(txt(no,'q:TargetValue'));lo=D(txt(de,'.//q:MinValue'));hi=D(txt(de,'.//q:MaxValue'));lim=txt(de,'.//q:DefinedAsLimit');return (lo,hi) if lim=='true' else (t+lo,t+hi)
def owner(e,pa):
 while e is not None and L(e.tag)!='MeasurementResults':e=pa.get(e)
 return e
def row(e,pa,ix):
 r=owner(e,pa); comp=[ix[n.text] for n in r.findall('.//q:ActualComponentIds/q:Id',Q)] if r is not None else []
 return dict(actual=e.get('id'),item=txt(e,'q:CharacteristicItemId'),value=txt(e,'q:Value'),status=txt(e,'.//q:CharacteristicStatusEnum'),result=r.get('id') if r is not None else None,components=[n.get('id') for n in comp],serials=[txt(n,'q:SerialNumber') for n in comp])
R={n:read(n) for n in ['Box_FAIR.qif','Box_incoming.qif','Cover_FAIR.qif','Cover_incoming.qif','Cover_reference_incoming.qif']}
report={}
manifest=json.loads((B/'evaluation/protected/input_manifest.json').read_text());identity=[]
for m in manifest:
 p=I/m['file']
 if m['file']=='Box_reference_incoming.qif':continue
 data=p.read_bytes();identity.append(dict(file=m['file'],sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),manifest_match=hashlib.sha256(data).hexdigest()==m['sha256'],archive=m['archive'],member=m['member']))
(O/'identities.json').write_text(json.dumps(identity,indent=2))
for j,src,dst,did in [('H1','Box_FAIR.qif','Box_incoming.qif','33'),('H2','Cover_FAIR.qif','Cover_incoming.qif','23')]:
 r,ix,pa=R[src];di=R[dst][1]
 ids=['14','20','26','32'] if j=='H1' else [e.get('id') for e in r.iter() if L(e.tag)=='DiameterCharacteristicItem' and txt(chain(ix,e.get('id'))[1],'q:TargetValue')=='4.5']
 rows=[row(e,pa,ix) for e in r.iter() if L(e.tag)=='DiameterCharacteristicActual' and txt(e,'q:CharacteristicItemId') in ids]
 lo,hi=interval(di,did);vals=[D(x['value']) for x in rows]
 badmm=[x for x in rows if not lo<=D(x['value'])<=hi];badformal=[x for x in rows if not lo<=D(x['value'])*1000<=hi]
 for x in rows:x['mm_hypothesis_pass']=lo<=D(x['value'])<=hi;x['formal_pass']=lo<=D(x['value'])*1000<=hi
 with (O/(j+'_witness.csv')).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 report[j]=dict(ids=ids,source_chains=[list(map(flat,chain(ix,x))) for x in ids],destination_chain=list(map(flat,chain(di,did))),interval_mm=list(map(str,[lo,hi])),count=len(rows),result_count=len({x['result'] for x in rows}),range_raw=list(map(str,[min(vals),max(vals)])),status_counts=dict(collections.Counter(x['status'] for x in rows)),formal_fail_count=len(badformal),mm_hypothesis_fail_count=len(badmm),mm_counterexample=badmm[:3],min_witness=rows[vals.index(min(vals))],max_witness=rows[vals.index(max(vals))],per_item={i:dict(n=sum(x['item']==i for x in rows),low=str(min(D(x['value']) for x in rows if x['item']==i)),high=str(max(D(x['value']) for x in rows if x['item']==i)),mm_fail=sum(x['item']==i for x in badmm)) for i in ids},has_file_units=r.find('q:FileUnits',Q) is not None,value_attribute_sets=list({tuple(sorted(e.find('q:Value',Q).attrib.items())) for e in r.iter() if L(e.tag)=='DiameterCharacteristicActual' and txt(e,'q:CharacteristicItemId') in ids}))
 print(j,json.dumps({k:v for k,v in report[j].items() if k!='source_chains'}))
 print(j,'SOURCE CHAINS',[(a[0]['id'],a[1]['id'],a[2]['id'],a[2]['leaves']) for a in report[j]['source_chains']])
r,ix,pa=R['Box_incoming.qif'];seen=set();queue=['534'];objs=[]
while queue:
 id=queue.pop(0)
 if id in seen:continue
 seen.add(id);e=ix[id];objs.append(flat(e))
 for n in e.iter():
  if not len(n) and L(n.tag).endswith('Id') and (n.text or '').strip() in ix:queue.append(n.text.strip())
mr=owner(ix['534'],pa)
parents=[E.tostring(e,encoding='unicode') for e in mr if L(e.tag) not in ['CharacteristicActuals','FeatureActuals']]
compids=[n.text for n in mr.findall('.//q:ActualComponentIds/q:Id',Q)]
report['H4']=dict(objects=objs,measurement_result=mr.attrib,parent_fields=parents,components=[flat(ix[id]) for id in compids])
print('H4',json.dumps(report['H4']))
a=R['Cover_incoming.qif'];z=R['Cover_reference_incoming.qif']
differing=[]
for id,e in a[1].items():
 if id in z[1] and E.tostring(e)!=E.tostring(z[1][id]):
  ee=E.fromstring(E.tostring(e));zz=E.fromstring(E.tostring(z[1][id]))
  for n in list(ee.iter())+list(zz.iter()):n.tail=None;n.text=(n.text or '').strip() or None
  if E.tostring(ee)!=E.tostring(zz):differing.append((id,L(e.tag)))
report['H3']=dict(differing_objects=differing,text_diff='\n'.join(difflib.unified_diff((I/'Cover_incoming.qif').read_text().splitlines(),(I/'Cover_reference_incoming.qif').read_text().splitlines())))
print('H3',json.dumps(report['H3']))
for id,t in differing:
 if len(E.tostring(a[1][id]))<4000:print('H3 OBJECT',id,E.tostring(a[1][id],encoding='unicode'),E.tostring(z[1][id],encoding='unicode'))
print('ALL IDENTITY MATCH',all(x['manifest_match'] for x in identity))
report['revisions']={n:dict(root=r.attrib,qp_id=txt(r,'q:QPId'),creation=txt(r,'q:Version/q:TimeCreated'),products=[(L(e.tag),(e.text or '').strip()) for e in r.findall('q:Product',Q)[0].iter() if L(e.tag) in ['Name','Version','ModelNumber'] and not len(e)]) for n,(r,ix,pa) in R.items()}
(O/'analysis.json').write_text(json.dumps(report,indent=2));print('REVISIONS',json.dumps(report['revisions']))
