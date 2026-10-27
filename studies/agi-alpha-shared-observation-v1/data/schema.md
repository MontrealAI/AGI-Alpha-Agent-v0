# Frozen mission contract, v1

This finite Bayesian simulator is not an orbit propagator, covariance validator or spacecraft controller.
All cases are synthetic, all monetary inputs are assumptions, and every action has execution_authorized=false.

JSON input:
- schema: "shared-observation-mission/v1"
- mission_id: unique string
- evidence_type: "synthetic"
- calibration_scope: string
- states: unique nonempty string list, at most 12
- prior: probability vector over states (nonnegative, sums to 1)
- observation: {id, usable: bool, rights_cleared: bool, calibration_scope: string,
  outcomes: [{id, likelihood: vector over states, arrival_hours: nonnegative float or null}]}
  For each state, outcome likelihoods sum to 1. A null arrival is no result. At most 12 outcomes.
- operators: [{id, risk_limit, decision_deadline_hours, fallback_action, actions:
  [{id, risk_by_state: vector, cost_usd, latest_start_hours}]}], at most 6 operators and 6 actions each.
  The decision deadline is the last moment the operator will wait for an observation. An action must
  start no later than latest_start_hours. All risks are probabilities in [0,1]; costs and times are nonnegative.
  Action risks/costs already encode the supplied bounded consequences; inter-operator maneuver interactions
  are outside this finite model and a changed interaction requires a new model. We do not learn physical risks.

Each operator's baseline selects the lowest cost action at time 0 whose prior-averaged risk is <= risk_limit.
For each timely outcome (arrival <= decision deadline), recompute Bayes posterior and select the lowest cost
available action that meets the original risk_limit. Cost/id breaks ties deterministically.
For each operator separately, aggregate every null/late outcome into ONE timeout likelihood, then apply Bayes.
The timeout action must be the declared fallback_action and must be available at decision_deadline_hours.
Zero-probability branches are unreachable, with no claim of acceptance. Every positive-probability branch must
pass; an expected-risk average does not substitute for these branch constraints. All equality boundaries allow
equality, with numerical tolerance 1e-12. If any branch is impossible, shared observation is refused while the
baseline remains separately reportable. Unusable sensor, mismatched calibration scope or uncleared rights
refuse observation before any value is claimed. No expected information benefit is guaranteed.

CLI: python capability/compiler.py --mission INPUT.json --output OUTPUT.json [--profile capability/sensor_profile.json]
Profile contains only scope/contract limitations; no evaluation instances or answers. It is not a calibrated sensor model.
Outputs: schema shared-observation-result/v1, mission_id, input_sha256, observation_accepted, operators,
total_baseline_cost, total_contingent_cost, total_value_of_information, execution_authorized:false.
Each operator result: id, baseline_cost, baseline_action, contingent_cost, value_of_information, valid,
peak_action_reserve, branches. Costs exclude acquisition and commercial fees. Invalid contingent costs/value are null.
Branch: id, probability, posterior, observed_at_hours, action, risk, cost_usd, valid, reachable.
All timely branches and aggregate timeout are retained, including adverse results and zero-probability branches.

Independent confirmation generation must not inspect compiler.py. Root freezes source and development records
before reading confirmation cases or outputs. Conventional exact enumeration gets identical information and rights.
