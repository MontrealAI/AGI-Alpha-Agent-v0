from pathlib import Path
from collections import Counter
from decimal import Decimal as D
import xml.etree.ElementTree as ET
import json
B=Path('studies/agi-alpha-opportunity-discovery-v4');I=B/'evaluation/protected/inputs';O=B/'expertise/E';N={'q':'http://qifstandards.org/xsd/qif2'}
def t(e):return e.tag.rsplit('}',1)[-1]
def compact(e):
 if e is None:return None
 return {'tag':t(e),**e.attrib,**({'text':e.text.strip()} if e.text and e.text.strip() else {}),**({'children':[compact(c) for c in e]} if len(e) else {})}
def v(e,k):return e.findtext('q:'+k,namespaces=N)
def read(f):
 r=ET.parse(I/f).getroot();return r,{e.get('id'):e for e in r.iter() if e.get('id')},{c:p for p in r.iter() for c in p}
def interval(ix,id):
 item=ix[id]; nom=ix[v(item,'CharacteristicNominalId')]; de=ix[v(nom,'CharacteristicDefinitionId')];tol=de.find('q:Tolerance',N)
 vals={t(e):e.text for e in tol};target=D(v(nom,'TargetValue'));lo=D(vals['MinValue']);hi=D(vals['MaxValue']);limit=vals.get('DefinedAsLimit') in ('true','1')
 return (lo,hi) if limit else (target+lo,target+hi)
def result_of(e,par):
 while e in par:
  e=par[e]
  if t(e)=='MeasurementResults':return e
 return None
out=[]
def emit(k,x):out.append(k+' '+json.dumps(x,ensure_ascii=False))
for line in (O/'focused_analysis.log').read_text().splitlines():
 if line.startswith(('CHAIN FILE','OBJECT','H1 SUMMARY')):emit('EVIDENCE',line)
s=ET.parse(B/'instrument/QIF_2_1_Units.xsd').getroot()
for e in s:
 if e.get('name') in {'LinearValueType','ActualLinearValueType'}:emit('UNIT RULE',compact(e))
for source,dest,ids,did,label in [('Box_FAIR.qif','Box_incoming.qif',{'14','20','26','32'},'33','H1'),('Cover_FAIR.qif','Cover_incoming.qif',set(),'23','H2')]:
 r,ix,par=read(source); dr,di,dp=read(dest)
 if label=='H2':ids={e.get('id') for e in r.iter() if t(e)=='DiameterCharacteristicItem' and v(ix[v(e,'CharacteristicNominalId')],'TargetValue')=='4.5'}
 actuals=[e for e in r.iter() if t(e).endswith('CharacteristicActual') and v(e,'CharacteristicItemId') in ids];lo,hi=interval(di,did)
 records=[]
 for e in actuals:
  value=D(v(e,'Value'));res=result_of(e,par);comps=res.find('q:ActualComponentIds',N);cids=[z.text for z in comps] if comps is not None else []
  records.append({'actual':e.get('id'),'item':v(e,'CharacteristicItemId'),'value':str(value),'pass_formal':lo<=value*1000<=hi,'pass_mm_hypothesis':lo<=value<=hi,'result':res.get('id'),'components':cids,'serials':[ix[c].findtext('.//q:SerialNumber',namespaces=N) for c in cids],'status':e.findtext('.//q:CharacteristicStatusEnum',namespaces=N)})
 (O/(label.lower()+'_verified_values.json')).write_text(json.dumps(records,indent=2))
 values=[D(x['value']) for x in records];report={'source':source,'destination':dest,'items':sorted(ids,key=int),'destination_chain':[did,v(di[did],'CharacteristicNominalId'),v(di[v(di[did],'CharacteristicNominalId')],'CharacteristicDefinitionId')],'dest_interval_mm':[str(lo),str(hi)],'dest_interval_m':[str(lo/D(1000)),str(hi/D(1000))],'source_intervals':{i:list(map(str,interval(ix,i))) for i in sorted(ids,key=int)},'records':len(records),'raw_range':[str(min(values)),str(max(values))],'formal_m_to_mm_range':[str(min(values)*1000),str(max(values)*1000)],'formal_pass':sum(z['pass_formal'] for z in records),'hypothesis_pass':sum(z['pass_mm_hypothesis'] for z in records),'source_pass_status_count':sum(z['status']=='PASS' for z in records),'hypothesis_extrema_check':lo<=min(values)<=max(values)<=hi,'formal_fail_witness':next((z for z in records if not z['pass_formal']),None),'hypothesis_fail_witnesses':[z for z in records if not z['pass_mm_hypothesis']][:12]}
 emit(label+' CALCULATION',report)
r,ix,par=read('Box_incoming.qif');a=ix['534'];res=result_of(a,par);emit('H4 PARENT',{'tag':t(res),'id':res.get('id'),'small_fields':[compact(c) for c in res if len(ET.tostring(c))<2500]})
for c in res.findall('q:ActualComponentIds/q:Id',N):emit('H4 COMPONENT',compact(ix[c.text]))
emit('H4 FAILS',[compact(e) for e in res.iter() if t(e).endswith('CharacteristicActual') and e.findtext('.//q:CharacteristicStatusEnum',namespaces=N)=='FAIL'])
for f in ['Box_FAIR.qif','Box_incoming.qif','Cover_FAIR.qif','Cover_incoming.qif']:
 r,ix,par=read(f);emit('REVISION/STANDARD '+f,[compact(e) for e in r.iter() if t(e) in {'Version','FormalStandard','Header','Part','PartSet','PreInspectionTraceability'} and len(ET.tostring(e))<4000])
# The graph uses generated node names, so inspect by stored XML _id literals.
for f,ids in [('Cover_integrated.owl',{'571','570'}),('Box_integrated.owl',{'534','533','27'})]:
 r=ET.parse(I/f).getroot(); nodes={next(iter(e.attrib.values()),''):e for e in r};matches=[e for e in r if any(t(c)=='_id' and (c.text or '').strip() in ids for c in e)]
 emit('GRAPH ID MATCH '+f,[compact(e) for e in matches])
 # expand direct referenced slots once, excluding ontology types
 for e in matches:
  for c in e:
   if t(c)=='type':continue
   for z in c.attrib.values():
    if z in nodes:emit('GRAPH SLOT '+f,compact(nodes[z]))
log='\n'.join(out);(O/'final_checks.log').write_text(log);print(log)
