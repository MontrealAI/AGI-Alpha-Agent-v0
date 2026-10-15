#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Evaluate supplied business assumptions, without queuing or external execution.
# Usage: API_TOKEN=<configured token> ./scripts/post_alpha_job.sh examples/job_evaluate_business.json
set -euo pipefail

JOB_FILE="${1:-examples/job_evaluate_business.json}"
HOST="${HOST:-localhost}"
PORT="${PORT:-8000}"
: "${API_TOKEN:?Set API_TOKEN to the configured orchestrator authentication token}"

for cmd in curl jq; do
  command -v "$cmd" >/dev/null || { echo "$cmd not found" >&2; exit 1; }
done

if ! jq -e 'keys == ["agent", "state"] and .agent == "alpha_execution" and (.state | type == "object")' "$JOB_FILE" >/dev/null; then
  echo "Unsupported job: provide agent=alpha_execution and a complete state. Nothing was submitted." >&2
  exit 1
fi

RESULT=$(jq -c '.state' "$JOB_FILE" | curl -fsS -X POST \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data-binary @- \
  "http://${HOST}:${PORT}/agent/alpha_execution/evaluate")
if ! printf '%s' "$RESULT" | jq -e '.status == "evaluated_supplied_assumptions" and .external_actions_performed == false and (.evaluation | type == "object")' >/dev/null; then
  echo "Server did not return a supplied-input evaluation." >&2
  exit 1
fi
printf '%s\n' "$RESULT"
