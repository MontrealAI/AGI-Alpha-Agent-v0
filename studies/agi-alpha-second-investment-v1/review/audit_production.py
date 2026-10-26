"""Read archived primary evidence only; never invoke pip or a producer.

This post-confirmation review is not an additional experiment or independent
customer acceptance. Recomputing the frozen verifier checks archival consistency.
"""
import copy
import datetime
import hashlib
import importlib.util
import json
import statistics
import time
import tomllib
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.tags import sys_tags
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import InvalidVersion, Version

ROOT = Path(__file__).resolve().parent.parent
START = time.perf_counter()
failures = []
checks = 0


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def check(ok, label):
    global checks
    checks += 1
    if not ok:
        failures.append(label)
    return bool(ok)


def semantic_certificate(value):
    result = copy.deepcopy(value)
    result['verifier'].pop('wall_seconds', None)
    result['verifier'].pop('cpu_seconds', None)
    return result


freeze_path = ROOT / 'protocol/production-freeze.json'
freeze = read(freeze_path)
for item in freeze['files']:
    path = ROOT / item['path']
    check(path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], 'source:' + item['path'])
source_hashes = {item['path']: item['sha256'] for item in freeze['files']}
for item in read(ROOT / 'protocol/inherited-identities.json')['files']:
    path = ROOT / item['path']
    check(path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], 'inherited:' + item['path'])

selection_path = ROOT / 'protocol/selected-inputs.json'
selection = read(selection_path)
commitment = read(ROOT / 'protocol/input-selection-commitment.json')
manifest_path = ROOT / 'protocol/confirmation-jobs.json'
manifest = read(manifest_path)
campaign_path = ROOT / 'results/confirmation-01/campaign.json'
campaign = read(campaign_path)
check(commitment['selection_sha256'] == digest(selection_path) == manifest['selection_sha256'], 'selection_binding')
check(commitment['source_freeze_sha256'] == digest(freeze_path) == campaign['source_freeze_sha256'], 'freeze_binding')
check(campaign['job_manifest_sha256'] == digest(manifest_path), 'manifest_binding')
ordered_times = [freeze['frozen_at'], selection['selected_at'], commitment['registered_at'], campaign['started_at'], campaign['finished_at']]
check(ordered_times == sorted(ordered_times), 'recorded_temporal_order')
check(campaign['partial'] is False and campaign['questions'] == 6 and len(campaign['rows']) == 18, 'complete_scheduled_cohort')
baseline = read(ROOT / 'inputs/development/job.json')
base_wheels = {canonicalize_name(w['name']): w for w in baseline['wheels']}
tags = {tag: rank for rank, tag in enumerate(sys_tags())}
selection_checks = []
for row in selection['rows']:
    family = row['family']
    raw_index = ROOT / 'inputs/release-index' / (family + '.json')
    check(digest(raw_index) == row['index_sha256'], 'index:' + family)
    index = read(raw_index)
    eligible = []
    for text, releases in index['releases'].items():
        try:
            version = Version(text)
        except InvalidVersion:
            continue
        if version < Version(base_wheels[family]['version']) and not version.is_prerelease and not version.is_devrelease and any(not release.get('yanked', False) for release in releases):
            eligible.append((version, text))
    previous = max(eligible)[1]
    check(row['status'] == 'SELECTED' and row['version'] == previous, 'immediate_predecessor:' + family)
    choices = []
    for release in index['releases'][previous]:
        if release.get('yanked', False) or not release['filename'].endswith('.whl'):
            continue
        name, version, _, wheel_tags = parse_wheel_filename(release['filename'])
        ranks = [tags[tag] for tag in wheel_tags if tag in tags]
        if canonicalize_name(name) == family and version == Version(previous) and ranks:
            choices.append((min(ranks), release['filename'], release))
    expected = min(choices, key=lambda value: (value[0], value[1]))[2]
    check(row['wheel']['filename'] == expected['filename'] and row['wheel']['sha256'] == expected['digests']['sha256'], 'deterministic_wheel:' + family)
    selection_checks.append({'family': family, 'baseline': row['baseline_version'], 'selected': previous, 'index_sha256': digest(raw_index), 'rule_matches': row['version'] == previous})

