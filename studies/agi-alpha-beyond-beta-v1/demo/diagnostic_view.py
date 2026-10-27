# SPDX-License-Identifier: Apache-2.0
"""Display-only reader for the single closed exploratory controller diagnostic."""
import csv
import hashlib
import json
from pathlib import Path

ARMS = ('frozen_beta','frozen_network','posterior_coherent_network')


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def load_diagnostic(root: Path, primary_hash: str):
    path=root/'results/paid_work_prior_diagnostic'
    if not (path/'run_manifest.json').exists():
        return None
    read=lambda name:json.loads((path/name).read_text())
    summary,freeze,manifest,design=(read(name) for name in ('summary.json','freeze.json','run_manifest.json','diagnostic_design.json'))
    if not manifest.get('completed_at_utc') or manifest.get('no_further_tuning') is not True:
        raise ValueError('Exploratory diagnostic is not closed.')
    if set(summary['arms'])!=set(ARMS) or summary['worlds']!=100 or summary['seed']!=951557 or manifest['history_count']!=300:
        raise ValueError('Unexpected exploratory diagnostic design; no silent experiment substitution.')
    if design['historical_primary_config_sha256']!=primary_hash or not design['actual_capability_cost_demand_tests_and_beta_unchanged']:
        raise ValueError('Diagnostic no longer preserves the declared primary/capability boundary.')
    for key,file in (('configuration_sha256','frozen_config.json'),('workflow_costs_sha256','frozen_workflow_costs.json')):
        actual=canonical_hash(read(file))
        if summary[key]!=actual or freeze[key]!=actual or manifest[key]!=actual:
            raise ValueError('Diagnostic frozen identity mismatch: '+key)
    for source in ('sim/economy_v3_posterior.py','sim/run_recipient_prior_diagnostic.py','sim/test_recipient_prior_diagnostic.py','sim/PRIOR_DIAGNOSTIC_PROTOCOL.md'):
        if hashlib.sha256((root/source).read_bytes()).hexdigest()!=freeze['closure_sha256'][source]:
            raise ValueError('Diagnostic source changed after its separate freeze: '+source)
    with (path/'worlds.csv').open() as stream:
        rows=list(csv.DictReader(stream))
    if len(rows)!=300 or any(len({r['world'] for r in rows if r['diagnostic_arm']==arm})!=100 for arm in ARMS):
        raise ValueError('Diagnostic scalar histories are not complete and unique by arm.')
    audit=json.loads((root/'qa/posterior_diagnostic_reconciliation.json').read_text())
    if audit['status']!='PASS':
        raise ValueError('Independent diagnostic accounting audit did not pass.')
    return {**summary,'complete':True,'source_run':str(path.relative_to(root)),
            'manifest':manifest,'design':design,'audit_status':audit['status'],
            'summary_sha256':hashlib.sha256((path/'summary.json').read_bytes()).hexdigest()}
