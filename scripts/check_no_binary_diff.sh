#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Fail if the diff introduces binary files.
set -euo pipefail

binary_pattern='\\.(wasm|zip|gz|png|jpg|jpeg|webp|gif|pdf|ico|mp4|mp3|woff2?|ttf|otf|bin|exe|dll|so|dylib)$'

resolve_base() {
    local base=""
    if [[ -n "${GITHUB_EVENT_PATH:-}" && -f "${GITHUB_EVENT_PATH}" ]]; then
        base="$(
            python - <<'PY'
import json
import os

path = os.environ.get("GITHUB_EVENT_PATH")
if not path:
    raise SystemExit(0)

try:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    base = payload.get("pull_request", {}).get("base", {}).get("sha")
    if base:
        print(base)
except Exception:
    pass
PY
        )"
    fi

    if [[ -z "${base}" ]]; then
        base="origin/main"
        if ! git rev-parse --verify "${base}^{commit}" >/dev/null 2>&1; then
            git fetch --quiet origin main
        fi
    fi

    echo "${base}"
}

base_sha="$(resolve_base)"
echo "Checking binary diffs against ${base_sha}"

name_status="$(git diff --name-status "${base_sha}...HEAD")"
if [[ -n "${name_status}" ]]; then
    changed_paths="$(printf "%s\n" "${name_status}" | awk '{for (i=2; i<=NF; i++) print $i}')"
    if printf "%s\n" "${changed_paths}" | rg -i "${binary_pattern}" >/dev/null; then
        echo "::error::Binary file changes detected in git diff."
        printf "%s\n" "${changed_paths}" | rg -i "${binary_pattern}" || true
        exit 1
    fi
fi

binary_numstat="$(git diff --numstat "${base_sha}...HEAD" | awk '$1 == "-" && $2 == "-" {print $3}')"
if [[ -n "${binary_numstat}" ]]; then
    echo "::error::Binary file content changes detected in git diff."
    printf "%s\n" "${binary_numstat}"
    exit 1
fi

echo "No binary diffs detected."