jobs = {}
root_reviews = []
for entry in manifest['jobs']:
    path = ROOT / entry['job']
    job = read(path)
    jobs[entry['family']] = (entry, path, job)
    check(entry['status'] == 'READY' and digest(path) == entry['job_sha256'], 'job:' + entry['family'])
    check(job['id'] == entry['id'], 'job_id:' + entry['family'])
    wheels = {canonicalize_name(w['name']): w for w in job['wheels']}
    changed = [name for name in wheels if wheels[name] != base_wheels[name]]
    check(len(wheels) == 41 and set(wheels) == set(base_wheels) and changed == [entry['family']], 'only_one_changed_distribution:' + entry['family'])
    check(job['pyproject_sha256'] == baseline['pyproject_sha256'] and job['target_environment'] == baseline['target_environment'] == default_environment() and job['project_extras'] == baseline['project_extras'] == ['chain'], 'common_project_environment_extras:' + entry['family'])
    project_path = (path.parent / job['pyproject_path']).resolve()
    lock_path = (path.parent / job['lock_path']).resolve()
    check(digest(project_path) == job['pyproject_sha256'] and digest(lock_path) == job['lock_sha256'], 'job_input_hashes:' + entry['family'])
    for wheel in job['wheels']:
        wheel_path = (path.parent / job['wheelhouse_path'] / wheel['filename']).resolve()
        check(digest(wheel_path) == wheel['sha256'], 'selected_wheel:' + entry['family'] + ':' + wheel['name'])
    project = tomllib.loads(project_path.read_text())['project']
    roots = list(project.get('dependencies', []))
    for extra in job['project_extras']:
        roots += project['optional-dependencies'][extra]
    contradictions = []
    for text in roots:
        requirement = Requirement(text)
        if requirement.marker and not any(requirement.marker.evaluate({**job['target_environment'], 'extra': extra}) for extra in ['', *job['project_extras']]):
            continue
        name = canonicalize_name(requirement.name)
        if name not in wheels or Version(wheels[name]['version']) not in requirement.specifier:
            contradictions.append({'requirement': str(requirement), 'selected': wheels.get(name, {}).get('version')})
    root_reviews.append({'family': entry['family'], 'root_count': len(roots), 'root_contradictions': contradictions})

