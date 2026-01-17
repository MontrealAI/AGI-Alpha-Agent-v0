#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

binary_regex='\.(wasm|zip|gz|png|jpg|jpeg|webp|gif|pdf|ico|mp4|mp3|woff2?|ttf|otf|bin|exe|dll|so|dylib)$'

base_ref="${GITHUB_BASE_SHA:-}"

if [[ -z "${base_ref}" ]]; then
  if git rev-parse --verify origin/main >/dev/null 2>&1; then
    base_ref="origin/main"
  elif git remote get-url origin >/dev/null 2>&1; then
    git fetch origin main >/dev/null 2>&1 || true
    if git rev-parse --verify origin/main >/dev/null 2>&1; then
      base_ref="origin/main"
    fi
  else
    base_ref="main"
  fi
fi

if ! git rev-parse --verify "${base_ref}" >/dev/null 2>&1; then
  if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
    base_ref="HEAD~1"
    echo "Falling back to ${base_ref} for binary diff check." >&2
  else
    echo "Unable to resolve base reference '${base_ref}'. Set GITHUB_BASE_SHA to a valid commit." >&2
    exit 1
  fi
fi

name_status_matches=$(
  git diff --name-status "${base_ref}...HEAD" \
    | awk 'NF>=2 {for (i=2; i<=NF; i++) print $i}' \
    | grep -Ei "${binary_regex}" || true
)

numstat_matches=$(
  git diff --numstat "${base_ref}...HEAD" \
    | awk '$1 == "-" && $2 == "-" {print $3}' \
    | grep -Ei "${binary_regex}" || true
)

if [[ -n "${name_status_matches}" || -n "${numstat_matches}" ]]; then
  echo "Binary file changes detected in diff against ${base_ref}:" >&2
  if [[ -n "${name_status_matches}" ]]; then
    echo "- Name-status matches:" >&2
    echo "${name_status_matches}" >&2
  fi
  if [[ -n "${numstat_matches}" ]]; then
    echo "- Numstat binary matches:" >&2
    echo "${numstat_matches}" >&2
  fi
  exit 1
fi

echo "No binary file changes detected against ${base_ref}."
