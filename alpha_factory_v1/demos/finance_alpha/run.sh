#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "$demo_dir/../../.." && pwd)"
python_bin="${PYTHON:-python3}"
"$python_bin" - <<'PY'
import sys
if not (3, 11) <= sys.version_info[:2] < (3, 14):
    sys.exit("Finance Alpha requires Python 3.11–3.13")
PY
cd -- "$repo_dir"
exec "$python_bin" -m alpha_factory_v1.demos.finance_alpha "$@"
