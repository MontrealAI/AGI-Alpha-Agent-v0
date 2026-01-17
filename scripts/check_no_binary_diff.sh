#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Fail if the current diff modifies any binary files.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BINARY_REGEX='\.(wasm|zip|gz|png|jpg|jpeg|webp|gif|pdf|ico|mp4|mp3|woff2?|ttf|otf|bin|exe|dll|so|dylib)$'

resolve_base_sha() {
  local base_sha=""
  if [[ -n "${GITHUB_EVENT_PATH:-}" && -f "${GITHUB_EVENT_PATH}" ]]; then
    base_sha=$(python - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ.get("GITHUB_EVENT_PATH", ""))
if path.is_file():
    data = json.loads(path.read_text())
    pr = data.get("pull_request")
    if pr and pr.get("base"):
        print(pr["base"].get("sha", ""))
PY
    )
  fi

  if [[ -z "$base_sha" && -n "${GITHUB_BASE_REF:-}" ]]; then
    if git rev-parse --verify "origin/${GITHUB_BASE_REF}^{commit}" >/dev/null 2>&1; then
      base_sha="origin/${GITHUB_BASE_REF}"
    fi
  fi

  if [[ -z "$base_sha" ]]; then
    if git rev-parse --verify origin/main >/dev/null 2>&1; then
      base_sha="origin/main"
    else
      base_sha="HEAD"
    fi
  fi
  echo "$base_sha"
}

BASE_SHA="$(resolve_base_sha)"

if [[ "$BASE_SHA" == "HEAD" ]]; then
  diff_range=()
else
  diff_range=("${BASE_SHA}...HEAD")
fi

binary_numstat=$(git diff --numstat "${diff_range[@]}" | awk '$1 == "-" && $2 == "-" {print $3}')
if [[ -n "$binary_numstat" ]]; then
  echo "Binary diffs detected via numstat:" >&2
  echo "$binary_numstat" >&2
  exit 1
fi

changed_paths=$(git diff --name-status "${diff_range[@]}" | awk '{print $2 "\n" $3}')
if [[ -n "$changed_paths" ]]; then
  binary_paths=$(printf '%s\n' "$changed_paths" | rg -i "$BINARY_REGEX" || true)
  if [[ -n "$binary_paths" ]]; then
    echo "Binary file changes detected:" >&2
    echo "$binary_paths" >&2
    exit 1
  fi
fi

echo "No binary diffs detected."
