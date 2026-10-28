from pathlib import Path
import argparse, base64, datetime, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'catalog': 'evidence/catalog/catalog.json',
    'production': 'evidence/production-summary.json',
    'reuse': 'evidence/reuse-controls.json',
    'market': 'evidence/market-primary/summary.json',
    'worlds': 'evidence/market-primary/compact-worlds.jsonl',
    'marketExecution': 'evidence/market-primary/execution.json',
    'effects': 'evidence/market-primary/effect-calibration.json',
    'marketDesign': 'protocol/market-design.json',
    'costs': 'market/cost-assumptions.json',
    'researchDesign': 'protocol/research-design.json',
    'missionDesign': 'protocol/mission-design.json',
    'productionFreeze': 'protocol/production-freeze.json',
    'marketFreeze': 'protocol/market-freeze.json',
    'acceptance': 'protocol/acceptance-contract.json',
    'assets': 'market/asset-bindings.json',
    'admission': 'evidence/asset-admission.json',
    'resources': 'costs/research-resource-ledger.json',
    'positiveInspection': 'review/positive-world-inspection.json',
    'positiveTrace': 'review/positive-world-trace.json',
}

def build(final=False):
    downloads, index, missing, missions = {}, [], [], {}
    for key, path in SOURCES.items():
        source = ROOT / path
        if not source.is_file():
            missing.append({'key': key, 'path': path})
            continue
        raw = source.read_bytes()
        row = {'key': key, 'path': path, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
               'filename': source.name, 'type': 'application/x-ndjson' if source.suffix == '.jsonl' else 'application/json'}
        index.append(row)
        downloads[key] = dict(row, data=base64.b64encode(raw).decode())
    if 'production' in downloads:
        production = json.loads(base64.b64decode(downloads['production']['data']))
        for mission in production.get('arms', {}).get('C', {}).get('per_mission', []):
            mission_files = {}
            for kind, field, mime in [('packet', 'packet_zip_path', 'application/zip'),
                                      ('selection', 'selection_path', 'application/json')]:
                path = mission.get(field)
                if not path:
                    continue
                source = (ROOT / path).resolve()
                if not source.is_relative_to(ROOT.resolve()):
                    raise SystemExit('Mission evidence path escapes study: ' + path)
                key = 'mission:' + mission['id'] + ':' + kind
                if not source.is_file():
                    missing.append({'key': key, 'path': path})
                    if final:
                        raise SystemExit('Final demo lacks actual mission evidence: ' + path)
                    continue
                raw = source.read_bytes()
                row = {'key': key, 'path': path, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                       'filename': mission['id'] + '-' + source.name, 'type': mime}
                index.append(row)
                downloads[key] = dict(row, data=base64.b64encode(raw).decode())
                mission_files[kind] = key
            missions[mission['id']] = mission_files
    for key, pattern, mime in [('paper', '*.pdf', 'application/pdf'), ('latex', '*.tex', 'application/x-tex')]:
        candidates = sorted((ROOT / 'paper').glob(pattern))
        if key == 'paper':
            stable_pdf = ROOT / 'paper/AGI_ALPHA_Economy_of_Verified_Capability.pdf'
            candidates = [stable_pdf] if stable_pdf.is_file() else []
        if candidates:
            source = candidates[0]
            raw = source.read_bytes()
            if key == 'paper' and final and not (raw.startswith(b'%PDF-') and raw.rstrip().endswith(b'%%EOF')):
                raise SystemExit('Final companion requires a complete PDF')
            row = {'key': key, 'path': str(source.relative_to(ROOT)), 'bytes': len(raw),
                   'sha256': hashlib.sha256(raw).hexdigest(), 'filename': source.name, 'type': mime}
            index.append(row)
            downloads[key] = dict(row, data=base64.b64encode(raw).decode())
    required = ['catalog', 'production', 'reuse', 'market', 'worlds', 'marketExecution', 'effects', 'marketDesign', 'costs',
                'productionFreeze', 'marketFreeze', 'acceptance', 'assets', 'admission', 'resources', 'paper', 'latex']
    absent = [key for key in required if key not in downloads]
    if final and absent:
        raise SystemExit('Final demo requires actual artifacts: ' + ', '.join(absent))
    if final:
        outcome = json.loads(base64.b64decode(downloads['market']['data']))
        if not outcome.get('complete'):
            raise SystemExit('Final demo cannot label an incomplete market campaign complete')
    payload_index = {'schema': 'agi-alpha-verified-capability-demo-evidence-index/v1',
                     'builtUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     'edition': 'FINAL_LOCAL_RESEARCH' if final else 'SCAFFOLD_AWAITING_FINAL_DATA',
                     'sourceFiles': index, 'missingAtBuild': missing,
                     'identity': 'FIXTURE_ONLY; live ENS NOT RUN; no cryptographic signer proof',
                     'publicServing': 'NOT CLAIMED', 'actualCustomerCollectionsUSD': 0,
                     'scope': 'Exact locally supplied evidence files; web publication and live deployment are separate.'}
    raw_index = (json.dumps(payload_index, ensure_ascii=False, indent=2) + '\n').encode()
    (ROOT / 'demo/data-index.json').write_bytes(raw_index)
    downloads['index'] = {'key': 'index', 'path': 'demo/data-index.json', 'filename': 'data-index.json',
                          'bytes': len(raw_index), 'sha256': hashlib.sha256(raw_index).hexdigest(),
                          'type': 'application/json', 'data': base64.b64encode(raw_index).decode()}
    payload = {'edition': payload_index['edition'], 'builtUTC': payload_index['builtUTC'], 'downloads': downloads,
               'missions': missions,
               'references': [
                   {'title': 'Merkle Roots for the Validated Skill Graph', 'url': 'https://github.com/MontrealAI/goalos-agialpha-sovereign-machine-economy/blob/main/docs/paper/Merkle_Roots_for_the_Validated_Skill_Graph_v114.pdf', 'status': 'PUBLIC ARCHITECTURAL SOURCE'},
                   {'title': 'PROOF LOOPS', 'url': 'https://github.com/MontrealAI/goalos-agialpha-sovereign-machine-economy/blob/main/docs/paper/PROOF_LOOPS_research_paper_v2_author_edition.pdf', 'status': 'PUBLIC ARCHITECTURAL SOURCE'},
                   {'title': 'Research coordination · issue 4850', 'url': 'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850', 'status': 'PUBLIC COORDINATION RECORD'},
                   {'title': 'Preserved second-investment result · PR 4940', 'url': 'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4940', 'status': 'PRIOR PUBLIC DRAFT; NO RELEASE CLAIM'},
               ]}
    data = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    template = (ROOT / 'demo/template.html').read_text()
    if template.count('__EMBEDDED_EVIDENCE__') != 1:
        raise SystemExit('Exactly one embedded-data insertion required')
    html = template.replace('__EMBEDDED_EVIDENCE__', data)
    output = ROOT / 'demo/index.html'
    output.write_text(html)
    receipt = {'schema': 'agi-alpha-verified-capability-demo-build/v1', 'edition': payload_index['edition'],
               'sourceCount': len(index), 'missing': absent, 'htmlBytes': output.stat().st_size,
               'htmlSHA256': hashlib.sha256(output.read_bytes()).hexdigest(),
               'templateSHA256': hashlib.sha256((ROOT / 'demo/template.html').read_bytes()).hexdigest(),
               'networkRequests': 0, 'evidenceIndexSHA256': downloads['index']['sha256']}
    (ROOT / 'demo/build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--final', action='store_true')
    build(parser.parse_args().final)
