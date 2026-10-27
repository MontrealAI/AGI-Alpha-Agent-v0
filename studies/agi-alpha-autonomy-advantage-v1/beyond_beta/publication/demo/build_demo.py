# SPDX-License-Identifier: Apache-2.0
"""Build a portable evidence-bound BeyondBeta demonstration. No economic execution."""
from pathlib import Path
import hashlib
import html as html_tools
import json
import re
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[3]
LANE=ROOT/'beyond_beta'
HERE=Path(__file__).resolve().parent

def record(relative, required=True):
    path=LANE/relative
    if not path.exists():
        if required:raise FileNotFoundError(path)
        return None,None
    raw=path.read_bytes()
    return json.loads(raw),{'path':'beyond_beta/'+relative,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}

protocol,pbind=record('protocol.json')
screen,sbind=record('calibration/market-screen.json')
external_sources,ebind=record('calibration/sources.json')
frontier,frontier_bind=record('calibration/frontier-configuration.json')
sources,fbind=record('foundations/source-provenance.json')
v93,vbind=record('foundations/v93-interface-probes.json')
review1,rbind1=record('foundations/graph-review-accounting-v1.json',False)
review2,rbind2=record('foundations/graph-review-additional-accounting-v1.json',False)
controls,cbind=record('validation/graph-controls.json',False)
coverage,coveragebind=record('foundations/LIFECYCLE_TEST_SPEC.json')

# A later, reviewed publication binding may populate this separate, normalized
# data file from the registered result closure. The builder never selects wins.
binding,binding_hash=record('publication/demo/registered-results.json',False)
if binding is not None:
    if binding.get('schema')!='beyond-beta-demo-results/v1':raise ValueError('Unknown result binding schema')
    if binding.get('demonstrationPreselection')!=protocol['experiment']['demonstrationPreselection']:raise ValueError('Changed prospective demonstration selection')
    for entry in binding.get('boundFiles',[]):
        path=ROOT/entry['path']
        with path.open('rb') as stream:actual_hash=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual_hash!=entry['sha256']:raise ValueError('Result/source binding mismatch: '+entry['path'])
    if not binding.get('boundFiles'):raise ValueError('Final results require immutable source/result binding')

data={
 'schema':'beyond-beta-portable-demo/v1',
 'builtAt':datetime.now(timezone.utc).isoformat(),
 'status':'REGISTERED_RESULTS' if binding else 'PENDING_RESULTS',
 'binding':[x for x in [pbind,sbind,ebind,frontier_bind,fbind,vbind,rbind1,rbind2,cbind,coveragebind,binding_hash] if x],
 'protocol':protocol,'screen':screen,
 'externalSourceRegister':external_sources,'frontierConfiguration':frontier,
 'sources':[{k:v for k,v in s.items() if k not in {'libraryFileId'}} for s in sources['sources']],
 'sourceInspection':{'exactSuppliedV974EqualsOfficial':sources['officialSuppliedV974ByteIdentity'],'v93':v93},
 'graphReviews':[r for r in [review1,review2] if r],
 'graphControls':controls,
 'prospectiveCoverage':coverage,
 'actualEvidence':{'acceptedCommercialJobs':0,'collectedRevenueUsd':0,'completeStudyCostUsd':None,'liveEns':False,'liveSettlement':False},
 'results':binding,
 'preselected':protocol['experiment']['demonstrationPreselection'],
 'artifactBoundary':'All economic quantities are simulated or assumed unless explicitly stated. Local fixture controls are executed code observations, not real capability qualification or commercial sales.'
}
raw=json.dumps(data,ensure_ascii=False,separators=(',',':'))
(HERE/'demo-data.json').write_text(raw+'\n')
copy=json.loads((HERE/'copy.json').read_text())
if set(copy['en'])!=set(copy['fr']):raise ValueError('Translation keys differ')
template=(HERE/'template.html').read_text()
# Keep the research overview readable in non-script previews as well.
template=re.sub(r'(<([A-Za-z0-9]+)\b[^>]*\bdata-i18n="([^"]+)"[^>]*>)[\s\S]*?(</\2>)',lambda m:m.group(1)+html_tools.escape(copy['en'][m.group(3)])+m.group(4),template)
html=template.replace('__DEMO_DATA__',raw.replace('<','\\u003c')).replace('__DEMO_COPY__',json.dumps(copy,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c'))
if '__DEMO_' in html:raise ValueError('Unresolved template token')
(HERE/'index.html').write_text(html)
manifest={'schema':'beyond-beta-demo-binding/v1','status':data['status'],'builtAt':data['builtAt'],'defaultSelection':data['preselected'],'boundInputFiles':data['binding'],'outputSha256':hashlib.sha256(html.encode()).hexdigest(),'translationKeys':len(copy['en']),'economicWorldsExecutedByBuilder':0}
(HERE/'binding-record.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest))
