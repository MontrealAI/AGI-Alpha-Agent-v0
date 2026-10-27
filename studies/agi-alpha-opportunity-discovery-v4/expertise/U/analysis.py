from pathlib import Path
import xml.etree.ElementTree as ET
from decimal import Decimal as D
from collections import Counter
import hashlib, json
BASE=Path(__file__).resolve().parents[2]
INPUT=BASE/'evaluation/protected/inputs'
OUT=Path(__file__).parent
Q='{http://qifstandards.org/xsd/qif2}'
RDF='{http://www.w3.org/1999/02/22-rdf-syntax-ns#}'
O='{http://www.nist.gov/QIF_ontology#}'
def load(name):
    r=ET.parse(INPUT/name).getroot()
    return r, {e.get('id'):e for e in r.iter() if e.get('id')}
def get(e,path):
    return e.findtext('/'.join(Q+x for x in path.split('/')),default='')
def name(e):return e.tag.rsplit('}',1)[-1]
def xml(e):return ET.tostring(e,encoding='unicode')
summary={}
for source,items,destination,dest_id in [('Box_FAIR.qif',['14','20','26','32'],'Box_incoming.qif','33'),('Cover_FAIR.qif',None,'Cover_incoming.qif','23')]:
    root,idx=load(source);dr,di=load(destination)
    if items is None:
        items=[i for i,e in idx.items() if name(e)=='DiameterCharacteristicItem' and get(idx[get(e,'CharacteristicNominalId')],'TargetValue')=='4.5']
    n=di[get(di[dest_id],'CharacteristicNominalId')];de=di[get(n,'CharacteristicDefinitionId')]
    target=D(get(n,'TargetValue'));lo=D(get(de,'Tolerance/MinValue'));hi=D(get(de,'Tolerance/MaxValue'))
    if get(de,'Tolerance/DefinedAsLimit')=='false':lo+=target;hi+=target
    records=[(e.get('id'),get(e,'CharacteristicItemId'),D(get(e,'Value')),get(e,'Status/CharacteristicStatusEnum')) for e in root.iter() if name(e)=='DiameterCharacteristicActual' and get(e,'CharacteristicItemId') in items]
    summary[source]={'items':items,'count':len(records),'range':[str(min(x[2] for x in records)),str(max(x[2] for x in records))],'destination_interval':[str(lo),str(hi)],'hypothetical_failures':[[a,i,str(v),s] for a,i,v,s in records if not lo<=v<=hi],'formal_failures':sum(not lo<=v*1000<=hi for a,i,v,s in records),'per_item_pass_count':{i:sum(lo<=v<=hi for a,j,v,s in records if j==i) for i in items},'statuses':dict(Counter(x[3] for x in records))}
r,idx=load('Box_incoming.qif');parents={c:p for p in r.iter() for c in p};e=idx['534']
while name(e)!='MeasurementResults':e=parents[e]
summary['H4']={'result_id':e.get('id'),'result_status':get(e,'InspectionStatus/InspectionStatusEnum'),'actual_component_id':get(e,'ActualComponentIds/Id'),'component':xml(idx[get(e,'ActualComponentIds/Id')]),'recorded_characteristic_status_counts':dict(Counter(get(x,'Status/CharacteristicStatusEnum') for x in e.iter() if name(x).endswith('CharacteristicActual'))),'trace':{i:xml(idx[i]) for i in ['534','33','32','31','533','29','28','27']}}
r,idx=load('Cover_incoming.qif');ref,refidx=load('Cover_reference_incoming.qif');parents={c:p for p in r.iter() for c in p}
empty=[e for e in r.iter() if name(e)=='FeatureItemIds' and not len(e)]
summary['H3_changes']=[]
graph=ET.parse(INPUT/'Cover_integrated.owl').getroot()
for e in empty:
    owner=parents[e];oid=owner.get('id');refowner=refidx.get(oid)
    if refowner is not None and refowner.find(Q+'FeatureItemIds') is None:
        individuals=[x for x in graph if x.findtext(O+'_id')==oid and x.find(RDF+'type') is not None and x.find(RDF+'type').get(RDF+'resource','').endswith('#'+name(owner))]
        summary['H3_changes'].append({'owner':xml(owner),'reference_owner':xml(refowner),'graph_individuals':[xml(x) for x in individuals]})
# Detect all structural differences, ignoring only whitespace and attribute order.
def diff(a,b,path=''):
    changes=[];path+='/'+name(a)+(('[id='+a.get('id')+']') if a.get('id') else '')
    if a.tag!=b.tag or a.attrib!=b.attrib or (a.text or '').strip()!=(b.text or '').strip():changes.append((path,'element content',a.attrib,b.attrib,(a.text or '').strip(),(b.text or '').strip()))
    ac=list(a);bc=list(b)
    if len(ac)!=len(bc):
        changes.append((path,'child structures',[name(x) for x in ac],[name(x) for x in bc]))
        ac=[x for x in ac if name(x)!='FeatureItemIds'];bc=[x for x in bc if name(x)!='FeatureItemIds']
    for x,y in zip(ac,bc):changes.extend(diff(x,y,path))
    return changes
summary['H3_structural_diff']=diff(ref,r)
summary['H3_graph_qpids']=[(x.get(RDF+'about'),c.text) for x in graph for c in x if name(c)=='QPId']
summary['identities']={f:{'bytes':(INPUT/f).stat().st_size,'sha256':hashlib.sha256((INPUT/f).read_bytes()).hexdigest()} for f in ['Cover_incoming.qif','Cover_reference_incoming.qif','Cover_FAIR.qif','Cover_integrated.owl']}
(OUT/'analysis_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
