from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import math
import time
from pathlib import Path

import numpy as np

BASE = Path('/workspace/scratch/a54a233bfad9/alpha/studies/agi-alpha-microscopy-transfer-v1/hosted_trials')
INPUT = BASE / 'inputs'
OUTPUT = BASE / 'Eplus'
ARTIFACT = BASE.parent / 'integration/results/frozen-v1/received-artifact.py'
EXPECTED_SHA256 = 'a04326ce0504bfe3ac290b6cb65ee6f089cc66a607f70b7cc7869099250c77db'
SCALES = {'micrometer': 1.0, 'um': 1.0, 'nanometer': 0.001, 'nm': 0.001,
          'millimeter': 1000.0, 'mm': 1000.0, 'meter': 1e6, 'm': 1e6}
METRICS = {'label_count', 'native_measure', 'mapped_measure', 'native_centroid', 'mapped_centroid'}
OBJECT_FIELDS = ('label_id', 'voxel_count', 'native_measure', 'mapped_measure',
                 'native_centroid_um', 'mapped_centroid_um')
SCOPE_CHECKS = [
    'Exact source-file SHA256 identity',
    'Nonempty 2D/3D integer array, zero background, every nonzero signed label one region',
    'Explicit source and target axes; matrix columns follow source, rows follow target',
    'Finite positive calibrated spacing; spacing and origin converted per axis to micrometers',
    'Supplied label support, label identity, geometric pushforward, supported metrics only',
    'Explicit nonsingular homogeneous affine in physical micrometers',
    'Native measure is voxel count times calibrated voxel measure',
    'Mapped measure uses absolute determinant; centroids use voxel-center coordinates',
    'No biological completeness, intensity, topology, resampling, or new segmentation inferred',
]


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def determinant_expansion(matrix):
    n = len(matrix)
    terms = []
    for p in itertools.permutations(range(n)):
        inversions = sum(p[i] > p[j] for i in range(n) for j in range(i + 1, n))
        terms.append((-1 if inversions % 2 else 1) * math.prod(float(matrix[i][p[i]]) for i in range(n)))
    return math.fsum(terms)


def independent_scope(labels, c, digest):
    if digest != c['source_sha256']:
        return 'REJECT', 'Actual file SHA256 differs from contract source SHA256.'
    if labels.ndim not in (2, 3) or labels.dtype.kind not in 'iu' or any(s <= 0 for s in labels.shape):
        return 'REJECT', 'Requires a nonempty 2D/3D integer array.'
    d = labels.ndim
    if c['schema'] != 'microscopy-moments/v1':
        return 'HOLD', 'Unknown contract schema.'
    if c['object_definition'] != 'label_id':
        return 'HOLD', 'Unsupported object definition.'
    if c['coverage'] != 'provided_label_support':
        return 'HOLD', 'Complete biological objects cannot be inferred from provided support.'
    if c['map_semantics'] != 'geometric_pushforward':
        return 'HOLD', 'Unknown map semantics.'
    if not c['metrics'] or set(c['metrics']) - METRICS:
        return 'HOLD', 'Unsupported requested metric; intensity data are absent.'
    for axes in [c['source_axes'], c['target_axes']]:
        if len(axes) != d or len(set(axes)) != d or set(axes) - {'x', 'y', 'z'}:
            return 'REJECT', 'Invalid spatial axis names.'
    if set(c['source_axes']) != set(c['target_axes']):
        return 'HOLD', 'Source and target physical axes differ.'
    if len(c['units']) != d or any(unit not in SCALES for unit in c['units']):
        return 'HOLD', 'Unrecognized per-axis physical units.'
    spacing = [x * SCALES[u] for x, u in zip(c['spacing'], c['units'])]
    origin = [x * SCALES[u] for x, u in zip(c['origin'], c['units'])]
    if len(spacing) != d or len(origin) != d or not all(math.isfinite(x) and x > 0 for x in spacing) or not all(math.isfinite(x) for x in origin):
        return 'REJECT', 'Invalid physical calibration.'
    affine = np.asarray(c['affine'], dtype=float)
    if affine.shape != (d + 1, d + 1) or not np.isfinite(affine).all():
        return 'REJECT', 'Invalid transform shape or coefficients.'
    if not np.array_equal(affine[-1], np.r_[np.zeros(d), 1.0]):
        return 'HOLD', 'Non-affine homogeneous last row; projective map is out of scope.'
    linear = affine[:d, :d]
    if determinant_expansion(linear) == 0 or np.linalg.cond(linear) > 1e12:
        return 'HOLD', 'Singular or unstable affine.'
    return 'ACCEPT', 'All supplied mission requirements are in scope.'


