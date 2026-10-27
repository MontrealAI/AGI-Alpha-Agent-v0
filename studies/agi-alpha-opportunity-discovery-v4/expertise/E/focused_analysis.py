from pathlib import Path
from collections import Counter
from decimal import Decimal as D
import xml.etree.ElementTree as ET
import hashlib,json,difflib
B=Path('studies/agi-alpha-opportunity-discovery-v4'); I=B/'evaluation/protected/inputs'; O=B/'expertise/E'; ns={'q':'http://qifstandards.org/xsd/qif2'}
def tag(e):return e.tag.rsplit('}',1)[-1]
def small(e):
 if e is None:return None
 return {'tag':tag(e),**e.attrib,**({'text':e.text.strip()} if e.text and e.text.strip() else {}),**({'children':[small(c) for c in e]} if len(e) else {})}
lines=[]
def out(label,x):lines.append(label+' '+json.dumps(x,ensure_ascii=False))
def val(e,key):return e.findtext('q:'+key,namespaces=ns)
def ctx(r):return ({e.get('id'):e for e in r.iter() if e.get('id')},{c:p for p in r.iter() for c in p})
def chain(ix,ids):
 seen=set(); todo=list(ids)
 while todo:
  i=todo.pop(0)
  if i in seen:continue
  seen.add(i); e=ix.get(i)
  if e is None:out('MISSING REF',i);continue
  out('OBJECT',small(e))
  for c in e.iter():
   if (tag(c).endswith('Id') or tag(c)=='Id') and c.text and c.text.strip() in ix:todo.append(c.text.strip())
def actuals(r,ids):return [e for e in r.iter() if tag(e).endswith('CharacteristicActual') and val(e,'CharacteristicItemId') in ids]
def statuses(e):return [(tag(c),(c.text or '').strip()) for c in e.iter() if 'Status' in tag(c) and len(c)==0]
def ancestry(e,par):
 a=[]
 while e in par:
  e=par[e]
  if tag(e)=='QIFDocument':break
  a.append({'tag':tag(e),**e.attrib,'fields':[small(c) for c in e if len(ET.tostring(c))<1300]})
 return a
roots={name:ET.parse(I/name).getroot() for name in ['Box_FAIR.qif','Box_incoming.qif','Cover_FAIR.qif','Cover_incoming.qif','Cover_reference_incoming.qif']}
manifest=json.loads((B/'evaluation/protected/input_manifest.json').read_text())
for entry in manifest:
 name=entry['file']
 if name=='Box_reference_incoming.qif':continue
 p=I/name; actual=hashlib.sha256(p.read_bytes()).hexdigest();out('IDENTITY',{'file':name,'bytes':p.stat().st_size,'sha256':actual,'matches_manifest':actual==entry['sha256']})
for name,r in roots.items():
 out('QIF META',{'name':name,'root_attrs':r.attrib,'top':[(tag(e),e.attrib) for e in r]})
 out('UNITS/STANDARDS',{'name':name,'objects':[small(e) for e in r.iter() if tag(e) in {'FileUnits','Standard','Standards','StandardId','InspectionScope','QIFDocumentHeader'}]})
 out('REVISION/SPECIMEN FIELDS',{'name':name,'values':[(tag(e),e.attrib,(e.text or '').strip()) for e in r.iter() if any(w in tag(e) for w in ['Revision','Standard','Serial','UUID','QPId'])][:65]})
 out('KEY ELEMENT COUNTS',{'name':name,'counts':{k:v for k,v in Counter(tag(e) for e in r.iter()).items() if any(w in k for w in ['Result','Component','PartInstance','Status','CharacteristicNominalId','FeatureItemId'])}})
s=ET.parse(B/'instrument/QIF_2_1_Units.xsd').getroot()
for e in s:
 if e.get('name') in {'LinearValueType','ActualLinearValueType','UnitConversionType','LinearUnitType'}:
  out('SCHEMA SELECTED',small(e))
for name, ids in [('Box_FAIR.qif',['14','20','26','32']),('Box_incoming.qif',['33','534']),('Cover_incoming.qif',['23'])]:
 out('CHAIN FILE',name);r=roots[name];ix,par=ctx(r);chain(ix,ids)
 if name=='Box_incoming.qif':
  out('H4 ANCESTORS',ancestry(ix['534'],par))
  # identify component records and all local fail statuses within containing measurement set
  e=ix['534']
  while e in par and tag(e) not in {'MeasurementResultsSet','MeasurementResult'}:e=par[e]
  out('H4 CONTAINER',{'tag':tag(e),'attrs':e.attrib,'children':[(tag(c),c.attrib) for c in e]})
  out('H4 LOCAL FAILS',[{'id':c.get('id'),'type':tag(c),'item':val(c,'CharacteristicItemId'),'value':val(c,'Value'),'statuses':statuses(c)} for c in e.iter() if c.get('id') and any(t=='FAIL' for _,t in statuses(c)) and tag(c).endswith('Actual')])
