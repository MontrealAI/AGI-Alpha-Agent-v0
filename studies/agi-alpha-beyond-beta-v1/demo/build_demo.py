# SPDX-License-Identifier: Apache-2.0
"""Build a self-contained bilingual companion; reject invented or stale final data."""
import argparse
import hashlib
import gzip
import json
import pathlib
from diagnostic_view import load_diagnostic

ROOT = pathlib.Path(__file__).resolve().parents[1]


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--view', default=str(ROOT / 'results/paid_work_demo_view.json'))
    parser.add_argument('--output', default=str(ROOT / 'demo/index.html'))
    parser.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args()
    view_path = pathlib.Path(args.view)
    view = json.loads(view_path.read_text()) if view_path.exists() else None
    lifecycle_path = ROOT / 'results/graph_lifecycle_v3_cases.json'
    lifecycle = json.loads(lifecycle_path.read_text()) if lifecycle_path.exists() else None
    if not args.allow_incomplete:
        if not view:
            raise SystemExit('Missing normalized frozen economic results. --allow-incomplete is for internal QA only.')
        if 'confirm' not in view['status'].lower() or 'paid' not in view.get('study_id', '').lower():
            raise SystemExit('Development or prior-study data cannot be delivered as the final paid-work demo.')
        if view.get('commercial_cash_audit', {}).get('status') != 'PASS':
            raise SystemExit('Final companion requires audited complete population cash and scope-matched price data.')
        if not view.get('sensitivity', {}).get('complete'):
            raise SystemExit('Final companion requires every frozen sensitivity case and its completed run manifest.')
        if not lifecycle or not lifecycle.get('audit', {}).get('passed') or not all(case['passed'] for case in lifecycle['cases']):
            raise SystemExit('Final companion requires the executed and passing lifecycle traces.')
        actual_source = hashlib.sha256((ROOT / 'sim/graph_lifecycle_v3.py').read_bytes()).hexdigest()
        actual_test = hashlib.sha256((ROOT / 'sim/test_graph_lifecycle_v3.py').read_bytes()).hexdigest()
        if actual_test != lifecycle['audit']['test_sha256']:
            raise SystemExit('Lifecycle tests changed since the embedded executed traces.')
        if actual_source != lifecycle['source_sha256']:
            raise SystemExit('Lifecycle implementation changed since the embedded executed test traces.')
    workflow_file = ROOT / view['workflow_source'] if view else ROOT / 'evidence/workflow_costs_v3.json'
    workflow = json.loads(workflow_file.read_text())
    if view and not args.allow_incomplete and canonical_hash(workflow) != view['workflow_costs_sha256']:
        raise ValueError('Demo workflow register differs from the frozen results.')
    models = json.loads((ROOT / 'evidence/model_register.json').read_text())
    mechanism = json.loads((ROOT / 'results/mechanism.json').read_text())
    sources = [{'id': source['id'], 'title': source['title'], 'url': source['url'], 'date': source['retrieved']}
               for source in models['sources'] if source['id'] in ('OAI-01', 'OAI-02', 'OAI-03', 'OAI-04')]
    foundation = json.loads((ROOT / 'evidence/foundation_source_register.json').read_text())
    sources.extend({'id': source['id'], 'title': source['title'], 'url': source['url'],
                    'date': source.get('retrieved', source.get('retrieval_date', '2026-10-26'))}
                   for source in foundation['sources'] if source['id'] in ('TI-2026', 'GSA-4S-2026', 'ALPHAEVOLVE-2025'))
    graph_source_file = ROOT / 'evidence/graph_foundation_source_register.json'
    if graph_source_file.exists():
        graph_sources = json.loads(graph_source_file.read_text())
        sources.extend({'id': source['id'], 'title': source['title'], 'url': source['url'],
                        'date': source.get('retrieved', '2026-10-26')}
                       for source in graph_sources.get('sources', []) if source.get('url'))
    paid_source_file = ROOT / 'evidence/paid_job_foundation_source_register.json'
    if paid_source_file.exists():
        paid_sources = json.loads(paid_source_file.read_text())
        sources.extend({'id': source['id'], 'title': source['title'], 'url': source['url'],
                        'date': source.get('retrieved', '2026-10-26')}
                       for source in paid_sources.get('sources', []) if source.get('url'))
    trace_path = ROOT / 'results/paid_work_trace.json'
    receipt_trace = json.loads(trace_path.read_text()) if trace_path.exists() else None
    if not args.allow_incomplete and not receipt_trace:
        raise SystemExit('Final companion requires the receipt-linked illustration export or an explicit no-path record.')
    if receipt_trace and view and receipt_trace.get('primary_confirmation_config_sha256') != view['config_sha256']:
        raise SystemExit('Receipt illustration belongs to a different primary confirmation.')
    diagnostic = load_diagnostic(ROOT, view['config_sha256']) if view else None
    exploratory_path = ROOT / 'results/paid_work_exploratory_trace.json'
    exploratory_trace = json.loads(exploratory_path.read_text()) if exploratory_path.exists() else None
    if not args.allow_incomplete and (not diagnostic or not exploratory_trace):
        raise SystemExit('Final companion requires the single closed exploratory diagnostic and its selected nonpayback trace.')
    if exploratory_trace and view and exploratory_trace['primary_confirmation_config_sha256'] != view['config_sha256']:
        raise SystemExit('Exploratory illustration belongs to a different primary study.')
    data = {'study': 'AGI ALPHA FLYWHEEL: Profitable Work First. Compounding Capability When Worthwhile.', 'evidence_date': '2026-10-26', 'publication_status': 'INTERNAL PREVIEW — COMPLETE SENSITIVITY PENDING' if args.allow_incomplete else 'COMPLETE FROZEN RESEARCH COMPANION',
            'workflow': workflow, 'models': models, 'mechanism': mechanism,
            'lifecycle': lifecycle, 'view': view, 'sources': sources, 'receipt_trace': receipt_trace, 'controller_diagnostic': diagnostic, 'exploratory_trace': exploratory_trace}
    embedded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', r'<\/')
    output = pathlib.Path(args.output)
    output.write_text((ROOT / 'demo/template.html').read_text().replace('__EMBEDDED_DATA__', embedded))
    compressed_path = output.with_name(output.name + '.gz')
    if not args.allow_incomplete:
        compressed_path.write_bytes(gzip.compress(output.read_bytes(), compresslevel=9, mtime=0))
    status = 'internal preview with incompleteness explicitly permitted' if args.allow_incomplete else ('frozen confirmation companion' if 'confirm' in view['status'].lower() else 'internal economic preview') if view else 'internal mechanism/lifecycle preview'
    print(json.dumps({'output': str(output), 'bytes': output.stat().st_size,
                      'economic_scenarios': len(view.get('scenarios', [])) if view else 0,
                      'lifecycle_cases': len(lifecycle.get('cases', [])) if lifecycle else 0,
                      'status': status, 'gzip_bytes': compressed_path.stat().st_size if not args.allow_incomplete else None, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
