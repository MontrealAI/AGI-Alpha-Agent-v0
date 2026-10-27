from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET
import hashlib, difflib, json
B=Path('studies/agi-alpha-opportunity-discovery-v4')
I=B/'evaluation/protected/inputs'
O=B/'expertise/E'
N={'q':'http://qifstandards.org/xsd/qif2'}
def tag(e): return e.tag.rsplit('}',1)[-1]
def xml(e): return ET.tostring(e,encoding='unicode') if e is not None else 'MISSING'
lines=[]
def emit(*x): lines.append(' '.join(map(str,x)))
manifest=B/'evaluation/protected/input_manifest.json'
emit('MANIFEST',manifest.read_text())
schema=B/'instrument/QIF_2_1_Units.xsd'
emit('UNIT SCHEMA',schema, 'SHA256',hashlib.sha256(schema.read_bytes()).hexdigest(),schema.read_text())
roots={}
for p in sorted(I.iterdir()):
    if p.name not in {'Box_FAIR.qif','Box_incoming.qif','Box_AP242.STP','Box_integrated.owl','Cover_FAIR.qif','Cover_incoming.qif','Cover_reference_incoming.qif','Cover_AP242.STP','Cover_integrated.owl'}: continue
    data=p.read_bytes(); emit('FILE',p.name,'BYTES',len(data),'SHA256',hashlib.sha256(data).hexdigest())
    if p.suffix=='.qif':
        r=ET.fromstring(data); roots[p.name]=r
        emit('ROOT',p.name, r.attrib,'TOP',[(tag(e),e.attrib) for e in r])
        for e in r:
            if tag(e) not in {'Features','Characteristics','MeasurementResults','Product'}: emit('HEADER',p.name,xml(e))
        emit('ELEMENT COUNTS',p.name,Counter(tag(e) for e in r.iter()))
    elif p.suffix=='.owl':
        text=data.decode(); owl=ET.fromstring(data)
        emit('OWL ROOT',p.name,owl.attrib,'TOP COUNT',len(owl))
        for e in owl:
            s=xml(e)
            if any(w in s.lower() for w in ['sha256','hashvalue','file_name','filename','sourcefile','qifdocument','filelocation','ontology','revision','2024','qualified']): emit('OWL METADATA',p.name,s)
        emit('OWL PROPERTY COUNTS',p.name,Counter(tag(e) for e in owl.iter()))
    else:
        txt=data.decode(errors='replace'); emit('STEP HEADER',p.name,txt[:txt.find('ENDSEC;')+7])
for name, ids in {'Box_FAIR.qif':['14','20','26','32'], 'Box_incoming.qif':['33','534'],'Cover_incoming.qif':['23']}.items():
    r=roots[name]; ix={e.get('id'):e for e in r.iter() if e.get('id')}
    seen=set(); todo=list(ids)
    while todo:
        ident=todo.pop(0)
        if ident in seen:continue
        seen.add(ident); e=ix.get(ident); emit('SELECTED OBJECT',name,ident,xml(e))
        if e is not None:
            for c in e.iter():
                if c.text and c.text.strip() in ix and (tag(c).endswith('Id') or tag(c) in {'Id'}):todo.append(c.text.strip())
    targets=set(ids)
    for e in r.iter():
        if tag(e).endswith('Actual') and any(c.text and c.text.strip() in targets for c in e.iter() if tag(c).endswith('Id')): emit('RELATED ACTUAL',name,xml(e))
    if name=='Box_incoming.qif':
        for e in r.iter():
            if tag(e) in {'MeasurementResult','MeasurementResultsSet','MeasurementResults','Component','PhysicalPartInstance','PartInstance','InspectionStatus','MeasurementStatus','OverallStatus'}: 
                if tag(e)=='MeasurementResults':emit('RESULTS CHILDREN',[(tag(c),c.attrib) for c in e]);continue
                if any(c.get('id')=='534' for c in e.iter()):
                    emit('ANCESTOR 534',tag(e),e.attrib)
                    for c in e:
                        if tag(c) not in {'CharacteristicActuals','FeatureActuals'}:emit('ANCESTOR CHILD',tag(c),xml(c)[:18000])
                elif len(xml(e))<2000:emit('STATUS/COMPONENT',xml(e))
r=roots['Cover_FAIR.qif']; ix={e.get('id'):e for e in r.iter() if e.get('id')}; targets=[]
for e in r.iter():
    if tag(e)=='DiameterCharacteristicItem':
        nom=e.find('q:NominalId',N); n=ix.get(nom.text) if nom is not None else None
        emit('COVER DIAMETER ITEM',xml(e),'NOMINAL',xml(n))
        if n is not None: 
            for c in n.iter():
                if c.text and c.text.strip() in ix and tag(c).endswith('Id'):emit('COVER DEFINITION',xml(ix[c.text.strip()]))
for e in r.iter():
    if tag(e).endswith('CharacteristicActual'):emit('COVER ACTUAL',xml(e))
a=(I/'Cover_reference_incoming.qif').read_text().splitlines(); b=(I/'Cover_incoming.qif').read_text().splitlines()
emit('COVER DIFF','\n'.join(difflib.unified_diff(a,b,fromfile='Cover_reference_incoming.qif',tofile='Cover_incoming.qif',n=5)))
log='\n'.join(lines); (O/'exploration.log').write_text(log)
print(log)
