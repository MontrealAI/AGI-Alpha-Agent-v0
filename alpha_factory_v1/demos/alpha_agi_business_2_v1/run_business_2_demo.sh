#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Run one supplied-input computation. No image build, provider, service or payment.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root_dir="$(cd -- "$script_dir/../../.." && pwd)"
python_bin="${PYTHON:-python3}"
command -v "$python_bin" >/dev/null 2>&1 || { echo "Python 3.11–3.13 is required" >&2; exit 2; }
# Keep the caller's working directory so relative --input paths retain their meaning.
export PYTHONPATH="$root_dir${PYTHONPATH:+:$PYTHONPATH}"
exec "$python_bin" -m alpha_factory_v1.demos.alpha_agi_business_2_v1.planning "$@"
