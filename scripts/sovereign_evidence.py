# SPDX-License-Identifier: Apache-2.0
"""Validate public acceptance against the exact committed Sovereign packets."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def verify_report(report: dict[str, Any], commit: str, version: str, origin: str) -> None:
    """Require all six route/scenario downloads, accessibility and release identity."""
    if (report.get('schema') != 'sovereign-browser-v1' or report.get('passed') is not True
        or report.get('origin') != origin or report.get('native_workflow') is not False
        or report.get('browser_errors') != [] or report.get('axe_checked') is not True
        or report.get('mobile_no_overflow') is not True or report.get('release', {}).get('commit') != commit
        or report.get('release', {}).get('version') != version):
        raise ValueError('Sovereign acceptance must match the canonical release and required browser checks')
    demo = 'sovereign_agentic_agialpha_agent_v0'
    fixture = Path(__file__).resolve().parents[1] / 'alpha_factory_v1/demos' / demo / 'recorded.json'
    cases = json.loads(fixture.read_text(encoding='utf-8'))['cases']
    expected = {(prefix+demo+'/', case):json.loads(value['packet_json'])['sha256']
                for prefix in ('','alpha_factory_v1/demos/') for case, value in cases.items()}
    seen = set()
    for item in report.get('scenarios', []):
        key = (item.get('route'), item.get('case'))
        if key in seen or key not in expected or item.get('verified') is not True or item.get('sha256') != expected[key]:
            raise ValueError('Sovereign public packet is missing, duplicated, unverified or differs from the release')
        seen.add(key)
    if seen != set(expected):
        raise ValueError('Sovereign must pass both routes and all three scenarios')
