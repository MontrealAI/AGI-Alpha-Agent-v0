#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build from the repository root and retain the offline decision bundle on the host.
set -euo pipefail

usage() {
  echo "Usage: $0 [--case NAME] [--output-dir DIRECTORY]"
  echo "Build and run the offline enterprise planner; no credentials are forwarded."
  echo "Cases: industrial, lean-budget, review-bottleneck, severe-downside, evidence-first"
  echo "For custom JSON or legacy integrations, use the Python CLI documented in README.md."
}

case_name="industrial"
output_dir="$PWD/business3-runs"
while (($#)); do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --case|--output-dir)
      if (($# < 2)); then echo "Missing value for $1" >&2; exit 2; fi
      if [[ "$1" == "--case" ]]; then case_name="$2"; else output_dir="$2"; fi
      shift 2 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done
case "$case_name" in
  industrial|lean-budget|review-bottleneck|severe-downside|evidence-first) ;;
  *) echo "Unknown case: $case_name" >&2; usage; exit 2 ;;
esac
command -v docker >/dev/null 2>&1 || { echo "Docker is required. Start Docker Desktop or use the Python CLI." >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker is not running. Start Docker Desktop and retry." >&2; exit 1; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root_dir="$(cd "$script_dir/../../.." && pwd)"
mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd)"
image="alpha_business_v3:1.13.0"
docker build -t "$image" -f "$script_dir/Dockerfile" "$root_dir"
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 512m --cpus 2 --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  --user "$(id -u):$(id -g)" -v "$output_dir:/output" \
  "$image" --case "$case_name" --output /output
echo "Evidence retained in $output_dir"
