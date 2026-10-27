# SPDX-License-Identifier: Apache-2.0
"""Explicit offline examples. Numeric examples are fictional controls, not calibration."""
from copy import deepcopy
from graph_lifecycle import BeyondBetaGraph, OfflinePrincipal, authority_fixture, costs, digest, COST_CATEGORIES


def make_fixture_environment(functions=None, private_ablation=False):
    roles = {"creator": ["creator", "compose", "execution", "retrieve"], "writer": ["writer"], "assessor": ["assessor"],
             "validator-a": ["validator"], "validator-b": ["validator"], "admitter": ["admission"],
             "executor": ["execution", "retrieve"], "reader": []}
    people = {name: OfflinePrincipal(name + ".agent.agi.eth") for name in roles}
    fixtures = [authority_fixture(people[name], allowed) for name, allowed in roles.items()]
    policy = dict(id="FICTIONAL-CONTROL-POLICY", version=1, functions=functions or ["solver", "verifier", "composition"],
        contractHash=digest("FICTIONAL-CONTRACT", {"complete": True}), minCases=2, minValidators=2,
        minAcceptanceBps=10000, maxEvidenceAge=8, permitLife=1, maxAllocationUses=10,
        minCompositionCases=2, uncertaintyMultiplierMilli=2000, minimumNetAlphaMicros=0,
        operators={"IDENTITY": 1, "ADD": 2, "RETURN": 1}, inputArity=2,
        publicParameters={"public-zero": 0, "public-one": 1}, publicSourceIds=["public-fixture-v1"],
        privateAblation=private_ablation)
    beta = dict(id="FICTIONAL-COMPETENT-BETA", version=1, competent=True,
                competenceEvidenceHash=digest("FIXTURE-BETA-EVIDENCE", {"scope": "fictional"}))
    return BeyondBetaGraph(policy, beta, [], fixtures), people


def fixture_artifact(function="solver"):
    return dict(schema="beyond-beta-shareable-ir/v1", function=function,
                nodes=[dict(op="IDENTITY", inputs=[-1], parameterKeys=[])], publicSourceIds=["public-fixture-v1"])


def matched_evidence(graph, key, candidate_costs, comparator_costs, *, epoch=0, case_prefix="fresh",
                     construction_micros=0, allocation_uses=1, revalidation=False, values=None,cost_ownership=None):
    """All economics are caller supplied; construction is amortized exactly once."""
    n = len(candidate_costs)
    context = graph.comparison_context(key)
    record = graph.record(key)
    cases = [dict(id=f"{case_prefix}-{i}", valueMicros=(values[i] if values is not None else 0)) for i in range(n)]
    def arm(values, construction=0, historical=0):
        return dict(records=[dict(caseId=case["id"], accepted=True, criticalFailure=False,
                                 costs=costs(production=value)) for case,value in zip(cases,values)],
                    lifecycleCosts=costs(construction=construction), allocationUses=allocation_uses,
                    historicalConstructionMicros=historical)
    arms = {"candidate": arm(candidate_costs, construction_micros, record["historicalConstructionMicros"] if revalidation else 0)}
    for name in context["requiredArms"]:
        if name != "candidate":
            values_for_arm = comparator_costs[name] if isinstance(comparator_costs, dict) else comparator_costs
            arms[name] = arm(values_for_arm)
    dependencies = record["descriptor"]["dependencies"]
    composition = dict(dependencyHash=digest("DEPENDENCIES", dependencies), independentCaseIds=[c["id"] for c in cases]) if dependencies else None
    support=graph.support_costs(dependencies)
    if support:composition["supportConstructionMicros"]=support
    evidence=dict(schema="beyond-beta-matched-evidence/v1", candidateHash=record["candidateHash"],
                policyHash=context["policyHash"], betaHash=context["betaHash"], inventoryHash=context["inventoryHash"],
                capturedEpoch=epoch, caseSetId=case_prefix, cases=cases, arms=arms,
                phase="revalidation" if revalidation else "initial", composition=composition, dataBasis="SIMULATED_FIXTURE")
    if cost_ownership is not None:
        evidence["costOwnership"]=deepcopy(cost_ownership)
        return evidence
    return bind_cost_ownership(evidence)


def bind_cost_ownership(evidence,origin_job_costs=None,retention_entries=None,research_entries=None):
    """Bind A as provenance and derive lifecycle costs from explicit B/C entries.

    Without supplied entries this creates an explicitly fictional B commitment
    for the already-declared lifecycle map. Production adapters pass real modeled
    ledger entries; this convenience function does not create a financial charge.
    """
    e=deepcopy(evidence);research=deepcopy(research_entries or [])
    if retention_entries is None:
        fixed=deepcopy(e["arms"]["candidate"]["lifecycleCosts"])
        for row in research:
            for category in COST_CATEGORIES:fixed[category]-=row["costs"][category]
        if any(v<0 for v in fixed.values()):raise ValueError("Research allocation exceeds declared lifecycle cost")
        frame={"candidateHash":e["candidateHash"],"caseSetId":e["caseSetId"],"phase":e["phase"],"costs":fixed}
        commitment=digest("FICTIONAL-RETENTION-LEDGER-ENTRY",frame)
        retention=[dict(chargeId="fixture-retention-"+commitment,ledgerCommitment=commitment,costs=fixed,ownership="INCREMENTAL_RETENTION_B")]
    else:retention=deepcopy(retention_entries)
    fixed=costs()
    for entry in retention+research:
        for category in COST_CATEGORIES:fixed[category]+=entry["costs"][category]
    e["arms"]["candidate"]["lifecycleCosts"]=fixed
    e["costOwnership"]=dict(schema="beyond-beta-cost-ownership/v1",originJobCosts=deepcopy(origin_job_costs or []),retentionEntries=retention,researchEntries=research)
    return e


def qualify(graph, people, key, evidence, epoch=0):
    graph.register_evidence(people["writer"], key, evidence, epoch)
    assessment = graph.assess(people["assessor"], key, epoch)
    graph.validate(people["validator-a"], key, epoch)
    graph.validate(people["validator-b"], key, epoch)
    return assessment


def mission_for(graph, function="solver"):
    return dict(id="fictional-mission", function=function, policyHash=graph.policy_hash,
                permittedOperators=list(graph.policy["operators"]))
