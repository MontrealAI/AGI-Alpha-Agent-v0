# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import numpy as np
import scipy


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def matrix(value, rows, cols):
    return isinstance(value, list) and len(value) == rows and all(isinstance(row, list) and len(row) == cols and all(finite(x) for x in row) for row in value)


def check_job(file):
    raw = Path(file).read_bytes()
    task = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
    require(task.get('schema') == 'agi-alpha-conductance-job/v1', 'UNSUPPORTED_SCHEMA')
    family = task.get('family')
    require(family in ('forward', 'inverse', 'design'), 'UNSUPPORTED_FAMILY')
    require(isinstance(task.get('id'), str) and 0 < len(task['id']) <= 128, 'INVALID_TASK_ID')
    require(task.get('provenance', {}).get('data_class') == 'synthetic-research', 'SYNTHETIC_RESEARCH_RIGHTS_REQUIRED')
    network = task['network']; n = network['node_count']; edges = network['edges']; ground = network['ground']
    require(integer(n) and 2 <= n <= 4096, 'NODE_SCOPE')
    require(isinstance(edges, list) and 1 <= len(edges) <= 32768, 'EDGE_SCOPE')
    require(isinstance(ground, list) and len(ground) == n and all(finite(x) and x >= 0 for x in ground), 'GROUND_SCOPE')
    adjacent = [[] for _ in range(n)]; seen = set()
    for edge in edges:
        require(isinstance(edge, list) and len(edge) == 3, 'EDGE_SCHEMA')
        left, right, weight = edge
        require(integer(left) and integer(right) and 0 <= left < n and 0 <= right < n and left != right, 'EDGE_ENDPOINT')
        require(finite(weight) and weight > 0, 'CONDUCTANCE_SCOPE')
        pair = tuple(sorted((left, right))); require(pair not in seen, 'DUPLICATE_EDGE'); seen.add(pair)
        adjacent[left].append(right); adjacent[right].append(left)
    visited = set()
    for seed in range(n):
        if seed in visited:
            continue
        todo = [seed]; visited.add(seed); grounded = False
        while todo:
            node = todo.pop(); grounded = grounded or ground[node] > 0
            for neighbor in adjacent[node]:
                if neighbor not in visited:
                    visited.add(neighbor); todo.append(neighbor)
        require(grounded, 'UNGROUNDED_COMPONENT')
    loads = task['loads']; require(isinstance(loads, list) and 1 <= len(loads) <= 16 and matrix(loads, len(loads), n), 'LOAD_SCOPE')
    if family == 'inverse':
        parameters = task['parameters']; groups = parameters['groups']; p = len(groups)
        require(1 <= p <= 32, 'PARAMETER_SCOPE'); used = set()
        for group in groups:
            require(isinstance(group, list) and group and all(integer(x) and 0 <= x < len(edges) for x in group), 'GROUP_SCOPE')
            require(len(set(group)) == len(group) and not used.intersection(group), 'GROUP_OVERLAP'); used.update(group)
        bounds = parameters['bounds']; require(matrix(bounds, p, 2) and all(0 < lo < hi for lo, hi in bounds), 'PARAMETER_BOUNDS')
        initial = parameters['initial']; require(isinstance(initial, list) and len(initial) == p and all(finite(v) and lo <= v <= hi for v, (lo, hi) in zip(initial, bounds)), 'INITIAL_PARAMETERS')
        observations = task['observations']; nodes = observations['nodes']
        require(isinstance(nodes, list) and nodes and all(integer(x) and 0 <= x < n for x in nodes) and len(set(nodes)) == len(nodes), 'OBSERVATION_NODES')
        require(matrix(observations['states'], len(loads), len(nodes)), 'OBSERVATION_SCOPE')
        prediction = task['prediction_loads']; require(isinstance(prediction, list) and 1 <= len(prediction) <= 16 and matrix(prediction, len(prediction), n), 'PREDICTION_SCOPE')
    if family == 'design':
        design = task['design']; indices = design['edge_indices']; count = len(indices)
        require(1 <= count <= 80 and all(integer(x) and 0 <= x < len(edges) for x in indices) and len(set(indices)) == count, 'DESIGN_INDEX_SCOPE')
        require(len(design['upper_bounds']) == count and all(finite(x) and x >= 0 for x in design['upper_bounds']), 'DESIGN_BOUNDS')
        require(len(design['costs']) == count and all(finite(x) and x > 0 for x in design['costs']), 'DESIGN_COSTS')
        require(finite(design['resource_budget']) and design['resource_budget'] >= 0, 'DESIGN_BUDGET')
    return {'accepted': True, 'schema': task['schema'], 'jobId': task['id'], 'jobSha256': hashlib.sha256(raw).hexdigest(),
            'family': family, 'nodeCount': n, 'loadCount': len(loads),
            'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__},
            'rights': {'license': 'Apache-2.0', 'dataClass': 'synthetic'},
            'permission': 'PROSPECTIVE_BOUNDED_RESEARCH_TRIAL', 'empiricalAdmissionNodeCounts': [225, 400],
            'thisJobNumericalAcceptance': 'PENDING', 'liveIdentityEnforcement': 'NOT_RUN', 'nativeAuthority': []}


if __name__ == '__main__':
    try:
        result = check_job(sys.argv[1])
    except Exception as error:
        result = {'accepted': False, 'reason': str(error)}
    print(json.dumps(result, allow_nan=False))
    if not result['accepted']:
        raise SystemExit(2)
