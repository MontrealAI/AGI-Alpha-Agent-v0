import hashlib
import json
from pathlib import Path

OUT = Path('/workspace/scratch/a54a233bfad9/alpha/studies/agi-alpha-microscopy-transfer-v1/hosted_trials/Eplus')
answers = json.loads((OUT / 'answers.json').read_text())
validation = json.loads((OUT / 'validation.json').read_text())
compile((OUT / 'solve.py').read_text(), str(OUT / 'solve.py'), 'exec')
assert len(answers) == 12 and [x['case_id'] for x in answers] == list(range(12))
assert sum(x['status'] == 'ACCEPT' for x in answers) == 8
assert sum(x['status'] == 'HOLD' for x in answers) == 3
assert sum(x['status'] == 'REJECT' for x in answers) == 1
assert answers[7]['objects'] == [] and answers[7]['label_count'] == 0
assert [o['label_id'] for o in answers[6]['objects']] == [-3, 11]
assert answers[5]['label_count'] == 3
for answer in answers:
    if answer['status'] == 'ACCEPT':
        assert answer['label_count'] == len(answer['objects'])
        for obj in answer['objects']:
            assert set(obj) == {'label_id', 'voxel_count', 'native_measure', 'mapped_measure',
                                'native_centroid_um', 'mapped_centroid_um'}
    else:
        assert isinstance(answer['reason'], str) and answer['reason']
checks = [x for x in validation['cases'] if x['scope_status'] == 'ACCEPT']
receipt = {
    'configuration': 'Eplus',
    'completed': True,
    'tool_invocations': 4,
    'nested_exec_command_invocations': 4,
    'inclusive_tool_api_calls': 8,
    'tool_count_basis': 'Four functions.exec invocations, each containing one exec_command invocation; eight if both layers are counted.',
    'observed_work': [
        {'call': 1, 'action': 'Read only supplied TASK.md, cases.json, expert rubric and authorized retained executable; list input files; verify retained SHA256 before use.'},
        {'call': 2, 'action': 'Read all twelve actual arrays and contracts; inspect dimensions, dtype, signed label counts, coordinate sums, calibration, affine semantics and source hashes.'},
        {'call': 3, 'action': 'Save solve.py; verify retained SHA256 again; invoke retained run(Path,Path) on a hand-calculated fixture and all twelve missions; inspect every returned status; independently validate accepted geometry; save answers and audit files.'},
        {'call': 4, 'action': 'Read back answer and validation files, check requested schema and preserved edge cases, compile saved source without writing bytecode, and save this receipt.'},
    ],
    'retained_executable': {
        'path': '/workspace/scratch/a54a233bfad9/alpha/studies/agi-alpha-microscopy-transfer-v1/integration/results/frozen-v1/received-artifact.py',
        'expected_sha256': 'a04326ce0504bfe3ac290b6cb65ee6f089cc66a607f70b7cc7869099250c77db',
        'observed_sha256': validation['artifact_sha256'],
        'verified_before_execution': True,
        'interface_used': 'run(Path, Path)',
        'calls': 13,
        'returned_statuses_inspected': True,
        'modifications': None,
    },
    'rubric_applied': validation['scope_checks'],
    'validation': {
        'known_case': 'PASS',
        'accepted_case_count': 8, 'held_case_count': 3, 'rejected_case_count': 1,
        'independent_method': 'Enumerate actual physical voxel centers; average native and mapped points; compute determinant by signed permutation expansion.',
        'max_measure_relative_error': max(x['max_measure_relative_error'] for x in checks),
        'max_centroid_absolute_error_um': max(x['max_centroid_absolute_error_um'] for x in checks),
        'relative_measure_tolerance': 1e-9,
        'absolute_centroid_tolerance_um': 1e-8,
        'measured_solver_wall_seconds': validation['measured_solver_wall_seconds'],
    },
    'corrections_performed': [],
    'costs': {
        'token_count': None, 'billing_amount': None, 'currency': None,
        'whole_trial_elapsed_seconds': None,
        'note': 'Token counts, billing, and whole-trial wall time were not instrumented. The reported solver runtime measures only the saved solver execution. No cost estimate is invented.'
    },
    'public_documentation_lookups': 0,
    'subagents_spawned': 0,
    'output_files': ['answers.json', 'solve.py', 'finalize.py', 'receipt.json', 'retained_results.json', 'validation.json',
                     'validation/known.npy', 'validation/known.json', 'validation/known_result.json'],
    'answers_sha256': hashlib.sha256((OUT / 'answers.json').read_bytes()).hexdigest(),
}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
print(json.dumps({'receipt': str(OUT / 'receipt.json'), 'answers_sha256': receipt['answers_sha256'],
                  'validation': receipt['validation'],
                  'files': [{'path': str(OUT / name), 'bytes': (OUT / name).stat().st_size} for name in receipt['output_files']]}, indent=2))
