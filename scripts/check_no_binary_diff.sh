#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

binary_regex='\.('"'"'wasm|zip|gz|png|jpg|jpeg|webp|gif|pdf|ico|mp4|mp3|woff2?|ttf|otf|bin|exe|dll|so|dylib)'"'"'$'

get_base_ref() {
  local base_ref=""

  if [[ -n "${GITHUB_EVENT_PATH:-}" && -f "${GITHUB_EVENT_PATH}" ]]; then
    base_ref="$(python - <<'PY'
import json
import os

path = os.environ.get("GITHUB_EVENT_PATH")
if path:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        payload = {}
    pull_request = payload.get("pull_request") or {}
    base = pull_request.get("base") or {}
    sha = base.get("sha") or ""
    if sha:
        print(sha)
PY
)"
  fi

  if [[ -z "$base_ref" && -n "${GITHUB_BASE_SHA:-}" ]]; then
    base_ref="$GITHUB_BASE_SHA"
  fi

  if [[ -z "$base_ref" ]]; then
    base_ref="origin/main"
    if ! git rev-parse --verify "$base_ref^{commit}" >/dev/null 2>&1; then
      git fetch --quiet origin main || true
    fi
    if ! git rev-parse --verify "$base_ref^{commit}" >/dev/null 2>&1; then
      base_ref="main"
    fi
  fi

  echo "$base_ref"
}

BASE_REF="$(get_base_ref)"
if ! git rev-parse --verify "$BASE_REF^{commit}" >/dev/null 2>&1; then
  echo "ERROR: Unable to resolve base ref for diff checks: $BASE_REF" >&2
  exit 1
fi

mapfile -t diff_lines < <(git diff --name-status "$BASE_REF...HEAD")
binary_hits=()

for line in "${diff_lines[@]}"; do
  [[ -z "$line" ]] && continue
  status="$(cut -f1 <<<"$line")"
  path1="$(cut -f2 <<<"$line")"
  path2="$(cut -f3 <<<"$line" || true)"
  for candidate in "$path1" "$path2"; do
    [[ -z "$candidate" ]] && continue
    if [[ "$candidate" =~ $binary_regex ]]; then
      binary_hits+=("$status	$path1${path2:+	$path2}")
      break
    fi
  done
done

if [[ ${#binary_hits[@]} -gt 0 ]]; then
  echo "ERROR: Binary path changes detected in diff against $BASE_REF:" >&2
  printf '  %s\n' "${binary_hits[@]}" >&2
  exit 1
fi

binary_numstat="$(git diff --numstat "$BASE_REF...HEAD" | awk '$1=="-" && $2=="-" {print $0}')"
if [[ -n "$binary_numstat" ]]; then
  echo "ERROR: Binary file changes detected via numstat against $BASE_REF:" >&2
  echo "$binary_numstat" >&2
  exit 1
fi

echo "No binary file changes detected against $BASE_REF."
