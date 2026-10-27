from pathlib import Path
import xml.etree.ElementTree as E
import json
B=Path('studies/agi-alpha-opportunity-discovery-v4');I=B/'evaluation/protected/inputs';O=B/'expertise/Eplus';L=lambda t:t.rsplit('}',1)[-1];rdf='{http://www.w3.org/1999/02/22-rdf-syntax-ns#}';owl='{http://www.w3.org/2002/07/owl#}';q='{http://www.nist.gov/QIF_ontology#}'
for file,targets in [('Cover_integrated.owl',{'571'}),('Box_integrated.owl',{'29','534','533','604','528'})]:
 r=E.parse(I/file).getroot();ix={e.get(rdf+'about'):e for e in r if e.get(rdf+'about')};sels=[e for e in r if e.tag==owl+'NamedIndividual' and any(L(n.tag)=='_id' and (n.text or '').strip() in targets for n in e)]
 print('\nGRAPH',file)
 for e in sels:
  print('NODE',E.tostring(e,encoding='unicode'))
  if file.startswith('Cover'):
   for n in e:
    if L(n.tag)=='FeatureItemIdsSlot':print('LINK',E.tostring(ix[n.get(rdf+'resource')],encoding='unicode'))
 r0=E.parse(I/('Cover_incoming.qif' if file.startswith('Cover') else 'Box_incoming.qif')).getroot();ns={'q':'http://qifstandards.org/xsd/qif2'}
 print('QIF PREINSPECTION',E.tostring(r0.find('q:PreInspectionTraceability',ns),encoding='unicode'))
