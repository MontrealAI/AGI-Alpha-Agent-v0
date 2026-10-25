#!/usr/bin/env python3
"""Build one offline HTML companion from unchanged upstream modules and recorded evidence."""
import base64
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
REF = 'f836f06e8351e64db1da770e16e304b5feb01f28'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read_json(path):
    return json.loads((BASE / path).read_text())

def b64(data):
    return base64.b64encode(data).decode('ascii')

def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def main():
    manifest = {entry['path']: entry for entry in read_json('protocol/UPSTREAM_SOURCE_MANIFEST.json')}
    module_paths = ['examples/successor-alpha/engine.mjs', 'examples/successor-alpha/research.mjs', 'examples/ti-guide/guide.mjs']
    originals, identities = {}, []
    for path in module_paths:
        data = (BASE / 'upstream' / path).read_bytes()
        if sha(data) != manifest[path]['actual_sha256']:
            raise ValueError('Original source identity mismatch: ' + path)
        originals[path] = data.decode('utf-8')
        identities.append({'path': path, 'sha256': sha(data), 'bytes': len(data)})
    identities.sort(key=lambda item: item['path'])
    def uri(text):
        return 'data:text/javascript;base64,' + b64(text.encode('utf-8'))
    alpha_uri = uri(originals[module_paths[0]])
    research = originals[module_paths[1]]
    assert research.count("from './engine.mjs'") == 1
    research_uri = uri(research.replace("from './engine.mjs'", "from '" + alpha_uri + "'"))
    guide = originals[module_paths[2]]
    assert guide.count("from '../successor-alpha/engine.mjs'") == 1
    assert guide.count("from '../successor-alpha/research.mjs'") == 1
    guide_uri = uri(guide.replace("from '../successor-alpha/engine.mjs'", "from '" + alpha_uri + "'").replace("from '../successor-alpha/research.mjs'", "from '" + research_uri + "'"))
    analysis = read_json('raw/ANALYSIS.json')
    tool = (BASE / 'raw/showcase/output/successor-tool.mjs').read_bytes()
    receipt = read_json('raw/showcase/receipt.json')
    assert sha(tool) == receipt['retained_tool_created_sha256']
    evidence_paths = [
        'raw/ANALYSIS.json', 'raw/ENVIRONMENT.json', 'raw/primary/results.json', 'raw/scale/results.json',
        'raw/controls/controls.json', 'raw/controls/source-identity.json', 'raw/controls/evidence-manifest.json',
        'raw/showcase/brief.json', 'raw/showcase/input.json', 'raw/showcase/receipt.json', 'raw/showcase/acceptance.json',
        'raw/showcase/OUTPUT_MANIFEST.json', 'raw/showcase/output/summary.json',
        'raw/successor-report/receipt.json', 'raw/successor-report/acceptance.json', 'raw/successor-report/lineage.json',
        'raw/successor-report/output/analysis.json', 'protocol/PROTOCOL.md', 'protocol/PROTOCOL_CONTROLS.md',
        'protocol/UPSTREAM_SOURCE_MANIFEST.json', 'browser/LICENSE',
    ]
    memory = io.BytesIO()
    evidence_manifest = []
    with zipfile.ZipFile(memory, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in evidence_paths:
            data = (BASE / path).read_bytes()
            info = zipfile.ZipInfo(path, date_time=(2026, 10, 25, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
            evidence_manifest.append({'path': path, 'sha256': sha(data), 'bytes': len(data)})
        archive.writestr('README.txt', 'Recorded evidence subset bundled with the offline browser companion. The complete reproduction companion contains the remaining per-job inputs, outputs, code, and logs. These are local machine-accepted observations; no new human trial was run.\n')
        archive.writestr('MANIFEST.json', json.dumps(evidence_manifest, indent=2) + '\n')
    delivery = (BASE / 'raw/showcase/delivery.zip').read_bytes()
    payload = {
        'builtUTC': datetime.now(timezone.utc).isoformat(), 'sourceCommit': REF,
        'release': 'v1.43.0', 'sourceFiles': identities,
        'sourceHash': sha(canonical(identities).encode('utf-8')),
        'moduleBundling': 'Original source preserved; only static relative import specifiers replaced with data: module URLs.',
        'analysis': analysis, 'controls': read_json('raw/controls/controls.json'),
        'publicInput': read_json('raw/showcase/input.json'), 'publicBrief': read_json('raw/showcase/brief.json'),
        'publicSummary': read_json('raw/showcase/output/summary.json'),
        'publicAcceptance': read_json('raw/showcase/acceptance.json'),
        'successorSummary': read_json('raw/successor-report/output/analysis.json'),
        'tool': {'base64': b64(tool), 'sha256': sha(tool), 'bytes': len(tool)},
        'delivery': {'base64': b64(delivery), 'sha256': sha(delivery), 'bytes': len(delivery)},
        'evidence': {'base64': b64(memory.getvalue()), 'sha256': sha(memory.getvalue()), 'files': evidence_manifest},
    }
    template = (HERE / 'template.html').read_text()
    assert all(template.count(marker) == 1 for marker in ['__ALPHA_MODULE__', '__GUIDE_MODULE__', '__PAYLOAD__'])
    html = template.replace('__ALPHA_MODULE__', alpha_uri).replace('__GUIDE_MODULE__', guide_uri).replace('__PAYLOAD__', json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c'))
    destination = HERE / 'AGI_ALPHA_Work_Economics_Demo.html'
    destination.write_text(html)
    identity = {'path': destination.name, 'sha256': sha(destination.read_bytes()), 'bytes': destination.stat().st_size,
                'builtUTC': payload['builtUTC'], 'templateSha256': sha((HERE / 'template.html').read_bytes()),
                'builderSha256': sha(Path(__file__).read_bytes()), 'originalModuleIdentities': identities,
                'retainedToolSha256': sha(tool), 'analysisSha256': sha((BASE / 'raw/ANALYSIS.json').read_bytes()),
                'externalRuntimeDependencies': [], 'publicationStatus': 'PREPARED_LOCAL_NOT_DEPLOYED'}
    (HERE / 'BUILD_MANIFEST.json').write_text(json.dumps(identity, indent=2) + '\n')
    print(json.dumps(identity, indent=2))

if __name__ == '__main__':
    main()
