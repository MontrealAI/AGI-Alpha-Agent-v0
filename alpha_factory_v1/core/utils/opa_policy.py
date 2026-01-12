# SPDX-License-Identifier: Apache-2.0
"""Lightweight helpers for evaluating OPA policies."""
from __future__ import annotations

import re
from pathlib import Path


def _find_policy_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "policies"
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parents[2] / "policies"


_POLICY_DIR = _find_policy_dir()


def _load_banned_hosts() -> set[str]:
    policy_path = _POLICY_DIR / "deny_finance.rego"
    try:
        text = policy_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return set()
    m = re.search(r"banned_hosts\s*=\s*{([^}]*)}", text, re.DOTALL)
    if not m:
        return set()
    hosts = [h.strip().strip('"') for h in m.group(1).split(",") if h.strip()]
    return set(hosts)


_BANNED_HOSTS = _load_banned_hosts()


def _load_insider_patterns() -> list[str]:
    policy_path = _POLICY_DIR / "deny_insider.rego"
    try:
        text = policy_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    return re.findall(r're_match\("([^"]+)",\s*input.text\)', text)


_INSIDER_RE = [re.compile(pat, re.IGNORECASE) for pat in _load_insider_patterns()]


def _load_exfil_patterns() -> list[str]:
    policy_path = _POLICY_DIR / "deny_exfil.rego"
    try:
        text = policy_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    return re.findall(r're_match\("([^"]+)",\s*input.text\)', text)


_EXFIL_RE = [re.compile(pat, re.IGNORECASE) for pat in _load_exfil_patterns()]


def violates_finance_policy(code: str) -> bool:
    """Return ``True`` if ``code`` references a banned finance API host."""
    for host in _BANNED_HOSTS:
        if host in code:
            return True
    return False


def violates_insider_policy(text: str) -> bool:
    """Return ``True`` if ``text`` matches the insider trading policy."""
    for pat in _INSIDER_RE:
        if pat.search(text):
            return True
    return False


def violates_exfil_policy(text: str) -> bool:
    """Return ``True`` if ``text`` matches exfiltration patterns."""
    for pat in _EXFIL_RE:
        if pat.search(text):
            return True
    return False
