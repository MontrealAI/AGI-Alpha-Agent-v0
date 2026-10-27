# SPDX-License-Identifier: Apache-2.0
"""Replay a prespecified stress world; never alter the frozen kernel or inputs."""
import argparse
import csv
import gzip
import hashlib
import json
import math
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from economy_v3 import HERE, POLICIES, dumps, initial_primitives, load_inputs, paired, sha, simulate, write_csv
from stress_v3 import FIELDS, design


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--case', default='compound_static_beta_large_pool_recurrence')
    p.add_argument('--output', default='results/paid_work_sensitivity/diagnostic_admitted_unused')
    a = p.parse_args()
    root = HERE.parent
    inputs = root / 'results/paid_work_sensitivity'
    freeze = json.loads((root / 'results/paid_work_final/freeze.json').read_text())
    def verify():
        for file, digest in freeze['closure_sha256'].items():
            assert hashlib.sha256((root / file).read_bytes()).hexdigest() == digest, file
    verify()
    c, register = load_inputs(HERE / 'config_v3.json')
    case = next(x for x in design(c, register) if x[0] == a.case)
    name, scenario, cc, rr, compound = case
    design_record = json.loads((inputs / 'design_freeze.json').read_text())
    expected = next(x for x in design_record['cases'] if x['name'] == name)
    assert expected['configuration_sha256'] == sha(cc)
    assert expected['workflow_costs_sha256'] == sha(rr)
    source_rows = list(csv.DictReader((inputs / f'{name}_worlds.csv').open()))
    eligible = [r for r in source_rows if r['policy'] == 'optimized_network' and float(r['retention_admissions']) > 0 and float(r['retention_uses']) == 0]
    world = min(int(r['world']) for r in eligible)
    rows = {r['policy']: r for r in source_rows if int(r['world']) == world}
    started = datetime.now(timezone.utc).isoformat()
    common = initial_primitives(cc, cc['scenarios'][scenario], design_record['seed'], world)
    runs = [simulate(cc, rr, scenario, world, policy, design_record['seed'], common) for policy in POLICIES]
    comparison = paired(*runs)
    checks = 0
    def equal(actual, expected_text):
        if isinstance(actual, bool):
            assert expected_text == str(actual), (actual, expected_text)
        elif actual is None:
            assert expected_text == ''
        else:
            assert math.isclose(float(actual), float(expected_text), rel_tol=1e-12, abs_tol=1e-7), (actual, expected_text)
    for run in runs:
        for key in FIELDS:
            equal(run.metrics[key], rows[run.policy][key]); checks += 1
        if run.policy == 'optimized_network':
            for key, value in comparison.items():
                equal(value, rows[run.policy][key]); checks += 1
    output = root / a.output
    output.mkdir(parents=True, exist_ok=True)
    (output / 'frozen_config.json').write_text(dumps(cc, indent=2))
    (output / 'frozen_workflow_costs.json').write_text(dumps(rr, indent=2))
    write_csv(output / f'{scenario}_worlds.csv', [rows[policy] for policy in POLICIES])
    with gzip.open(output / f'{scenario}_complete_records.jsonl.gz', 'wt', compresslevel=9) as stream:
        for run in runs:
            record = asdict(run)
            stream.write(dumps(record) + '\n')
            (output / f'{run.policy}.json').write_text(dumps(record, indent=2))
    verify()
    manifest = {'status': 'SELECTED ADMITTED-BUT-UNUSED DIAGNOSTIC REPLAY; NOT A NEW TRIAL OR PRODUCTIVE FEEDBACK', 'selection_rule': 'Lowest world ID in the completed prespecified stress with a retention admission and zero recipient use.', 'case': name, 'scenario': scenario, 'compound': compound, 'world': world, 'seed': design_record['seed'], 'source_worlds_per_case': design_record['worlds_per_case'], 'source_csv': str(inputs / f'{name}_worlds.csv'), 'configuration_sha256': sha(cc), 'workflow_costs_sha256': sha(rr), 'frozen_kernel_sha256': hashlib.sha256((HERE / 'economy_v3.py').read_bytes()).hexdigest(), 'scalar_matches': checks, 'all_four_policies_matched': True, 'started_at_utc': started, 'completed_at_utc': datetime.now(timezone.utc).isoformat(), 'paired': comparison}
    (output / 'diagnostic_manifest.json').write_text(dumps(manifest, indent=2))
    print(dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
