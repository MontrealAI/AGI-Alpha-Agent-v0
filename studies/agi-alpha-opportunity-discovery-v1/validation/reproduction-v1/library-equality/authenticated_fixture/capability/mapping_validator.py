# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse
import json
from pathlib import Path

def validate(item: dict) -> list[str]:
    errors = []
    required = ['purpose', 'effect_measure', 'effect_input', 'variance_input', 'time_meaning', 'dependence_limit', 'authority_limit']
    errors += ['missing:' + key for key in required if not item.get(key)]
    if item.get('variance_derivation') == 'equal_arms_from_total_n' and item.get('equal_arms_supported') is not True:
        errors.append('unsupported_equal_arm_assumption')
    if item.get('effect_measure') == 'SMD' and item.get('promised_units') in ['kg/ha', 'IQ_points']:
        errors.append('standardized_effect_cannot_be_relabelled_as_physical_units')
    if item.get('retraction_decision_automatic') is True:
        errors.append('numerical_output_does_not_authorize_editorial_decision')
    return errors

if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args()
    print(json.dumps({'issues':validate(json.loads(a.path.read_text()))},indent=2))
