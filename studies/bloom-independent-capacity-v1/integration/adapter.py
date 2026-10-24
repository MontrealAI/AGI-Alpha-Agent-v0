# SPDX-License-Identifier: Apache-2.0
"""Translate a source-bound study into genuine Alpha record schemas.

The records are a local structural translation. They are not authenticated
native proof, a production admission, or a replacement for the original frozen
scientific protocol. The native JobDispatcher fixture is separate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .native_workflow import runtime_environment, to_wire
from .source_loader import native_modules, verify_vendor


def _load(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32_000_000:
        raise ValueError('Expected a bounded regular JSON input')
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('Duplicate JSON key: ' + key)
            value[key] = item
        return value
    def constant(value):
        raise ValueError('Non-finite JSON value: ' + value)
    return json.loads(path.read_text(), object_pairs_hook=pairs, parse_constant=constant)


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _files(root, names):
    if not isinstance(names, list) or len(names) > 200:
        raise ValueError('An explicit list of at most 200 files is required')
    result = []
    for name in names:
        relative = Path(name)
        unresolved = root / relative
        if unresolved.is_symlink():
            raise ValueError('Evidence paths cannot be symbolic links')
        path = unresolved.resolve()
        if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(root):
            raise ValueError('Evidence paths must stay inside the experiment directory')
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 128_000_000:
            raise ValueError('Evidence must be bounded regular files: ' + str(name))
        data = path.read_bytes()
        result.append({'path': relative.as_posix(), 'bytes': len(data), 'sha256': _hash(data)})
    if len({row['path'] for row in result}) != len(result):
        raise ValueError('Duplicate evidence paths')
    return result


def _write(path, value, canonical):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical(value) + b'\n'
    with path.open('xb') as stream:
        stream.write(data)
    return {'path': str(path), 'bytes': len(data), 'sha256': _hash(data)}


def export_records(experiment_dir, summary_path, output_dir, *, metadata_path=None):
    root = Path(experiment_dir).resolve()
    summary = Path(summary_path).resolve()
    if not summary.is_relative_to(root):
        raise ValueError('The summary must belong to the experiment directory')
    metadata = _load(metadata_path or root / 'integration_metadata.json')
    summary_data = _load(summary)
    if not isinstance(summary_data, dict):
        raise ValueError('The summary must be an object')
    modules = native_modules()
    p = modules['successor.protocol']
    required = ('mission_id', 'objective', 'protocol_path', 'source_paths', 'comparators', 'thresholds')
    if any(key not in metadata for key in required):
        raise ValueError('Metadata requires ' + ', '.join(required))
    if not metadata['thresholds'] or len(metadata['comparators']) < 2:
        raise ValueError('Supply the actual thresholds and at least two declared comparators')
    now = datetime.now(UTC)
    packaged_at = now.isoformat(timespec='seconds').replace('+00:00', 'Z')
    until = (now + timedelta(days=1)).isoformat(timespec='seconds').replace('+00:00', 'Z')
    mission_id = metadata['mission_id']
    institution_id = metadata.get('institution_id', 'bloom-local-study')
    sources = _files(root, metadata['source_paths'])
    protocol_files = _files(root, [metadata['protocol_path']])
    manifests = {
        'source': sources,
        'graph': _files(root, metadata.get('graph_paths', metadata['source_paths'])),
        'policy': _files(root, metadata.get('policy_paths', [metadata['protocol_path']])),
        'environment': _files(root, metadata.get('environment_paths', [])),
        'artifact': _files(root, list(dict.fromkeys([str(summary.relative_to(root))] + metadata.get('artifact_paths', [])))),
    }
    environment = runtime_environment()
    env_digest = p.digest('bloom-structural-environment', {'runtime': environment, 'files': manifests['environment']})
    budget_data = metadata.get('budget', {'limits': {}, 'units': {}, 'enforceable': [],
                                        'unknown_costs': ['human-fees', 'platform-billing', 'maintenance']})
    budget = p.ResourceBudget.model_validate(budget_data)
    thresholds = [p.OutcomeMeasure.model_validate(item) for item in metadata['thresholds']]
    mission = p.MissionConstitution(
        mission_id=mission_id, owner=metadata.get('owner', 'MontrealAI'), objective=metadata['objective'],
        mission_distribution=metadata.get('mission_distribution', 'See the exact bound scientific protocol.'),
        scope='Local public research; structural record export conveys no operational authority.',
        outcome_measures=thresholds, evidence_rights=['Public research source and customer-owned export.'],
        constraints=['Native schema validation does not establish scientific validity or independent trust.'],
        prohibited_actions=['financial-transaction', 'external-dispatch', 'credentials', 'security-settings'],
        budget=budget, authority_ceiling='none',
        stop_conditions=metadata.get('stop_conditions', ['Follow the bound scientific protocol and stop on exhausted resources.']),
    )
    world = p.WorldProgram(
        world_id=mission_id + '-world', artifact_digest=p.digest('bloom-world-files', manifests['graph']),
        inputs=[p.TypedPort(name='graph', type_name='Source-bound dependency graph and query workload')],
        outputs=[p.TypedPort(name='impact', type_name='Exact graph impact result; scientific qualification is external to this schema')],
        transitions=metadata.get('world_transitions', ['Use only the transformations declared in the bound scientific protocol.']),
        uncertainty=metadata.get('world_uncertainty', 'Synthetic benchmark and identified public fixtures; external validity remains limited.'),
        assumptions=metadata.get('assumptions', ['Graph and measurement semantics are those in the bound protocol.']),
        falsifiers=metadata.get('falsifiers', ['Disagreement with the independently implemented reference or invalid predecessor binding.']),
    )
    policy = p.PolicyProgram(
        policy_id=mission_id + '-policy', artifact_digest=p.digest('bloom-policy-files', manifests['policy']),
        objective=metadata['objective'], decision_rules=metadata.get('decision_rules', ['Apply the frozen scientific policy without held-out retuning.']),
        admissible_actions=['reuse', 'compose', 'repair', 'construct', 'conventional', 'stop'],
        constraints=['No external transactions, native financial activation, or inherited authority.'],
        abstention=['Stop or retain the qualifying conventional alternative when incremental construction is unjustified.'],
        dependencies=[protocol_files[0]['sha256']],
    )
    release = p.CandidateReleaseManifest(
        release_id=mission_id + '-release', institution_id=institution_id, mission_id=mission_id,
        producer='bloom-local-research', environment_digest=env_digest,
        artifacts=[p.BehaviorArtifact(name=f'source-{i:03}', role='source', digest=row['sha256'], location=row['path'])
                   for i, row in enumerate(sources)], world_digest=p.digest('world-program', world),
        policy_digest=p.digest('policy-program', policy), budget=budget,
        configuration={'translation_scope': 'structural-local-only'},
    )
    cost_rule = p.digest('bloom-cost-rule', {'protocol_file': protocol_files[0], 'budget': budget.model_dump(mode='json')})
    comparators, comparator_releases = [], {}
    for comparator in metadata['comparators']:
        ident = comparator['id']
        rows = _files(root, comparator.get('source_paths', metadata['source_paths']))
        status = comparator.get('status', 'unavailable')
        alternative = p.CandidateReleaseManifest(
            release_id=ident, institution_id=institution_id, mission_id=mission_id,
            producer='bloom-local-research', environment_digest=env_digest,
            artifacts=[p.BehaviorArtifact(name=f'source-{i:03}', role='source', digest=row['sha256'], location=row['path'])
                       for i, row in enumerate(rows)], configuration=to_wire(comparator.get('configuration', {})),
        )
        comparator_releases[ident] = alternative.model_dump(mode='json')
        comparators.append(p.Comparator(
            comparator_id=ident, role=comparator.get('role', 'specialist'),
            release_digest=p.digest('release', alternative) if status == 'measured' else None,
            observed_at=packaged_at, resources=budget, status=status,
            selection_rationale=comparator.get('selection_rationale', 'Declared in the bound scientific protocol.'),
            unavailability_reason=comparator.get('unavailability_reason', 'Measurement is not asserted by this adapter.') if status == 'unavailable' else None,
        ))
    comparator_manifest = p.ComparatorManifest(
        manifest_id=mission_id + '-comparators', mission_id=mission_id, comparators=comparators,
        cost_rule_digest=cost_rule, selection_rule=metadata.get('selection_rule', 'Use the frozen scientific comparator plan.'),
        frozen_at=packaged_at,
    )
    disclosure = p.VerifierDisclosure(
        verifier='bloom-local-research', organization='MONTREAL.AI local experimental workflow',
        control_separation='Source-scoped local checks and same-session role separation only; no organizational independence claim.',
        custodian='bloom-local-research', funding_and_conflicts='User-authorized local research; author and system developer interests disclosed.',
        protocol_controller='bloom-local-research', replication_status='not-replicated', provenance='local',
    )
    protocol = p.ProofProtocol(
        protocol_id=mission_id + '-structural-protocol', mission_id=mission_id,
        candidate_release_digest=p.digest('release', release),
        comparator_manifest_digest=p.digest('comparator-manifest', comparator_manifest),
        environment_digest=env_digest,
        evidence_commitment=p.digest('bloom-evidence-inventory', manifests['artifact']),
        verifier_disclosure=disclosure, evaluation_unit=metadata.get('evaluation_unit', 'See the bound scientific protocol.'),
        thresholds=thresholds, randomization=metadata.get('randomization', 'See the original bound scientific protocol.'),
        warmup_and_cache=metadata.get('warmup_and_cache', 'See the original bound scientific protocol.'),
        timeout_ms=metadata.get('timeout_ms', 0), exclusions_policy=metadata.get('exclusions_policy', 'Retain every attempted case and failure.'),
        uncertainty_method=metadata.get('uncertainty_method', 'No interval method inferred by the adapter; consult the bound analysis.'),
        multiplicity_policy=metadata.get('multiplicity_policy', 'No multiplicity claim inferred by the adapter; consult the bound analysis.'),
        cost_rule_digest=cost_rule, validity=p.Validity(valid_from=packaged_at, valid_until=until), frozen_at=packaged_at,
    )
    verdict = metadata.get('receipt', {})
    receipt = p.ProofReceipt(
        proof_id=mission_id + '-local-record', institution_id=institution_id, mission_id=mission_id,
        release_digest=p.digest('release', release), environment_digest=env_digest,
        verifier='bloom-local-research', valid_until=until, issued_at=packaged_at,
        outcome=verdict.get('outcome', 'insufficient_evidence'), claim='correctness', evidence_scope='local',
        comparator_manifest_digest=p.digest('comparator-manifest', comparator_manifest),
        protocol_digest=p.digest('proof-protocol', protocol), evidence_commitment=protocol.evidence_commitment,
        disclosure=disclosure, evaluation_units=verdict.get('evaluation_units', 0),
        measurements=verdict.get('measurements', {}), uncertainty=verdict.get('uncertainty', 'Use the traceable raw study results; this adapter does not verify the analysis.'),
        costs=budget, failures=verdict.get('failures', []), interventions=verdict.get('interventions', []),
        exclusions=verdict.get('exclusions', []),
    )
    records = {'MissionConstitution': mission, 'WorldProgram': world, 'PolicyProgram': policy,
               'CandidateReleaseManifest': release, 'ComparatorManifest': comparator_manifest,
               'ProofProtocol': protocol, 'ProofReceipt': receipt}
    payload = {
        'schema': 'bloom-alpha-structural-records/v1', 'packaged_at': packaged_at,
        'native_source': verify_vendor(), 'runtime_environment': environment, 'file_manifests': manifests,
        'records': {key: record.model_dump(mode='json') for key, record in records.items()},
        'comparator_releases': comparator_releases,
        'original_scientific_protocol': protocol_files[0],
        'original_protocol_frozen_at_claim': metadata.get('frozen_at', 'Not asserted by the schema adapter.'),
        'schema_translation_time_is_not_preregistration': True,
        'interpretation': 'Actual Alpha schemas validated locally. This unsigned translation is not an authenticated native receipt, independent trust, admission, or operational grant.',
        'external_artifacts': 'The complete publication ZIP must include every path in file_manifests; this JSON alone is not the complete evidence package.',
        'active_proofs': [], 'active_grants': [], 'stopped': True,
    }
    capsule = {'payload': payload, 'digest': p.digest('bloom-alpha-structural-capsule', payload)}
    output = Path(output_dir)
    result = _write(output / 'native_records.json', capsule, p.canonical)
    return {**result, 'native_record_types': list(records), 'authority': 'none', 'authenticated': False}


def restore_records(capsule_path, experiment_dir, output_path):
    root = Path(experiment_dir).resolve()
    p = native_modules()['successor.protocol']
    capsule = _load(capsule_path)
    if set(capsule) != {'payload', 'digest'} or p.digest('bloom-alpha-structural-capsule', capsule['payload']) != capsule['digest']:
        raise ValueError('Structural export integrity mismatch')
    payload = capsule['payload']
    if payload.get('schema') != 'bloom-alpha-structural-records/v1' or payload['active_proofs'] or payload['active_grants']:
        raise ValueError('A structural import cannot carry active proof or authority')
    for name, record in payload['records'].items():
        if name not in {'MissionConstitution', 'WorldProgram', 'PolicyProgram', 'CandidateReleaseManifest',
                        'ComparatorManifest', 'ProofProtocol', 'ProofReceipt'}:
            raise ValueError('Unsupported native record type')
        getattr(p, name).model_validate(record)
    conditions = {}
    for category, rows in payload['file_manifests'].items():
        try:
            conditions[category] = _files(root, [row['path'] for row in rows]) == rows
        except (ValueError, OSError):
            conditions[category] = False
    conditions['runtime_environment'] = runtime_environment() == payload['runtime_environment']
    record = {
        'schema': 'bloom-alpha-structural-restore/v1', 'source_capsule_digest': capsule['digest'],
        'historical_records': payload['records'], 'stopped': True, 'active_proofs': [], 'active_grants': [],
        'revalidated_conditions': conditions, 'all_recorded_inputs_match': all(conditions.values()),
        'authority_revalidation_required': True, 'continuation_authorized': False,
        'scope': 'Inactive structural history only. Native journal fixture backup/restoration is exercised separately.',
    }
    _write(Path(output_path), record, p.canonical)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export')
    export.add_argument('experiment_dir'); export.add_argument('summary'); export.add_argument('output_dir')
    export.add_argument('--metadata', required=True)
    restore = commands.add_parser('restore')
    restore.add_argument('capsule'); restore.add_argument('experiment_dir'); restore.add_argument('output')
    args = parser.parse_args()
    if args.command == 'export':
        result = export_records(args.experiment_dir, args.summary, args.output_dir, metadata_path=args.metadata)
    else:
        result = restore_records(args.capsule, args.experiment_dir, args.output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
