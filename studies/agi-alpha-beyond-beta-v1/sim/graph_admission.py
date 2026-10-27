# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import hashlib, json, re
from typing import Any

SCHEMA = 'ase-simulated-skill-admission/v1'
DEFAULT_MODELS = {'gpt-6-astra': 'rolling-alias-observed-2026-10-26', 'gpt-6.1-terra': 'rolling-alias-observed-2026-10-26'}
ELIGIBLE = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.agent\.agi\.eth\Z')
HASH = re.compile(r'[a-f0-9]{64}\Z')

def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def bound_hash(record: dict[str, Any]) -> str:
    return digest({k: v for k, v in record.items() if k != 'attestation'})

def make_simulated_record(skill_id: str, world: int, created: int, lifetime: int, domains: list[int],
                          evaluation_passed: bool, dependencies: list[dict[str, Any]] | None = None,
                          models: dict[str, str] | None = None) -> dict[str, Any]:
    record = {'schema': SCHEMA, 'skill_id': skill_id, 'version': '1', 'scope_domains': sorted(set(domains)),
              'models': dict(models or DEFAULT_MODELS), 'evidence_sha256': digest({'basis': 'SIMULATED_EVALUATION',
              'world': world, 'skill_id': skill_id, 'created': created, 'passed': evaluation_passed}),
              'created_month': created, 'valid_until_month': created + lifetime,
              'revoked': False, 'dependencies': dependencies or [], 'evaluation_passed': evaluation_passed,
              'provenance': 'SIMULATED', 'execution_authority': [], 'settlement_authority': 'NONE'}
    record['attestation'] = {'issuer': f'validator-{world % 12}.agent.agi.eth', 'authenticated_simulated': True,
                             'bound_record_sha256': bound_hash(record)}
    return record

def inspect(record: dict[str, Any], now: int, catalog: dict[str, dict[str, Any]],
            domain: int | None = None, models: dict[str, str] | None = None,
            ancestors: frozenset[str] = frozenset()) -> dict[str, Any]:
    reasons: list[str] = []
    if not isinstance(record, dict):
        return {'admitted': False, 'reasons': ['missing_record'], 'basis': 'SIMULATED', 'execution_authority': []}
    key = record.get('skill_id')
    if not isinstance(key, str) or not key: reasons.append('missing_skill_identity')
    if key in ancestors: reasons.append('dependency_cycle')
    if record.get('schema') != SCHEMA or record.get('provenance') != 'SIMULATED': reasons.append('schema_or_basis')
    if record.get('execution_authority') != [] or record.get('settlement_authority') != 'NONE': reasons.append('authority_expansion')
    if record.get('revoked') is not False: reasons.append('revoked')
    start, end = record.get('created_month'), record.get('valid_until_month')
    if type(start) is not int or type(end) is not int or not start <= now < end: reasons.append('stale_or_future')
    if not record.get('version'): reasons.append('missing_version')
    if record.get('models') != (models or DEFAULT_MODELS): reasons.append('model_version_mismatch')
    scope = record.get('scope_domains')
    if not isinstance(scope, list) or not scope or any(type(v) is not int or v < 0 for v in scope): reasons.append('invalid_scope')
    elif domain is not None and domain not in scope: reasons.append('scope_mismatch')
    if not isinstance(record.get('evidence_sha256'), str) or not HASH.fullmatch(record['evidence_sha256']): reasons.append('missing_evidence')
    if record.get('evaluation_passed') is not True: reasons.append('evaluation_not_passed')
    att = record.get('attestation', {})
    if not isinstance(att, dict): att = {}
    if not isinstance(att.get('issuer'), str) or not ELIGIBLE.fullmatch(att['issuer']): reasons.append('ineligible_attester')
    if att.get('authenticated_simulated') is not True: reasons.append('missing_simulated_authentication')
    try:
        if att.get('bound_record_sha256') != bound_hash(record): reasons.append('evidence_binding_mismatch')
    except (TypeError, ValueError): reasons.append('invalid_record_data')
    deps = record.get('dependencies')
    if not isinstance(deps, list): reasons.append('invalid_dependencies'); deps = []
    if 'dependency_cycle' not in reasons:
        for dep in deps:
            if not isinstance(dep, dict) or not isinstance(dep.get('skill_id'), str):
                reasons.append('invalid_dependency'); continue
            parent = catalog.get(dep['skill_id'])
            if parent is None: reasons.append('missing_dependency'); continue
            if parent.get('version') != dep.get('version') or parent.get('evidence_sha256') != dep.get('evidence_sha256'):
                reasons.append('dependency_binding_mismatch'); continue
            required = dep.get('required_domains', scope if isinstance(scope, list) else [])
            if not isinstance(required, list) or any(type(x) is not int for x in required):
                reasons.append('invalid_dependency_scope'); continue
            check_domains = required if domain is None else ([domain] if domain in required else [])
            for parent_domain in check_domains:
                review = inspect(parent, now, catalog, parent_domain, models, ancestors | {str(key)})
                if not review['admitted']: reasons.append('dependency_unusable'); break
    return {'admitted': not reasons, 'reasons': sorted(set(reasons)), 'basis': 'SIMULATED',
            'eligibility_assumption': 'The receipt is a simulation fixture, not a signature or ENS resolution.',
            'execution_authority': [], 'settlement_authority': 'NONE',
            'quality_claim': 'Admission checks binding and declared scope; no correctness or economic bonus.'}