r=roots['Box_FAIR.qif'];ix,par=ctx(r);aa=actuals(r,{'14','20','26','32'})
out('H1 ALL RECORDS',[{'actual':e.get('id'),'item':val(e,'CharacteristicItemId'),'value':val(e,'Value'),'attrs':e.find('q:Value',ns).attrib,'status':statuses(e)} for e in aa])
out('H1 SUMMARY',{'count':len(aa),'range':[str(min(D(val(e,'Value')) for e in aa)),str(max(D(val(e,'Value')) for e in aa))],'items':Counter(val(e,'CharacteristicItemId') for e in aa),'status':Counter(tuple(statuses(e)) for e in aa) if False else [statuses(e) for e in aa[:1]]})
r=roots['Cover_FAIR.qif'];ix,par=ctx(r);ids=[]
for e in r.iter():
 if tag(e)=='DiameterCharacteristicItem':
  n=ix.get(val(e,'CharacteristicNominalId')); leaves=[(tag(c),(c.text or '').strip()) for c in n.iter() if len(c)==0]
  if any(t=='4.5' for k,t in leaves if not k.endswith('Id')):
   ids.append(e.get('id'));out('H2 ITEM/NOMINAL',{'item':small(e),'nominal':small(n),'definition':small(ix.get(val(n,'CharacteristicDefinitionId')))})
aa=actuals(r,set(ids));out('H2 SUMMARY',{'items':ids,'count':len(aa),'range':[str(min(D(val(e,'Value')) for e in aa)),str(max(D(val(e,'Value')) for e in aa))],'by_item':[{'item':i,'count':len([e for e in aa if val(e,'CharacteristicItemId')==i]),'range':[str(min(D(val(e,'Value')) for e in aa if val(e,'CharacteristicItemId')==i)),str(max(D(val(e,'Value')) for e in aa if val(e,'CharacteristicItemId')==i))]} for i in ids],'value_attributes':list({tuple(sorted(e.find('q:Value',ns).attrib.items())) for e in aa}),'status_counts':dict(Counter('/'.join(v for k,v in statuses(e)) for e in aa)),'minimum_actuals':[(e.get('id'),val(e,'CharacteristicItemId')) for e in aa if D(val(e,'Value'))==min(D(val(a,'Value')) for a in aa)],'maximum_actuals':[(e.get('id'),val(e,'CharacteristicItemId')) for e in aa if D(val(e,'Value'))==max(D(val(a,'Value')) for a in aa)]})
(O/'h2_values.json').write_text(json.dumps([{'actual':e.get('id'),'item':val(e,'CharacteristicItemId'),'value':val(e,'Value')} for e in aa],indent=2))
a=(I/'Cover_reference_incoming.qif').read_text().splitlines();b=(I/'Cover_incoming.qif').read_text().splitlines();out('H3 TEXT DIFF','\n'.join(difflib.unified_diff(a,b,fromfile='Cover_reference_incoming.qif',tofile='Cover_incoming.qif',n=4)))
for name in ['Cover_incoming.qif','Cover_reference_incoming.qif']:
 ix,par=ctx(roots[name]);out('H3 TARGET OBJECT '+name,small(ix['571']))
 # flatten structural XML by child position to check all substantive changes
 def flat(e,path=''):
  d={path+'/'+tag(e):(e.attrib,(e.text or '').strip())}
  for j,c in enumerate(e):d.update(flat(c,path+'/'+tag(e)+'['+str(j)+']'))
  return d
 globals()[name.split('.')[0]]=flat(roots[name])
x=Cover_incoming;y=Cover_reference_incoming
out('H3 STRUCTURAL DIFF',{'only_incoming':{k:v for k,v in x.items() if k not in y},'only_reference':{k:v for k,v in y.items() if k not in x},'changed':{k:(y[k],v) for k,v in x.items() if k in y and y[k]!=v}})
for name,needles in [('Cover_integrated.owl',['571','570']),('Box_integrated.owl',['534'])]:
 r=ET.parse(I/name).getroot();out('GRAPH META',{'name':name,'root':r.attrib,'top_types':dict(Counter(tag(e) for e in r)),'first_nodes':[small(e) for e in list(r)[:2]]})
 matches=[]
 for e in r:
  a=' '.join(e.attrib.values())
  if any(a.endswith('_'+v) or a.endswith('#'+v) or a.endswith('/'+v) or a.endswith('Id'+v) for v in needles):matches.append(small(e))
 out('GRAPH MATCHES '+name,matches[:12])
 out('GRAPH REFERENCING NODES '+name,[small(e) for e in r if any(any(v in a for v in needles) for c in list(e) for a in c.attrib.values())][:5])
log='\n'.join(lines);(O/'focused_analysis.log').write_text(log);print(log)
