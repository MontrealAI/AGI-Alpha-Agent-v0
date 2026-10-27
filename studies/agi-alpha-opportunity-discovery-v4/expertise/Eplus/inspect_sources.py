from pathlib import Path
import xml.etree.ElementTree as ET
import hashlib, json, difflib, collections
B=Path('studies/agi-alpha-opportunity-discovery-v4')
I=B/'evaluation/protected/inputs'
O=B/'expertise/Eplus'
local=lambda s:s.rsplit('}',1)[-1]
print('SOURCE MANIFEST')
print((B/'evaluation/protected/input_manifest.json').read_text())
print('EXACT UNIT SCHEMA')
print((B/'instrument/QIF_2_1_Units.xsd').read_text())
for name in ['Box_FAIR.qif','Box_incoming.qif','Cover_FAIR.qif','Cover_incoming.qif','Cover_reference_incoming.qif']:
 p=I/name; data=p.read_bytes(); r=ET.fromstring(data); ix={e.get('id'):e for e in r.iter() if e.get('id')}
 print('\nFILE',name,'SHA256',hashlib.sha256(data).hexdigest(),'BYTES',len(data),'ROOT',r.attrib)
 print('TOP',[(local(e.tag),e.attrib,len(e)) for e in r])
 counts=collections.Counter(local(e.tag) for e in r.iter())
 print('COUNTS', {k:v for k,v in counts.items() if any(t in k for t in ['Actual','Result','Unit','Status','Version','Component'])})
 for e in r:
  if local(e.tag) not in ['Product','Features','Characteristics','MeasurementResults','MeasurementsResults','DatumReferenceFrames','Geometry','Topology'] and len(ET.tostring(e))<10000: print('HEADER',ET.tostring(e,encoding='unicode'))
 ids={'Box_FAIR.qif':['14','20','26','32'],'Box_incoming.qif':['33','534'],'Cover_incoming.qif':['23']}.get(name,[])
 if name=='Cover_FAIR.qif':
  for e in r.iter():
   if local(e.tag)=='DiameterCharacteristicItem':
    nr=next((n.text for n in e.iter() if local(n.tag)=='CharacteristicNominalId'),None)
    if nr and nr in ix and any(local(n.tag)=='TargetValue' and n.text=='4.5' for n in ix[nr].iter()): ids.append(e.get('id'))
 seen=set(); todo=list(ids)
 while todo:
  i=todo.pop(0)
  if i in seen or i not in ix: continue
  seen.add(i); e=ix[i]; print('OBJECT',i,ET.tostring(e,encoding='unicode'))
  if len(seen)<30:
   for n in e.iter():
    if local(n.tag).endswith('Id') and (n.text or '').strip() in ix: todo.append(n.text.strip())
 for tag in ['MeasurementResult','MeasurementResults','MeasurementsResults','DiameterCharacteristicActual','LinearCharacteristicActual','CircularityCharacteristicActual','Component','Part','Units']:
  es=[e for e in r.iter() if local(e.tag)==tag]
  if es:
   e=es[0]; s=ET.tostring(e,encoding='unicode'); print('SAMPLE',tag,s if len(s)<4500 else s[:2000]+'...[TRUNCATED]')
a=(I/'Cover_incoming.qif').read_text().splitlines();z=(I/'Cover_reference_incoming.qif').read_text().splitlines()
print('\nCOVER INCOMING DIFF incoming -> reference')
print('\n'.join(difflib.unified_diff(a,z,fromfile='Cover_incoming.qif',tofile='Cover_reference_incoming.qif',n=4)))
for name in ['Box_integrated.owl','Cover_integrated.owl','Box_AP242.STP','Cover_AP242.STP']:
 p=I/name;d=p.read_bytes();s=d.decode(errors='replace')
 print('\nASSET',name,'SHA256',hashlib.sha256(d).hexdigest(),'BYTES',len(d))
 if name.endswith('.STP'):print(s[:2200])
 else:
  r=ET.fromstring(d); print('OWL TAGS',collections.Counter(local(e.tag) for e in r.iter()).most_common(35));print('OWL HEAD',s[:6500])
  matches=[line for line in s.splitlines() if any(t in line.lower() for t in ['sha256','hash','sourcefile','source_file','incoming','reference','provenance','qualified','qualification'])]
  print('OWL PROVENANCE MATCHES','\n'.join(matches[:100]))
