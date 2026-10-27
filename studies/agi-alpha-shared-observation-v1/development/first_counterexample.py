# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

prior_danger = 0.02
risk_if_danger = 0.002
timeout_given_danger, timeout_given_safe = 0.29, 0.04
timeout_probability = prior_danger * timeout_given_danger + (1 - prior_danger) * timeout_given_safe
posterior_danger = prior_danger * timeout_given_danger / timeout_probability
result = {
    "evidence_type": "executed_finite_counterexample_with_synthetic_probabilities",
    "provenance": "Reviewer-suggested design challenge; not a measured ordinary-user configuration.",
    "risk_limit": 0.0001,
    "prior_risk": prior_danger * risk_if_danger,
    "timeout_probability": timeout_probability,
    "timeout_conditional_risk": posterior_danger * risk_if_danger,
    "prior_based_timeout_check_accepts": prior_danger * risk_if_danger <= 0.0001,
    "correct_conditional_timeout_check_accepts": posterior_danger * risk_if_danger <= 0.0001,
    "revision": "Condition on operator-specific timeout event; preserve a safe fixed fallback and its reserve.",
    "execution_authorized": False,
}
Path(__file__).with_name("first_counterexample.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