def independent_objects(labels, c):
    d = labels.ndim
    spacing = [float(c['spacing'][i]) * SCALES[c['units'][i]] for i in range(d)]
    origin = [float(c['origin'][i]) * SCALES[c['units'][i]] for i in range(d)]
    linear = [row[:d] for row in c['affine'][:d]]
    translation = [row[d] for row in c['affine'][:d]]
    jacobian = abs(determinant_expansion(linear))
    objects = []
    for label in np.unique(labels):
        if int(label) == 0:
            continue
        indices = np.argwhere(labels == label)
        # Enumerate and map every physical voxel center, independently of artifact centroid propagation.
        native_points = [[origin[j] + int(index[j]) * spacing[j] for j in range(d)] for index in indices]
        mapped_points = [[math.fsum(linear[j][k] * point[k] for k in range(d)) + translation[j]
                          for j in range(d)] for point in native_points]
        count = len(indices)
        native_measure = count * math.prod(spacing)
        objects.append({
            'label_id': int(label), 'voxel_count': count,
            'native_measure': native_measure, 'mapped_measure': native_measure * jacobian,
            'native_centroid_um': [math.fsum(p[j] for p in native_points) / count for j in range(d)],
            'mapped_centroid_um': [math.fsum(p[j] for p in mapped_points) / count for j in range(d)],
        })
    return objects


def compare_objects(actual, expected):
    assert len(actual) == len(expected)
    max_measure_relative_error = 0.0
    max_centroid_absolute_error_um = 0.0
    for a, e in zip(actual, expected):
        assert a['label_id'] == e['label_id'] and a['voxel_count'] == e['voxel_count']
        for key in ('native_measure', 'mapped_measure'):
            assert math.isclose(a[key], e[key], rel_tol=1e-9, abs_tol=0.0), (key, a, e)
            max_measure_relative_error = max(max_measure_relative_error, abs(a[key] - e[key]) / abs(e[key]))
        for key in ('native_centroid_um', 'mapped_centroid_um'):
            assert len(a[key]) == len(e[key])
            for av, ev in zip(a[key], e[key]):
                assert abs(av - ev) <= 1e-8, (key, av, ev)
                max_centroid_absolute_error_um = max(max_centroid_absolute_error_um, abs(av - ev))
    return {'max_measure_relative_error': max_measure_relative_error,
            'max_centroid_absolute_error_um': max_centroid_absolute_error_um}


