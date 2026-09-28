#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Supported local lab; historical container integration is explicit opt-in.
set -Eeuo pipefail
demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == "--legacy" ]]; then
  shift
  printf '%s\n' 'Launching the preserved research stack. See RESEARCH_ARCHIVE.md; this is not the supported learning lab.' >&2
  exec bash "$demo_dir/legacy_run_experience_demo.sh" "$@"
fi
repo_dir="$(cd "$demo_dir/../../.." && pwd)"
export PYTHONPATH="$repo_dir${PYTHONPATH:+:$PYTHONPATH}"
if [[ $# -eq 0 || "${1:-}" == "--port" ]]; then
  set -- --serve "$@"
fi
exec "${PYTHON:-python3}" -m alpha_factory_v1.demos.era_of_experience "$@"
