# Clarification of the verified-design deliverable

Recorded 2026-10-27 after the economic policy freeze, before the economics lane read confirmation results.
The original `offerings.json` and `policy_freeze.json` are preserved unchanged.

The `verified_design.deliverable` prose includes “Executable local response model”. This over-specifies an
intermediate artifact for the direct-search comparator. The same record's acceptance field, technical protocol,
technical implementation and frozen economic policy consistently require a feasible plan with a directly measured
response of at least 2.0, cost at most 1.2 and valid input bounds. They do not require a fitted model for this offering.

The intended complete deliverable is the selected plan, its measured target-response result, exact input and cost
checks, reproducible search/invocation code, query trace and provenance. A fitted response model accompanies
methods that use one; it is an internal method choice. The separately priced `response_model` offering does require
an executable fitted model and 384 independently labeled acceptance points, charged to cost A.

This is a prose-contract erratum. No acceptance threshold, comparator, seed, query budget, price, route, method,
economic decision or recorded outcome is changed. A reader who requires a response model in every design delivery
should use the separately costed response-model service; the direct-search result does not satisfy that stronger
combined contract. It is not legitimate to count a direct-search plan as delivery of an unproduced fitted model.