spec = importlib.util.spec_from_file_location('frozen_acceptance_verifier_for_archival_check', ROOT / 'production/verify.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
native_manifest = read(ROOT / 'native/SOURCE.json')
native_identity = [[name, digest(ROOT / name)] for name in ['production/retained.py', 'production/workbench.mjs', 'production/verify.py', 'protocol/acceptance-contract.json']]
native_identity.extend(['native/' + item['path'], item['sha256']] for item in native_manifest['files'])
expected_native_source = hashlib.sha256(json.dumps(native_identity, separators=(',', ':')).encode()).hexdigest()
row_reviews = []
for row in campaign['rows']:
    label = row['family'] + '/' + row['arm']
    entry, job_path, job = jobs[row['family']]
    result_path = ROOT / row['result_path']
    certificate_path = ROOT / row['verification_path']
    result = read(result_path)
    certificate = read(certificate_path)
    check(digest(result_path) == row['result_sha256'] == certificate['result_sha256'], 'result_binding:' + label)
    check(digest(certificate_path) == row['verification_sha256'], 'certificate_binding:' + label)
    check(row['job_sha256'] == entry['job_sha256'] == result['job_sha256'] == certificate['job_sha256'], 'registered_job_binding:' + label)
    check(row['mission'] == job['id'] == result['job_id'] == certificate['job_id'], 'registered_job_name:' + label)
    check(certificate['verifier']['source_sha256'] == source_hashes['production/verify.py'], 'verifier_source:' + label)
    check(certificate['status'] == 'COMPLETE' and certificate['errors'] == [] and row['accepted'] is True, 'accepted:' + label)
    check(row['decision'] == certificate['verdict'] == result['decision'], 'decision_agreement:' + label)
    check(result['application_qualified'] is False and certificate['application_qualified'] is False and result['authority'] == [] and certificate['authority'] == [] and result['financial_action'] is False, 'scope:' + label)
    check(row['human_minutes'] is None and row['customer_minutes'] is None and row['new_customer_orders'] == 0, 'no_unmeasured_labor_or_orders:' + label)
    for key, relative in result['files'].items():
        if relative is None:
            continue
        artifact = (result_path.parent / relative).resolve()
        check(artifact.is_relative_to(result_path.parent.resolve()) and artifact.is_file(), 'artifact_containment:' + label + ':' + key)
        evidence_key = 'pip_report_sha256' if key == 'report' else key + '_sha256'
        check(digest(artifact) == certificate['evidence'][evidence_key], 'artifact_hash:' + label + ':' + key)
    recomputed = module.verify(job_path, result_path)
    check(semantic_certificate(recomputed) == semantic_certificate(certificate), 'archival_reverification:' + label)
    check(certificate['evidence']['active_lock_count'] == 41 and len(certificate['evidence']['wheels']) == 41, 'complete_lock:' + label)
    native = None
    if row['arm'] == 'B':
        native_dir = certificate_path.parent
        pack = read(native_dir / 'pack.json')
        inspection = read(native_dir / 'inspection.json')
        evidence = pack['result']['evidence']
        check(evidence['jobSha256'] == entry['job_sha256'] and evidence['verificationSha256'] == row['verification_sha256'] and evidence['sourceHash'] == expected_native_source == pack['frozen']['sourceHash'], 'native_binding:' + label)
        check(pack['result']['decision'] == certificate['verdict'] and pack['result']['summary']['accepted'] is True, 'native_headline:' + label)
        check(pack['evaluation'] == {'scope': 'PUBLIC_LOCAL_EXECUTION', 'independentProof': False, 'admission': 'HOLD', 'authority': [], 'settlement': 'NOT_CONNECTED'}, 'native_authority:' + label)
        check(inspection['authentication'] == 'UNAUTHENTICATED_HISTORICAL_IMPORT' and inspection['activeProof'] == [] and inspection['activeAuthority'] == [], 'native_inspection:' + label)
        check(evidence['runtimeModelCalls'] == 0 and evidence['customerAcceptanceObserved'] is False and evidence['authoring'] == 'assistant-authored thin ordinary-tool adapter', 'native_authoring:' + label)
        embedded = {artifact['name']: json.loads(artifact['content']) for artifact in pack['result']['artifacts']}
        check(embedded['lock-decision.json'] == result, 'native_embedded_result:' + label)
        check(embedded['independent-check-summary.json'] == {'status': certificate['status'], 'verdict': certificate['verdict'], 'sha256': row['verification_sha256']}, 'native_embedded_certificate:' + label)
        native = {'pack_sha256': digest(native_dir / 'pack.json'), 'inspection_sha256': digest(native_dir / 'inspection.json'), 'source_sha256': expected_native_source, 'admission': pack['evaluation']['admission'], 'runtime_model_calls': evidence['runtimeModelCalls']}
    row_reviews.append({'family': row['family'], 'arm': row['arm'], 'accepted': row['accepted'], 'verdict': certificate['verdict'], 'pip_exit_code': result['pip_exit_code'], 'distributions': certificate['evidence']['active_lock_count'], 'metadata_requirement_edges': len(certificate['dependency_edges']), 'active_edges': sum(edge['active'] for edge in certificate['dependency_edges']), 'witnesses': certificate['substantiated_witnesses'], 'complete_service_wall_seconds': row['complete_service_wall_seconds'], 'inclusive_cpu_seconds': row['inclusive_cpu_seconds'], 'native': native})

metrics = {}
for arm in ['A', 'B', 'C']:
    rows = [row for row in row_reviews if row['arm'] == arm]
    wall = [row['complete_service_wall_seconds'] for row in rows]
    cpu = [row['inclusive_cpu_seconds'] for row in rows]
    metrics[arm] = {'n': len(rows), 'accepted': sum(row['accepted'] for row in rows), 'consistent': sum(row['verdict'] == 'CONSISTENT' for row in rows), 'conflict': sum(row['verdict'] == 'CONFLICT' for row in rows), 'wall_mean_seconds': statistics.mean(wall), 'wall_median_seconds': statistics.median(wall), 'wall_min_seconds': min(wall), 'wall_max_seconds': max(wall), 'cpu_mean_seconds': statistics.mean(cpu)}
matched = {}
for comparator in ['A', 'C']:
    differences = []
    for family in jobs:
        by_arm = {row['arm']: row for row in row_reviews if row['family'] == family}
        differences.append(by_arm['B']['complete_service_wall_seconds'] - by_arm[comparator]['complete_service_wall_seconds'])
    matched['B_minus_' + comparator] = {'paired_questions': len(differences), 'seconds': differences, 'mean_seconds': statistics.mean(differences), 'B_slower_count': sum(value > 0 for value in differences)}

report = {'schema': 'agi-alpha-second-investment-production-independent-review/v1', 'reviewed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'reviewer_role': '/root/coordination_audit', 'scope': 'Read-only archival audit of six fresh full-lock questions and eighteen matched production records; no primary rerun.', 'audit_source_sha256': digest(__file__), 'campaign_path': str(campaign_path.relative_to(ROOT)), 'campaign_sha256': digest(campaign_path), 'source_freeze_sha256': digest(freeze_path), 'checks': checks, 'failures': failures, 'status': 'PASS_FOR_REGISTERED_METADATA_SCOPE' if not failures else 'FAIL', 'source_files_checked': len(freeze['files']), 'selection': selection_checks, 'recorded_chronology': ordered_times, 'root_constraint_review': root_reviews, 'metrics': metrics, 'paired_timing': matched, 'outputs': row_reviews, 'independence': {'verifier_written_before_fresh_targets_and_producer_review': True, 'same_session_distinct_agent_role': True, 'external_customer_or_institutional_acceptance': False, 'shared_frozen_verifier_for_all_arms': True, 'archival_reverification_is_separate_oracle': False, 'method': 'Independently authored verifier recomputed from raw wheel metadata, project inputs and recorded pip artifacts; post-run source/hash/selection audit plus direct project-root constraint check. Archival recomputation uses that same frozen verifier and cannot be treated as a second independent implementation.', 'shared_components': ['pip', 'packaging marker/specifier semantics', 'Python standard libraries', 'same native environment and public wheel cache']}, 'claim_limits': ['COMPLETE/CONFLICT is an accepted useful negative; it is not a failed acceptance.', 'The two negative questions are project-root version contradictions. All eighteen pip dry-run commands returned zero; there is no observed resolver failure in this fresh panel.', 'The four metadata-consistent questions are not installation, application behavior, security or release qualifications.', 'Six research-proposed predecessor substitutions are not representative customer orders or actual historical application locks.', 'One invocation per arm and family, shared host/cache and balanced order provide descriptive timing only; no population reliability or human effort estimate.', 'B gives the same six accepted outcomes as both strong alternatives and is slower than each in all six matched questions. No measured incremental production gain is established.', 'Native Workbench performs local research orchestration with HOLD, empty authority, disconnected settlement and zero runtime model calls; authoring is assistant supplied.', 'The Workbench reviewMinutes schema field is not observed labor, operating revenue or a financial action.', 'No customer acceptance, commercial collections or autonomous invention is observed.', 'No whole-application service runtime was installed or restarted by this production experiment.', 'Recorded hashes and timestamps establish internal archive consistency; they do not supply hostile-recorder attestation.'], 'practical_usability': {'machine_readable_packets': 'All eighteen supply exact job and artifact bindings, raw pip stdout/stderr/report, tool versions, independent wheel graph and scope-limited verdict.', 'negative_reason': 'Certificates state the source requirement and rejected version; B and C also present root findings in their result. cryptography50.0.0 is below >=50.0.1; eth-account0.13.6 is below >=0.13.7.', 'positive_reason': 'Certificates expose forty-one selected distributions, active/inactive dependency edges, roots, hashes and native environment for review.', 'standalone_consumer_requirement': 'Keep job inputs and wheel cache with the output packet. A report JSON alone is not a self-contained portable closure.', 'common_human_reader': 'At review time technical JSON is inspectable. A common EN/FR reader should explain source-root negatives despite pip exit0 and retain the application-qualification limitation; later presentation work must not be scored as additional production acceptance.'}, 'audit_wall_seconds': time.perf_counter() - START}
target = ROOT / 'review/production-independent-review.json'
target.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'checks': checks, 'failures': failures, 'metrics': metrics, 'paired_timing': matched, 'report': str(target.relative_to(ROOT)), 'audit_wall_seconds': report['audit_wall_seconds']}, indent=2))
