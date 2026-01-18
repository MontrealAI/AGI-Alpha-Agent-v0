#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BASE_SHA="${BASE_SHA:-}"
BINARY_REGEX='\.('"'"'wasm|zip|gz|png|jpg|jpeg|webp|gif|pdf|ico|mp4|mp3|woff2?|ttf|otf|bin|exe|dll|so|dylib'"'"')$'

if [[ -z "$BASE_SHA" && -n "${GITHUB_EVENT_PATH:-}" && -f "$GITHUB_EVENT_PATH" ]]; then
    BASE_SHA="$(
        python - <<'PY'
import json
from pathlib import Path

event_path = Path(__import__("os").environ.get("GITHUB_EVENT_PATH", ""))
if not event_path.exists():
    raise SystemExit(0)

data = json.loads(event_path.read_text())
base_sha = (
    data.get("pull_request", {}).get("base", {}).get("sha")
    or data.get("merge_group", {}).get("base_sha")
    or data.get("before")
    or ""
)
print(base_sha)
PY
    )"
fi

if [[ -z "$BASE_SHA" ]]; then
    if ! git show-ref --verify --quiet refs/remotes/origin/main; then
        git fetch --no-tags --depth=1 origin main >/dev/null 2>&1 || true
    fi
    if git show-ref --verify --quiet refs/remotes/origin/main; then
        BASE_SHA="origin/main"
    fi
fi

if [[ -n "$BASE_SHA" ]] && ! git rev-parse --verify "$BASE_SHA^{commit}" >/dev/null 2>&1; then
    echo "Unable to resolve base SHA for binary diff check." >&2
    exit 1
fi

binary_paths=()
if [[ -n "$BASE_SHA" ]]; then
    diff_name_status=$(git diff --name-status "$BASE_SHA"...HEAD)
    diff_numstat=$(git diff --numstat "$BASE_SHA"...HEAD)
else
    diff_name_status=$(git diff --name-status)
    diff_numstat=$(git diff --numstat)
fi

while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    status=$(echo "$line" | awk '{print $1}')
    if [[ "$status" == R* ]]; then
        old_path=$(echo "$line" | awk '{print $2}')
        new_path=$(echo "$line" | awk '{print $3}')
        for path in "$old_path" "$new_path"; do
            if [[ "$path" =~ $BINARY_REGEX ]]; then
                binary_paths+=("$path")
            fi
        done
    else
        path=$(echo "$line" | awk '{print $2}')
        if [[ "$path" =~ $BINARY_REGEX ]]; then
            binary_paths+=("$path")
        fi
    fi
done <<< "$diff_name_status"

binary_numstat=$(echo "$diff_numstat" | awk '$1=="-" && $2=="-" {print $3}')

base_label="${BASE_SHA:-working tree}"

if (( ${#binary_paths[@]} > 0 )) || [[ -n "$binary_numstat" ]]; then
    echo "Binary file changes detected in diff against $base_label:" >&2
    if (( ${#binary_paths[@]} > 0 )); then
        printf '  %s\n' "${binary_paths[@]}" >&2
    fi
    if [[ -n "$binary_numstat" ]]; then
        printf '  %s\n' "$binary_numstat" >&2
    fi
    exit 1
fi

echo "No binary file changes detected against $base_label."
