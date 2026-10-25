# SPDX-License-Identifier: Apache-2.0
"""Closed-form operational scenarios; inputs remain separately frozen.

This program makes no provider request, deployment or financial transaction.
It requires the exact public-freeze authorization and preserves each run directory.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


RESOURCE_KEYS = (
    "employer_minutes", "provider_minutes", "traditional_worker_minutes",
    "executor_seconds", "input_tokens", "output_tokens",
)
EXPECTED_FREEZE = "54bc70fec9bb635b473193d966d36ed5bf445460a58255f025cbed4a30854d8b"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def empty_account() -> dict[str, Any]:
    return {
        "components": {}, "ownership": {},
        "resources": {key: 0.0 for key in RESOURCE_KEYS}, "total": 0.0,
    }


def combine(*weighted: tuple[dict[str, Any], float]) -> dict[str, Any]:
    out = empty_account()
    for account, weight in weighted:
        for key, value in account["components"].items():
            out["components"][key] = out["components"].get(key, 0.0) + weight * value
            owner = account["ownership"][key]
            if key in out["ownership"] and out["ownership"][key] != owner:
                raise ValueError("Conflicting component ownership: " + key)
            out["ownership"][key] = owner
        for key in RESOURCE_KEYS:
            out["resources"][key] += weight * account["resources"][key]
    out["total"] = math.fsum(out["components"].values())
    out["account_totals"] = {}
    for key, value in out["components"].items():
        owner = out["ownership"][key]
        out["account_totals"][owner] = out["account_totals"].get(owner, 0.0) + value
    out["service_improvement_totals"] = {
        "identified_improvement": math.fsum(value for key, value in out["account_totals"].items()
                                           if key.startswith("improvement_")),
        "joint_service_improvement_unallocated": out["account_totals"].get("joint_service_improvement_unallocated", 0.0),
        "service_and_employer": math.fsum(value for key, value in out["account_totals"].items()
                                          if not key.startswith("improvement_")
                                          and key != "joint_service_improvement_unallocated"),
    }
    return out


def quantile(atoms: list[dict[str, float]], probability: float) -> float | None:
    mass = math.fsum(row["probability"] for row in atoms)
    if mass <= 0:
        return None
    running = 0.0
    for row in sorted(atoms, key=lambda r: r["seconds"]):
        running += row["probability"]
        if running + 1e-14 >= probability * mass:
            return row["seconds"] / 60
    return max(row["seconds"] for row in atoms) / 60


def latency_summary(atoms: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [row for row in atoms if row["accepted"]]
    failed = [row for row in atoms if not row["accepted"]]
    def mean(rows: list[dict[str, Any]]) -> float | None:
        mass = math.fsum(row["probability"] for row in rows)
        return (math.fsum(row["probability"] * row["seconds"] for row in rows) / mass / 60
                if mass else None)
    return {
        "atoms": atoms, "accepted_conditional_minutes": mean(accepted),
        "all_request_minutes": mean(atoms), "failed_conditional_minutes": mean(failed),
        "accepted_median_minutes": quantile(accepted, 0.5),
        "accepted_p95_minutes": quantile(accepted, 0.95),
        "worst_declared_path_minutes": max(row["seconds"] for row in atoms) / 60,
        "basis": "ASSUMED_SERIAL_OPERATIONAL_LATENCY; not the observed native component",
    }


class Model:
    def __init__(self, inputs: dict[str, Any], labor: dict[str, Any], anchor: dict[str, Any]):
        self.d = inputs
        self.rates = {row["id"]: row for row in labor["rates"]}
        self.anchor = anchor

    def currency_factor(self, currency: str) -> float:
        fx = self.d["fx"]
        return {"USD": 1.0, "EUR": 1 / fx["USD_per_EUR"],
                "CAD": fx["CAD_per_EUR"] / fx["USD_per_EUR"]}[currency]

    def rates_for(self, price_basis: dict[str, Any]) -> tuple[float, float, float]:
        factor = self.currency_factor(price_basis["currency"])
        customer = self.rates[price_basis["labor_rate_id"]]["rate_per_hour"]
        customer *= price_basis["employer_load_multiplier"]
        provider_config = self.d["provider_labor"]
        provider = self.rates[provider_config["labor_rate_id"]]["rate_per_hour"]
        provider *= provider_config["employer_load_multiplier"] * factor
        return customer, provider, factor

    def charge(
        self, scenario: dict[str, Any], price_basis: dict[str, Any], *,
        employer: dict[str, float] | None = None,
        provider: dict[str, float] | None = None,
        worker: dict[str, float] | None = None,
        tokens: dict[str, dict[str, float]] | None = None,
        search: float = 0, occupied: float = 0, requests: float = 0,
        storage_gib_hours: float = 0, cash_usd: dict[str, float] | None = None,
        prefix: str = "delivery", account: str = "delivery_service",
        labor_ownership: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        out = empty_account()
        customer_rate, provider_rate, factor = self.rates_for(price_basis)
        nonlabor = 0.0
        def add(key: str, amount: float, owner: str, is_nonlabor: bool = False) -> None:
            nonlocal nonlabor
            name = prefix + "." + key
            out["components"][name] = amount
            out["ownership"][name] = owner
            if is_nonlabor:
                nonlabor += amount
        for role, values, rate, resource in (
            ("employer", employer or {}, customer_rate, "employer_minutes"),
            ("provider", provider or {}, provider_rate, "provider_minutes"),
            ("traditional_worker", worker or {}, customer_rate, "traditional_worker_minutes"),
        ):
            for name, minutes in values.items():
                owner = (labor_ownership or {}).get(name, account)
                add(role + "." + name, minutes * rate / 60, owner)
                out["resources"][resource] += minutes
        for route, values in (tokens or {}).items():
            tariff = self.d["model_prices"][route]
            for side in ("input", "output"):
                quantity = values.get(side + "_tokens", 0.0)
                add("model." + route + "." + side,
                    quantity * tariff[side + "_usd_per_million"] / 1_000_000 * factor,
                    account, True)
                out["resources"][side + "_tokens"] += quantity
        add("successful_search", search * self.d["web_search_usd_per_1000"] / 1000 * factor,
            account, True)
        cloud = self.d["cloud"]
        if requests == 0:
            if occupied != 0:
                raise ValueError("Occupied executor time requires a declared request count")
            billed_seconds = 0.0
        else:
            quantum = cloud["billing_rounding_seconds"]
            billed_seconds = math.ceil((occupied / requests) / quantum - 1e-12) * quantum * requests
        add("executor_cpu", billed_seconds * cloud["vcpus"] * cloud["active_vcpu_second_usd"] * factor,
            account, True)
        add("executor_memory", billed_seconds * cloud["memory_gib"] * cloud["active_gib_second_usd"] * factor,
            account, True)
        add("executor_requests", requests * cloud["requests_per_million_usd"] / 1_000_000 * factor,
            account, True)
        add("storage_at_rest", storage_gib_hours * self.d["storage"]["gib_hour_usd"] * factor,
            account, True)
        for name, dollars in (cash_usd or {}).items():
            add("cash_allowance." + name, dollars * factor, account, True)
        add("nonlabor_tax_allowance", nonlabor * scenario["nonrecoverable_nontechnical_tax_allowance_fraction"],
            account, True)
        out["resources"]["executor_seconds"] = occupied
        out["meters"] = {"raw_occupied_seconds": occupied, "billed_allocated_seconds": billed_seconds,
                         "executor_requests": requests, "successful_search_calls": search,
                         "storage_gib_hours": storage_gib_hours}
        return combine((out, 1.0)) | {"meters": out["meters"]}

    def event(self, name: str, scenario: dict[str, Any], basis: dict[str, Any],
              options: dict[str, Any]) -> dict[str, Any]:
        event = self.d["events"][name]
        multipliers = scenario["delivery_multipliers"]
        employer = {key: value * multipliers["human_minutes"] for key, value in event["employer_minutes"].items()}
        review_keys = {"independent_review", "independent_rereview", "challenge_adjudication",
                       "rejection_review", "refusal_review"}
        review_factor = options.get("review_factor", 1.0)
        employer = {key: value * (review_factor if key in review_keys else 1.0)
                    for key, value in employer.items()}
        tokens = {
            route: {side: values[side] * multipliers["model_tokens"] * options.get("token_factor", 1.0)
                    for side in ("input_tokens", "output_tokens")}
            for route, values in event["model_usage"].items()
        }
        calls = {route: values["calls"] for route, values in event["model_usage"].items()}
        search = event["successful_web_search_calls"]
        if options.get("native_delivery_only"):
            tokens = {route: {"input_tokens": 0.0, "output_tokens": 0.0} for route in tokens}
            calls = {route: 0 for route in calls}
            search = 0
        occupied = event["executor_occupied_seconds"] * multipliers["executor_occupancy"]
        native_seconds = event["native_invocations"] * self.anchor["native_delivery_wall_seconds"]
        if occupied + 1e-12 < native_seconds:
            raise ValueError("Native included subcomponent exceeds declared occupancy")
        provider = event["provider_operator_minutes"] * multipliers["human_minutes"]
        result = self.charge(
            scenario, basis, employer=employer, provider={"operator": provider}, tokens=tokens,
            search=search, occupied=occupied, requests=event["executor_requests"], prefix="delivery." + name,
        )
        elapsed = occupied + 60 * (math.fsum(employer.values()) + provider)
        elapsed += event["external_wait_seconds"] * multipliers["external_wait"]
        return {"event": name, "account": result, "elapsed_seconds": elapsed,
                "production_attempts": event["production_attempts"], "model_calls": calls,
                "native_invocations": event["native_invocations"], "included_native_seconds": native_seconds}

    def agent_variable(self, scenario: dict[str, Any], basis: dict[str, Any],
                       options: dict[str, Any]) -> dict[str, Any]:
        storage = self.d["storage"]
        retention = scenario["artifact_gib_per_request"] * storage["artifact_copies"]
        retention *= storage["artifact_retention_days"] * storage["hours_per_day"]
        retained = self.charge(
            scenario, basis, storage_gib_hours=retention,
            cash_usd={"operations_and_egress": scenario["operations_egress_allowance_usd_per_request"]},
            prefix="delivery.request_retention",
        )
        branches, atoms = [], []
        for name, branch in self.d["branches"].items():
            events = [self.event(event, scenario, basis, options) for event in branch["events"]]
            attempts = sum(event["production_attempts"] for event in events)
            if attempts > self.d["maximum_production_attempts_per_request"]:
                raise ValueError("Attempt cap exceeded")
            account = combine((retained, 1.0), *((event["account"], 1.0) for event in events))
            elapsed = math.fsum(event["elapsed_seconds"] for event in events)
            probability = scenario["branch_weights"][name]
            branches.append({"branch": name, "probability": probability,
                             "accepted": branch["accepted"], "attempts": attempts,
                             "account": account, "elapsed_seconds": elapsed, "events": events})
            atoms.append({"path": name, "probability": probability,
                          "accepted": branch["accepted"], "seconds": elapsed})
        if abs(math.fsum(row["probability"] for row in branches) - 1.0) > 1e-12:
            raise ValueError("Terminal path probabilities do not sum to one")
        expected = combine(*((row["account"], row["probability"]) for row in branches))
        return {
            "branches": branches, "account": expected,
            "acceptance_probability": math.fsum(row["probability"] for row in branches if row["accepted"]),
            "expected_attempts": math.fsum(row["probability"] * row["attempts"] for row in branches),
            "latency": latency_summary(atoms),
        }

    def agent_fixed(self, scenario: dict[str, Any], basis: dict[str, Any]) -> dict[str, Any]:
        initial_groups = {
            "requirements_setup": "service_enablement", "deployment_configuration": "service_enablement",
            "approved_executor_integration": "service_enablement",
            "successful_capability_construction": "improvement_successful_construction",
            "unsuccessful_capability_construction": "improvement_unsuccessful_construction",
            "independent_qualification": "improvement_qualification",
            "onboarding_and_governance": "employer_enablement",
        }
        monthly_groups = {
            "support": "service_support", "runtime_dependency_maintenance": "runtime_maintenance",
            "capability_revalidation": "improvement_capability_upkeep",
            "recovery_security_upkeep": "runtime_maintenance",
            "successful_refresh": "improvement_successful_refresh",
            "unsuccessful_improvement": "improvement_unsuccessful_search",
            "governance": "employer_governance",
        }
        initial = self.charge(
            scenario, basis,
            employer={key: value * 60 for key, value in scenario["initial_employer_hours"].items()},
            provider={key: value * 60 for key, value in scenario["initial_provider_hours"].items()},
            tokens=scenario["initial_model_tokens"], search=scenario["initial_search_calls"],
            occupied=scenario["initial_executor_seconds"], requests=scenario["initial_executor_requests"],
            prefix="initial", account="joint_service_improvement_unallocated", labor_ownership=initial_groups,
        )
        hours = self.d["storage"]["calendar_days_per_operating_month"] * self.d["storage"]["hours_per_day"]
        monthly = self.charge(
            scenario, basis,
            employer={key: value * 60 for key, value in scenario["monthly_employer_hours"].items()},
            provider={key: value * 60 for key, value in scenario["monthly_provider_hours"].items()},
            tokens=scenario["monthly_model_tokens"], search=scenario["monthly_search_calls"],
            occupied=scenario["monthly_executor_seconds"], requests=scenario["monthly_executor_requests"],
            storage_gib_hours=scenario["shared_storage_gib"] * hours,
            cash_usd=scenario["monthly_cash_allowances_usd"], prefix="monthly",
            account="joint_service_improvement_unallocated", labor_ownership=monthly_groups,
        )
        return {"initial": initial, "monthly": monthly}

    def human_fixed(self, scenario: dict[str, Any], basis: dict[str, Any]) -> dict[str, Any]:
        return {
            "initial": self.charge(
                scenario, basis,
                employer={"onboarding": scenario["human_initial_employer_onboarding_hours"] * 60},
                worker={"template_setup": scenario["human_initial_worker_setup_hours"] * 60},
                prefix="human_initial", account="traditional_workflow_enablement",
            ),
            "monthly": self.charge(
                scenario, basis,
                employer={"governance": scenario["human_monthly_employer_governance_hours"] * 60},
                worker={"template_support": scenario["human_monthly_worker_template_support_hours"] * 60},
                cash_usd={"ordinary_software_IT": scenario["human_monthly_software_IT_allowance_usd"]},
                prefix="human_monthly", account="traditional_workflow_upkeep",
            ),
        }

    def human_variable(self, scenario: dict[str, Any], basis: dict[str, Any], productive: float,
                       options: dict[str, Any]) -> dict[str, Any]:
        h = self.d["traditional"]
        multiplier = scenario["delivery_multipliers"]["human_minutes"]
        review = options.get("review_factor", 1.0)
        probability = scenario["human_correction_probability"]
        common = {key: value * multiplier * (review if key == "independent_review" else 1.0)
                  for key, value in h["common_employer_minutes"].items()}
        queue = h["queue_wait_seconds"] * scenario["delivery_multipliers"]["external_wait"]
        rows, atoms = [], []
        for corrected, p in ((False, 1 - probability), (True, probability)):
            employer = dict(common)
            if corrected:
                employer["rereview"] = h["rereview_employer_minutes_if_correction"] * multiplier * review
            correction = scenario["human_correction_minutes"] if corrected else 0.0
            account = self.charge(
                scenario, basis, employer=employer,
                worker={"productive_work": productive, "correction": correction},
                prefix="human_delivery", account="traditional_delivery",
            )
            elapsed = 60 * (math.fsum(employer.values()) + productive + correction) + queue
            rows.append((account, p))
            atoms.append({"path": "human_corrected" if corrected else "human_direct",
                          "probability": p, "accepted": True, "seconds": elapsed})
        return {"account": combine(*rows), "latency": latency_summary(atoms),
                "productive_minutes": productive, "acceptance_probability": 1.0}

    def cohort(self, variable: dict[str, Any], fixed: dict[str, Any], requests: int | float,
               acceptance: float, months: int) -> dict[str, Any]:
        fixed_account = combine((fixed["initial"], 1.0), (fixed["monthly"], months))
        total = combine((fixed_account, 1.0), (variable, requests))
        accepted = requests * acceptance
        human_keys = ("employer_minutes", "provider_minutes", "traditional_worker_minutes")
        return {
            "requested": requests, "expected_accepted": accepted,
            "expected_unresolved": requests - accepted, "acceptance_probability": acceptance,
            "operating_months_reserved": months, "fixed_account": fixed_account,
            "total_account": total, "total_cost": total["total"],
            "cost_per_requested": total["total"] / requests if requests else None,
            "cost_per_expected_accepted": total["total"] / accepted if accepted else None,
            "accepted_denominator_status": "DEFINED" if accepted else "NO_EXPECTED_ACCEPTED_OUTPUTS",
            "human_minutes_per_requested": {
                key: total["resources"][key] / requests if requests else None for key in human_keys},
            "human_minutes_per_expected_accepted": {
                key: total["resources"][key] / accepted if accepted else None for key in human_keys},
            "all_human_minutes_per_expected_accepted":
                math.fsum(total["resources"][key] for key in human_keys) / accepted if accepted else None,
            "cost_shares": {key: value / total["total"] if total["total"] else None
                            for key, value in total["account_totals"].items()},
        }

    def capacity(self, scenario: dict[str, Any], basis: dict[str, Any], variable: dict[str, Any],
                 fixed: dict[str, Any], acceptance: float, setup_days: float) -> dict[str, Any]:
        resource = self.d["resources"]
        horizon = self.d["horizons"]
        months = horizon["annual_operating_months"]
        days = horizon["working_days"]
        utilization = scenario["resource_utilization"]
        days_after = max(0.0, days - setup_days)
        factor = self.currency_factor(basis["currency"])
        fixed_annual = combine((fixed["initial"], 1), (fixed["monthly"], months))
        raw_money = resource["annual_full_economic_budget_usd"] * factor - fixed_annual["total"]
        limits: dict[str, Any] = {}
        limits["economic_budget"] = {
            "annual_residual": raw_money, "effective_residual": max(0.0, raw_money),
            "per_request": variable["total"],
            "request_limit": max(0.0, raw_money) / variable["total"] if variable["total"] else None,
        }
        per_day = {
            "employer_minutes": resource["employer_available_minutes_per_workday"],
            "provider_minutes": resource["provider_available_minutes_per_workday"],
            "traditional_worker_minutes": resource["traditional_worker_available_minutes_per_workday"],
            "executor_seconds": horizon["working_hours_per_day"] * 3600 * self.d["cloud"]["parallel_executor_instances"],
        }
        for key, daily in per_day.items():
            recurring = fixed["monthly"]["resources"][key] * months
            annual = days * daily * utilization - fixed["initial"]["resources"][key] - recurring
            calendar = days_after * daily * utilization - recurring
            effective = max(0.0, min(annual, calendar))
            use = variable["resources"][key]
            limits[key] = {"annual_residual": annual, "postdeployment_residual": calendar,
                           "effective_residual": effective, "per_request": use,
                           "request_limit": effective / use if use else None}
        for key in ("input_tokens", "output_tokens"):
            budget = resource["annual_" + key.replace("_tokens", "_token_budget")]
            residual = budget * utilization - fixed_annual["resources"][key]
            use = variable["resources"][key]
            limits[key] = {"annual_residual": residual, "effective_residual": max(0.0, residual),
                           "per_request": use,
                           "request_limit": max(0.0, residual) / use if use else None}
        limits["demand"] = {"request_limit": float(scenario["requested_demand"])}
        values = {key: row["request_limit"] for key, row in limits.items()
                  if row["request_limit"] is not None}
        # Fixed obligations alone can be infeasible even when variable use is zero.
        fixed_shortfalls = [key for key, row in limits.items()
                            if row.get("annual_residual", 0.0) < -1e-9
                            or row.get("postdeployment_residual", 0.0) < -1e-9]
        smallest = min(values.values())
        admitted = 0 if fixed_shortfalls else max(0, math.floor(smallest + 1e-12))
        binding = [key for key, value in values.items()
                   if math.isclose(value, smallest, rel_tol=1e-10, abs_tol=1e-10)]
        setup_diagnostics = {}
        for key, daily in per_day.items():
            initial_use = fixed["initial"]["resources"][key]
            setup_available = setup_days * daily * utilization
            setup_diagnostics[key] = {
                "initial_resource_use": initial_use,
                "uniform_daily_available": daily * utilization,
                "declared_setup_window_available": setup_available,
                "minimum_workdays_if_uniform_daily_limit": initial_use / (daily * utilization),
                "fits_declared_setup_window_if_uniform_daily_limit": initial_use <= setup_available + 1e-9,
            }
        return {
            "requested_capacity": admitted, "expected_accepted_capacity": admitted * acceptance,
            "expected_unresolved_capacity": admitted * (1 - acceptance),
            "binding_constraints": binding, "fixed_resource_shortfalls": fixed_shortfalls,
            "limits": limits, "setup_elapsed_workdays": setup_days,
            "declared_demand_feasible": admitted >= scenario["requested_demand"],
            "feasible_admitted_cohort": self.cohort(variable, fixed, admitted, acceptance, months),
            "scope": "AGGREGATE_RESOURCE_FEASIBLE_UPPER_BOUND; not proof of daily schedulability or deployed service throughput",
            "setup_scheduling_diagnostic": setup_diagnostics,
            "setup_window_fits_uniform_daily_limits": all(row["fits_declared_setup_window_if_uniform_daily_limit"]
                                                          for row in setup_diagnostics.values()),
            "setup_scheduling_caveat": "Post-result consistency diagnostic only. Frozen setup elapsed days and primary capacity equations remain unchanged; assumed setup delay is unvalidated. An annual-average pool could be frontloaded, but additional setup staffing is not demonstrated.",
        }

    def hybrid(self, scenario: dict[str, Any], basis: dict[str, Any], agent: dict[str, Any],
               human: dict[str, Any], fixed_agent: dict[str, Any], fixed_human: dict[str, Any]) -> dict[str, Any]:
        failed = 1 - agent["acceptance_probability"]
        handoff = self.charge(scenario, basis,
                              employer={"fallback_handoff": scenario["hybrid_handoff_employer_minutes"]},
                              prefix="hybrid", account="hybrid_handoff")
        variable = combine((agent["account"], 1), (handoff, failed), (human["account"], failed))
        fixed = {period: combine((fixed_agent[period], 1), (fixed_human[period], 1))
                 for period in ("initial", "monthly")}
        atoms = []
        for branch in agent["branches"]:
            if branch["accepted"]:
                atoms.append({"path": branch["branch"], "probability": branch["probability"],
                              "accepted": True, "seconds": branch["elapsed_seconds"]})
            else:
                for h_atom in human["latency"]["atoms"]:
                    atoms.append({
                        "path": branch["branch"] + "+" + h_atom["path"],
                        "probability": branch["probability"] * h_atom["probability"],
                        "accepted": True,
                        "seconds": branch["elapsed_seconds"] + h_atom["seconds"]
                                   + 60 * scenario["hybrid_handoff_employer_minutes"],
                    })
        return {"account": variable, "fixed": fixed, "latency": latency_summary(atoms),
                "fallback_probability": failed, "acceptance_probability_assumed": 1.0}

    def evaluate(self, scenario_id: str, basis: dict[str, Any], options: dict[str, Any] | None = None,
                 human_times: list[float] | None = None) -> dict[str, Any]:
        options = options or {}
        scenario = copy.deepcopy(self.d["scenarios"][scenario_id])
        if "requested_volume" in options:
            scenario["requested_demand"] = options["requested_volume"]
        scenario["initial_provider_hours"]["unsuccessful_capability_construction"] *= options.get("failed_construction_factor", 1)
        upkeep = options.get("upkeep_factor", 1)
        for field in ("monthly_provider_hours", "monthly_employer_hours", "monthly_cash_allowances_usd"):
            scenario[field] = {key: value * upkeep for key, value in scenario[field].items()}
        for route in scenario["monthly_model_tokens"]:
            scenario["monthly_model_tokens"][route] = {
                key: value * upkeep for key, value in scenario["monthly_model_tokens"][route].items()}
        for field in ("monthly_search_calls", "monthly_executor_seconds", "monthly_executor_requests"):
            scenario[field] *= upkeep
        agent = self.agent_variable(scenario, basis, options)
        fixed_agent = self.agent_fixed(scenario, basis)
        fixed_human = self.human_fixed(scenario, basis)
        n = scenario["requested_demand"]
        months = self.d["horizons"]["annual_operating_months"]
        q = agent["acceptance_probability"]
        annual = self.cohort(agent["account"], fixed_agent, n, q, months)
        first = self.cohort(agent["account"], fixed_agent, 1, q, self.d["horizons"]["first_commission_operating_months"])
        setup_minutes = scenario["setup_elapsed_workdays"] * self.d["horizons"]["working_hours_per_day"] * 60
        first["accepted_conditional_turnaround_minutes_including_setup"] = setup_minutes + agent["latency"]["accepted_conditional_minutes"]
        first["setup_delay_minutes"] = setup_minutes
        capacity = self.capacity(scenario, basis, agent["account"], fixed_agent, q, scenario["setup_elapsed_workdays"])
        annual["feasible"] = capacity["declared_demand_feasible"]
        zero_human = self.human_variable(scenario, basis, 0, options)
        human_intercept = self.cohort(zero_human["account"], fixed_human, n, 1, months)
        rate = self.rates_for(basis)[0]
        productive_break_even = (annual["cost_per_expected_accepted"] - human_intercept["cost_per_expected_accepted"]) * 60 / rate
        zero_hybrid = self.hybrid(scenario, basis, agent, zero_human, fixed_agent, fixed_human)
        hybrid_intercept = self.cohort(zero_hybrid["account"], zero_hybrid["fixed"], n, 1, months)
        slope_difference = q * rate / 60
        hybrid_break_even = ((hybrid_intercept["cost_per_expected_accepted"] - human_intercept["cost_per_expected_accepted"])
                             / slope_difference if slope_difference > 0 else None)
        comparisons = []
        for productive in human_times or self.d["traditional"]["productive_minutes"]:
            human = self.human_variable(scenario, basis, productive, options)
            h_annual = self.cohort(human["account"], fixed_human, n, 1, months)
            h_first = self.cohort(human["account"], fixed_human, 1, 1, self.d["horizons"]["first_commission_operating_months"])
            h_setup = scenario["human_setup_elapsed_workdays"] * self.d["horizons"]["working_hours_per_day"] * 60
            h_first["accepted_conditional_turnaround_minutes_including_setup"] = h_setup + human["latency"]["accepted_conditional_minutes"]
            h_first["setup_delay_minutes"] = h_setup
            h_capacity = self.capacity(scenario, basis, human["account"], fixed_human, 1, scenario["human_setup_elapsed_workdays"])
            h_annual["feasible"] = h_capacity["declared_demand_feasible"]
            hybrid = self.hybrid(scenario, basis, agent, human, fixed_agent, fixed_human)
            hybrid_annual = self.cohort(hybrid["account"], hybrid["fixed"], n, 1, months)
            hybrid_first = self.cohort(hybrid["account"], hybrid["fixed"], 1, 1, self.d["horizons"]["first_commission_operating_months"])
            hybrid_first["setup_delay_minutes"] = setup_minutes + h_setup
            hybrid_first["accepted_conditional_turnaround_minutes_including_setup"] = setup_minutes + h_setup + hybrid["latency"]["accepted_conditional_minutes"]
            hybrid_capacity = self.capacity(scenario, basis, hybrid["account"], hybrid["fixed"], 1,
                                             scenario["setup_elapsed_workdays"] + scenario["human_setup_elapsed_workdays"])
            hybrid_annual["feasible"] = hybrid_capacity["declared_demand_feasible"]
            comparisons.append({
                "productive_minutes": productive,
                "traditional": {"variable": human, "fixed": fixed_human, "annual_at_demand": h_annual,
                                "first_commission": h_first, "capacity": h_capacity},
                "hybrid": {"variable": hybrid, "annual_at_demand": hybrid_annual,
                           "first_commission": hybrid_first, "capacity": hybrid_capacity,
                           "break_even_productive_minutes": hybrid_break_even},
                "modeled_human_to_agent_unit_cost_ratio": h_annual["cost_per_expected_accepted"] / annual["cost_per_expected_accepted"],
                "modeled_human_to_hybrid_unit_cost_ratio": h_annual["cost_per_expected_accepted"] / hybrid_annual["cost_per_expected_accepted"],
                "modeled_human_minus_agent_unit_cost": h_annual["cost_per_expected_accepted"] - annual["cost_per_expected_accepted"],
                "modeled_human_minus_hybrid_unit_cost": h_annual["cost_per_expected_accepted"] - hybrid_annual["cost_per_expected_accepted"],
                "same_demand_completion_caveat": "Agent-only leaves unresolved requests; hybrid pays for complete assumed human fallback.",
            })
        result = {
            "scenario": scenario_id, "price_basis": basis["id"], "geography": basis["geography"],
            "currency": basis["currency"], "evidence_class": "MODELED_OPERATIONAL_ECONOMICS",
            "price_basis_metadata": basis, "labor_prices": {"employer_worker_per_hour": rate,
                "provider_per_hour_in_reporting_currency": self.rates_for(basis)[1],
                "USD_to_reporting_currency": self.rates_for(basis)[2]},
            "options": options, "scenario_inputs": scenario,
            "agent_variable": agent, "fixed_agent": fixed_agent,
            "annual_at_demand": annual, "first_commission": first, "capacity": capacity,
            "human_break_even_productive_minutes": productive_break_even,
            "human_break_even_all_in_minutes": human_intercept["all_human_minutes_per_expected_accepted"] + productive_break_even,
            "hybrid_break_even_productive_minutes": hybrid_break_even,
            "break_even_slope_status": "POSITIVE_DIFFERENCE" if slope_difference > 0 else "NO_UNIQUE_POSITIVE_SLOPE_BREAK_EVEN",
            "traditional_comparisons": comparisons,
            "actual_end_to_end_field_cost": None, "actual_historical_authoring_cost": None,
            "downstream_liability_expected_loss": None,
        }
        # Stable flat aliases meet the frozen output interface; detailed nested
        # ledgers remain the canonical inspectable decomposition.
        result.update({
            "expected_acceptance_probability": q,
            "expected_attempts": agent["expected_attempts"],
            "branch_costs": [{"branch": branch["branch"], "probability": branch["probability"],
                              "accepted": branch["accepted"], "attempts": branch["attempts"],
                              "cost": branch["account"]["total"], "elapsed_seconds": branch["elapsed_seconds"]}
                             for branch in agent["branches"]],
            "variable_cost_by_component": agent["account"]["components"],
            "first_commission_total_cost": first["total_cost"],
            "first_commission_cost_per_expected_accepted": first["cost_per_expected_accepted"],
            "annual_fixed_cost_by_component": annual["fixed_account"]["components"],
            "declared_demand_cost_per_expected_accepted": annual["cost_per_expected_accepted"],
            "declared_demand_feasible": capacity["declared_demand_feasible"],
            "employer_minutes_per_requested": agent["account"]["resources"]["employer_minutes"],
            "employer_minutes_per_expected_accepted": annual["human_minutes_per_expected_accepted"]["employer_minutes"],
            "provider_human_minutes_per_expected_accepted": annual["human_minutes_per_expected_accepted"]["provider_minutes"],
            "all_human_minutes_per_expected_accepted": annual["all_human_minutes_per_expected_accepted"],
            "accepted_conditional_turnaround_minutes": agent["latency"]["accepted_conditional_minutes"],
            "all_request_turnaround_minutes": agent["latency"]["all_request_minutes"],
            "failed_conditional_turnaround_minutes": agent["latency"]["failed_conditional_minutes"],
            "accepted_turnaround_median_minutes": agent["latency"]["accepted_median_minutes"],
            "accepted_turnaround_p95_minutes": agent["latency"]["accepted_p95_minutes"],
            "worst_declared_path_minutes": agent["latency"]["worst_declared_path_minutes"],
            "capacity_requested": capacity["requested_capacity"],
            "capacity_expected_accepted": capacity["expected_accepted_capacity"],
            "capacity_binding_constraints": capacity["binding_constraints"],
            "capacity_residuals": capacity["limits"],
            "feasible_cost_per_expected_accepted": capacity["feasible_admitted_cohort"]["cost_per_expected_accepted"],
            "service_improvement_totals": annual["total_account"]["service_improvement_totals"],
        })
        return result


def verify_authorization(root: Path) -> dict[str, Any]:
    freeze_path = root / "FREEZE.json"
    if digest(freeze_path) != EXPECTED_FREEZE:
        raise ValueError("Unexpected public freeze identity")
    authorization = json.loads((root / "AUTHORIZATION.json").read_text())
    if (authorization["status"] != "GO_FOR_LOCAL_SCENARIO_CALCULATION_AND_INDEPENDENT_AUDIT"
            or authorization["freeze_sha256"] != EXPECTED_FREEZE
            or authorization["public_readback_exact"] is not True):
        raise ValueError("No matching public freeze and local calculation authorization")
    freeze = json.loads(freeze_path.read_text())
    for row in freeze["files"]:
        path = root / row["path"]
        if not path.is_file() or path.is_symlink() or path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise ValueError("Frozen input drift: " + row["path"])
    return authorization


def summary_row(row: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    a = row["annual_at_demand"]
    h = comparison["traditional"]["annual_at_demand"]
    y = comparison["hybrid"]["annual_at_demand"]
    return {
        "scenario": row["scenario"], "price_basis": row["price_basis"], "currency": row["currency"],
        "productive_human_minutes_assumed": comparison["productive_minutes"],
        "requested_demand": a["requested"], "agent_acceptance_probability_assumed": a["acceptance_probability"],
        "agent_expected_accepted": a["expected_accepted"], "agent_expected_unresolved": a["expected_unresolved"],
        "agent_cost_per_expected_accepted": a["cost_per_expected_accepted"],
        "traditional_cost_per_completed": h["cost_per_expected_accepted"],
        "hybrid_cost_per_completed": y["cost_per_expected_accepted"],
        "agent_first_commission_total_cost": row["first_commission"]["total_cost"],
        "agent_first_commission_per_expected_accepted": row["first_commission"]["cost_per_expected_accepted"],
        "traditional_first_commission_total_cost": comparison["traditional"]["first_commission"]["total_cost"],
        "hybrid_first_commission_total_cost": comparison["hybrid"]["first_commission"]["total_cost"],
        "traditional_employer_minutes_per_completed": h["human_minutes_per_expected_accepted"]["employer_minutes"],
        "hybrid_employer_minutes_per_completed": y["human_minutes_per_expected_accepted"]["employer_minutes"],
        "agent_employer_minutes_per_expected_accepted": a["human_minutes_per_expected_accepted"]["employer_minutes"],
        "agent_provider_minutes_per_expected_accepted": a["human_minutes_per_expected_accepted"]["provider_minutes"],
        "agent_all_human_minutes_per_expected_accepted": a["all_human_minutes_per_expected_accepted"],
        "traditional_all_human_minutes_per_completed": h["all_human_minutes_per_expected_accepted"],
        "hybrid_all_human_minutes_per_completed": y["all_human_minutes_per_expected_accepted"],
        "agent_accepted_turnaround_minutes": row["agent_variable"]["latency"]["accepted_conditional_minutes"],
        "agent_first_accepted_turnaround_minutes_including_setup": row["first_commission"]["accepted_conditional_turnaround_minutes_including_setup"],
        "traditional_turnaround_minutes": comparison["traditional"]["variable"]["latency"]["accepted_conditional_minutes"],
        "hybrid_turnaround_minutes": comparison["hybrid"]["variable"]["latency"]["accepted_conditional_minutes"],
        "agent_break_even_productive_human_minutes": row["human_break_even_productive_minutes"],
        "hybrid_break_even_productive_human_minutes": row["hybrid_break_even_productive_minutes"],
        "agent_declared_demand_feasible": row["capacity"]["declared_demand_feasible"],
        "agent_admitted_requests": row["capacity"]["requested_capacity"],
        "agent_capacity_expected_accepted": row["capacity"]["expected_accepted_capacity"],
        "agent_feasible_cost_per_expected_accepted": row["capacity"]["feasible_admitted_cohort"]["cost_per_expected_accepted"],
        "agent_binding_constraints": ";".join(row["capacity"]["binding_constraints"]),
        "agent_fixed_shortfalls": ";".join(row["capacity"]["fixed_resource_shortfalls"]),
        "human_capacity_completed": comparison["traditional"]["capacity"]["expected_accepted_capacity"],
        "hybrid_capacity_completed": comparison["hybrid"]["capacity"]["expected_accepted_capacity"],
        "hybrid_declared_demand_feasible": comparison["hybrid"]["capacity"]["declared_demand_feasible"],
        "capacity_scope": row["capacity"]["scope"],
        "agent_setup_window_fits_uniform_daily_limits": row["capacity"]["setup_window_fits_uniform_daily_limits"],
        "traditional_setup_window_fits_uniform_daily_limits": comparison["traditional"]["capacity"]["setup_window_fits_uniform_daily_limits"],
        "agent_annual_service_and_employer_cost": a["total_account"]["service_improvement_totals"]["service_and_employer"],
        "agent_annual_identified_improvement_cost": a["total_account"]["service_improvement_totals"]["identified_improvement"],
        "agent_annual_joint_service_improvement_unallocated_cost": a["total_account"]["service_improvement_totals"]["joint_service_improvement_unallocated"],
        "human_to_agent_unit_cost_ratio_modeled": comparison["modeled_human_to_agent_unit_cost_ratio"],
        "human_to_hybrid_unit_cost_ratio_modeled": comparison["modeled_human_to_hybrid_unit_cost_ratio"],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def execute(root: Path, output: Path) -> None:
    authorization = verify_authorization(root)
    if output.exists():
        raise FileExistsError("Preserve old outcomes; choose a fresh output directory")
    output.mkdir(parents=True)
    try:
        inputs = json.loads((root / "inputs.json").read_text())
        labor = json.loads((root / "sources/labor_rates.json").read_text())
        anchor = json.loads((root / "observed/ANCHOR.json").read_text())
        model = Model(inputs, labor, anchor)
        core = [model.evaluate(scenario, basis) for scenario in inputs["scenarios"] for basis in inputs["price_bases"]]
        base = next(basis for basis in inputs["price_bases"] if basis["id"] == "US_office")
        spec = inputs["one_way_sensitivities"]
        mapping = {
            "requested_reuse_volume": "requested_volume",
            "delivery_model_token_multiplier": "token_factor",
            "employer_review_effort_multiplier": "review_factor",
            "unsuccessful_initial_construction_human_hours_multiplier": "failed_construction_factor",
            "recurring_support_and_upkeep_multiplier": "upkeep_factor",
        }
        sensitivities = []
        for driver, option in mapping.items():
            for value in spec[driver]:
                sensitivities.append({"driver": driver, "value": value,
                    "result": model.evaluate("base", base, {option: value}, [inputs["traditional"]["reference_productive_minutes"]])})
        if spec["native_delivery_no_model_or_paid_search"]["enabled"]:
            sensitivities.append({"driver": "native_delivery_no_model_or_paid_search", "value": True,
                "result": model.evaluate("base", base, {"native_delivery_only": True}, [inputs["traditional"]["reference_productive_minutes"]])})
        results = {
            "schema": "operational-economics-amendment-results/v1",
            "input_manifest_sha256": EXPECTED_FREEZE, "authorization_record": authorization,
            "model_source_sha256": digest(Path(__file__)), "observed_anchor": anchor,
            "core_scenarios": core, "one_way_sensitivities": sensitivities,
            "human_duration_comparison": [summary_row(row, comparison) for row in core
                                          for comparison in row["traditional_comparisons"]],
            "hybrid_complete_demand": [{
                "scenario": row["scenario"], "price_basis": row["price_basis"], "currency": row["currency"],
                "traditional_productive_minutes": comparison["productive_minutes"],
                "completed_demand_probability_assumed": 1.0,
                "human_fallback_probability": comparison["hybrid"]["variable"]["fallback_probability"],
                "traditional_worker_minutes": comparison["hybrid"]["annual_at_demand"]["human_minutes_per_expected_accepted"]["traditional_worker_minutes"],
                "total_human_minutes": comparison["hybrid"]["annual_at_demand"]["all_human_minutes_per_expected_accepted"],
                "hybrid_break_even_productive_minutes": row["hybrid_break_even_productive_minutes"],
                "break_even_slope_status": row["break_even_slope_status"],
                "annual_cost_per_completed_request": comparison["hybrid"]["annual_at_demand"]["cost_per_expected_accepted"],
                "aggregate_resource_capacity": comparison["hybrid"]["capacity"]["requested_capacity"],
            } for row in core for comparison in row["traditional_comparisons"]],
            "limitations": [
                "All field acceptance, workload duration, service latency, attention, setup, support and cost quantities beyond the pinned native component and sourced tariffs are explicit deployment assumptions, not observed full-system performance.",
                "The native component copies and verifies four preselected passages. It does not establish semantic research quality or the acceptance probability of a provider-orchestrated service.",
                "Capacity is an aggregate-resource upper bound. Frozen setup days are unvalidated and may be inconsistent with uniform daily setup staffing; a separate post-result diagnostic exposes this without changing primary equations.",
                "Cost per expected accepted output includes rejected/refused requests but does not fulfill them; the separately priced hybrid charges complete assumed traditional rescue.",
                "Historical authoring, host model billing, observed employer attention and downstream material-error liability remain unknown, not zero.",
                "No matched traditional human timing or new human trial was conducted; five productive-time values and human final acceptance are scenarios. Labor-market sources do not establish AI use.",
                "No observed customer price, revenue, profit, cash savings, deployment or cash reinvestment is established by these resource-cost calculations.",
            ],
            "interpretation": {
                "status": "POST_FREEZE_MODELED_SCENARIOS_PENDING_INDEPENDENT_AUDIT",
                "units": "Money in the row currency; human time in minutes; occupancy in seconds; tokens include charged reasoning.",
                "accounts": "Service and improvement labor are itemized; shared model/tool/infrastructure pools remain joint and unallocated rather than split by an invented ratio.",
                "reserve_horizon": "All twelve monthly reserves charged; setup also reduces annual available working calendar. No proration or refunds assumed.",
                "comparison": "Pure Agent leaves unresolved demand. Hybrid pays every failed Agent path plus full traditional fallback and readiness.",
                "native": "Observed exact-passage component remains separate. Assumed provider-orchestration calls were not used or required by it.",
                "liability": "Downstream material-error loss and actual field total economic cost remain unknown; no high-consequence application is supported.",
                "cash": "No observed provider revenue, cash savings, profit, paid deployment or reinvestment.",
                "capacity": "Aggregate-resource feasible upper bound only; no demonstrated daily schedule. First-commission setup delays remain assumed/unvalidated.",
            },
        }
        schema = json.loads((root / "output_schema.json").read_text())
        for key in schema["required_top_level"]:
            if key not in results:
                raise ValueError("Missing frozen top-level output field: " + key)
        for row in core:
            for key in schema["core_row_fields"]:
                if key not in row:
                    raise ValueError("Missing frozen core output field: " + key)
        write_json(output / "results.json", results)
        comparisons = [summary_row(row, comparison) for row in core for comparison in row["traditional_comparisons"]]
        write_csv(output / "results_summary.csv", comparisons)
        sensitivity_rows = []
        for item in sensitivities:
            row = summary_row(item["result"], item["result"]["traditional_comparisons"][0])
            sensitivity_rows.append({"driver": item["driver"], "value": item["value"], **row})
        write_csv(output / "sensitivities.csv", sensitivity_rows)
        ledger_rows = []
        for row in core:
            accounts = {"variable_per_requested_job": row["agent_variable"]["account"],
                        "initial_investment": row["fixed_agent"]["initial"],
                        "monthly_reserve": row["fixed_agent"]["monthly"],
                        "annual_at_declared_demand": row["annual_at_demand"]["total_account"]}
            for period, account in accounts.items():
                for component, cost in account["components"].items():
                    ledger_rows.append({"scenario": row["scenario"], "price_basis": row["price_basis"],
                                        "currency": row["currency"], "period": period, "component": component,
                                        "ownership": account["ownership"][component], "cost": cost})
        write_csv(output / "component_ledger.csv", ledger_rows)
        verify_authorization(root)
        manifest = {"schema": "operational-economics-output-manifest/v1", "freeze_sha256": EXPECTED_FREEZE,
                    "files": [{"path": path.name, "bytes": path.stat().st_size, "sha256": digest(path)}
                              for path in sorted(output.iterdir()) if path.is_file()],
                    "core_rows": len(core), "human_duration_rows": len(comparisons), "sensitivity_rows": len(sensitivities),
                    "status": "COMPLETE_PENDING_INDEPENDENT_AUDIT"}
        write_json(output / "OUTPUT_MANIFEST.json", manifest)
        print(json.dumps({"output": str(output), "core_rows": len(core), "comparison_rows": len(comparisons),
                          "sensitivity_rows": len(sensitivities), "results_sha256": digest(output / "results.json")}))
    except Exception as error:
        write_json(output / "FAILED.json", {"status": "FAILED_IMPLEMENTATION_ATTEMPT_PRESERVED",
                                           "exception_type": type(error).__name__, "message": str(error)})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    execute(args.root.resolve(), args.output.resolve())
