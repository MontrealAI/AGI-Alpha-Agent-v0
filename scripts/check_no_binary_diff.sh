#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Guard against binary file changes in diffs.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BINARY_EXT_RE='\\.(wasm|zip|gz|png|jpg|jpeg|webp|gif|pdf|ico|mp4|mp3|woff2?|ttf|otf|bin|exe|dll|so|dylib)$'

resolve_base_sha() {
  if [[ -n "${BINARY_DIFF_BASE_SHA:-}" ]]; then
    echo "$BINARY_DIFF_BASE_SHA"
    return
  fi
  if [[ -n "${GITHUB_EVENT_PATH:-}" && -f "${GITHUB_EVENT_PATH:-}" ]]; then
    python - <<'PY'
import json
import os

path = os.environ.get("GITHUB_EVENT_PATH")
try:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    base = data.get("pull_request", {}).get("base", {}).get("sha")
    if base:
        print(base)
except Exception:
    pass
PY
    return
  fi
  if [[ -n "${GITHUB_BASE_REF:-}" ]]; then
    if git show-ref --verify --quiet "refs/remotes/origin/${GITHUB_BASE_REF}"; then
      git merge-base "origin/${GITHUB_BASE_REF}" HEAD
      return
    fi
  fi
  if git remote get-url origin >/dev/null 2>&1; then
    if ! git show-ref --verify --quiet refs/remotes/origin/main; then
      git fetch origin main --quiet || true
    fi
  fi
  if git show-ref --verify --quiet refs/remotes/origin/main; then
    git merge-base origin/main HEAD
    return
  fi
  if git show-ref --verify --quiet refs/heads/main; then
    git merge-base main HEAD
    return
  fi
  git rev-parse HEAD
}

BASE_SHA="$(resolve_base_sha)"
if [[ -z "$BASE_SHA" ]]; then
  echo "ERROR: Unable to determine base SHA for binary diff check." >&2
  exit 2
fi

binary_paths=()
while IFS= read -r -d '' status; do
  read -r -d '' path1 || true
  path2=""
  if [[ "$status" == R* || "$status" == C* ]]; then
    read -r -d '' path2 || true
  fi
  for candidate in "$path1" "$path2"; do
    if [[ -n "$candidate" && "$candidate" =~ $BINARY_EXT_RE ]]; then
      binary_paths+=("$candidate")
    fi
  done
done < <(git diff --name-status -z "${BASE_SHA}...HEAD")

if [[ "${#binary_paths[@]}" -gt 0 ]]; then
  printf "ERROR: Binary file changes detected in diff:\n" >&2
  printf "  %s\n" "${binary_paths[@]}" >&2
  exit 1
fi

if git diff --numstat "${BASE_SHA}...HEAD" | awk '$1 == "-" && $2 == "-" {exit 1}'; then
  exit 0
fi

echo "ERROR: Binary content diff detected via numstat." >&2
git diff --numstat "${BASE_SHA}...HEAD" | awk '$1 == "-" && $2 == "-" {print "  " $3}' >&2
exit 1