def main():
    started = time.perf_counter()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    artifact_digest = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
    assert artifact_digest == EXPECTED_SHA256, 'Retained executable checksum mismatch'
    spec = importlib.util.spec_from_file_location('verified_retained_artifact', ARTIFACT)
    retained = importlib.util.module_from_spec(spec)
    # Avoid writing bytecode anywhere outside the assigned output directory.
    import sys
    sys.dont_write_bytecode = True
    spec.loader.exec_module(retained)

    # Hand-calculated fixture: signed IDs, mixed units, target-axis reorder and reflection.
    known_dir = OUTPUT / 'validation'
    known_dir.mkdir(exist_ok=True)
    known_labels = np.array([[-3, 0], [7, -3]], dtype=np.int16)
    known_path = known_dir / 'known.npy'
    np.save(known_path, known_labels)
    known_contract = {
        'schema': 'microscopy-moments/v1', 'mission_id': 'known-independent-fixture',
        'source_sha256': hashlib.sha256(known_path.read_bytes()).hexdigest(),
        'source_axes': ['y', 'x'], 'target_axes': ['x', 'y'],
        'spacing': [1000, 2], 'units': ['nanometer', 'micrometer'], 'origin': [2000, -1],
        'object_definition': 'label_id', 'coverage': 'provided_label_support',
        'map_semantics': 'geometric_pushforward',
        'affine': [[0, 2, 5], [3, 0, -4], [0, 0, 1]],
        'metrics': sorted(METRICS),
    }
    known_contract_path = known_dir / 'known.json'
    save(known_contract_path, known_contract)
    known_result = retained.run(known_path, known_contract_path)
    assert known_result['status'] == 'ACCEPT', known_result
    assert known_result['label_count'] == 2
    known_expected = [
        {'label_id': -3, 'voxel_count': 2, 'native_measure': 4.0, 'mapped_measure': 24.0,
         'native_centroid_um': [2.5, 0.0], 'mapped_centroid_um': [5.0, 3.5]},
        {'label_id': 7, 'voxel_count': 1, 'native_measure': 2.0, 'mapped_measure': 12.0,
         'native_centroid_um': [3.0, -1.0], 'mapped_centroid_um': [3.0, 5.0]},
    ]
    known_errors = compare_objects(known_result['objects'], known_expected)
    save(known_dir / 'known_result.json', known_result)

    cases = json.loads((INPUT / 'cases.json').read_text())
    answers, raw_results, audits = [], [], []
    for case in cases:
        labels_path, contract_path = INPUT / case['array'], INPUT / case['contract']
        labels = np.load(labels_path, allow_pickle=False)
        contract = json.loads(contract_path.read_text())
        digest = hashlib.sha256(labels_path.read_bytes()).hexdigest()
        expected_status, scope_reason = independent_scope(labels, contract, digest)
        result = retained.run(labels_path, contract_path)
        # Inspect the actual return status. Exit codes or geometric plausibility are not acceptance.
        assert result['status'] == expected_status, (case, expected_status, result)
        answer = {'case_id': case['case_id'], 'status': result['status']}
        audit = {'case_id': case['case_id'], 'array_shape': list(labels.shape), 'array_dtype': str(labels.dtype),
                 'actual_source_sha256': digest, 'source_sha256_matches': digest == contract['source_sha256'],
                 'source_axes': contract['source_axes'], 'target_axes': contract['target_axes'],
                 'scope_status': expected_status, 'scope_reason': scope_reason,
                 'retained_status_inspected': result['status']}
        if result['status'] == 'ACCEPT':
            expected_objects = independent_objects(labels, contract)
            assert result['label_count'] == len(expected_objects)
            audit.update(compare_objects(result['objects'], expected_objects))
            answer['label_count'] = result['label_count']
            answer['objects'] = [{key: obj[key] for key in OBJECT_FIELDS} for obj in result['objects']]
        else:
            answer['reason'] = result['reason']
            audit['retained_reason'] = result['reason']
        answers.append(answer)
        raw_results.append({'case_id': case['case_id'], 'result': result})
        audits.append(audit)
    assert [a['case_id'] for a in answers] == [c['case_id'] for c in cases]
    save(OUTPUT / 'answers.json', answers)
    save(OUTPUT / 'retained_results.json', raw_results)
    save(OUTPUT / 'validation.json', {
        'artifact_sha256': artifact_digest, 'scope_checks': SCOPE_CHECKS,
        'known_case': {'status': 'PASS', 'expected_objects': known_expected, **known_errors},
        'cases': audits, 'measured_solver_wall_seconds': time.perf_counter() - started,
        'relative_measure_tolerance': 1e-9, 'absolute_centroid_tolerance_um': 1e-8,
    })
    print(json.dumps({'answers_written': str(OUTPUT / 'answers.json'),
                      'case_statuses': [{'case_id': a['case_id'], 'status': a['status'],
                                         'label_count': a.get('label_count'), 'reason': a.get('reason')}
                                        for a in answers], 'known_case': 'PASS',
                      'all_accepted_results_independently_validated': True}, indent=2))


if __name__ == '__main__':
    main()
