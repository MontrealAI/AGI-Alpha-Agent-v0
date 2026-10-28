# SPDX-License-Identifier: Apache-2.0
"""Executable mission environments and bounded retained workflow refinement.

Training modifies an identifiable workflow artifact. Protected evaluation is a
separate caller-owned partition, opened only after the output is frozen. A Gym
result grants neither skill admission nor production authority.
"""

from __future__ import annotations

import copy
import time
from collections.abc import Callable
from typing import Any, Literal, Protocol, TypeVar

from pydantic import Field, model_validator

from ..store import Conflict
from .flywheel_costs import Charge, CostLedger
from .flywheel_checkpoint import DurableCheckpoint
from .flywheel_experiments import PlacementProblem, verify_placement
from .flywheel_specialists import PlacementWorkflow, execute_workflow, placement_fingerprint
from .protocol import Digest, Identifier, StrictModel, canonical, digest
from .trust import SignedEnvelope
from .flywheel_execution import ExecutionEnvironment

KEY = "@flywheel-gym:"
TaskT = TypeVar("TaskT", bound=StrictModel, contravariant=True)


class GymTask(StrictModel):
    task_id: Identifier
    partition: Literal["training", "protected-evaluation", "transfer", "composition"]
    family: str = Field(min_length=1, max_length=100)
    problem: PlacementProblem
    objective: Literal["minimum-cost-resilient-placement"] = "minimum-cost-resilient-placement"
    logical_limit: int = Field(default=100_000, ge=1, le=100_000)

    @model_validator(mode="after")
    def bounded_checker(self) -> GymTask:
        hosts = len(self.problem.capacities)
        if (hosts * (hosts - 1) // 2) ** len(self.problem.demands) > 100_000:
            raise ValueError("task outside independent exhaustive-check budget")
        return self


class MissionEnvironment(Protocol[TaskT]):
    @property
    def identity(self) -> dict[str, Any]:
        ...

    def reset(self, task: TaskT) -> dict[str, Any]:
        ...

    def observe(self) -> dict[str, Any]:
        ...

    def step(self, action: dict[str, Any], active: Callable[[], bool]) -> dict[str, Any]:
        ...

    def outcome(self) -> dict[str, Any]:
        ...


class ToolEnvironmentTask(StrictModel):
    task_id: Identifier
    partition: Literal["training", "protected-evaluation", "transfer", "composition"]
    initial_state: dict[str, Any]
    objectives: list[str] = Field(min_length=1, max_length=32)
    constraints: list[str] = Field(min_length=1, max_length=32)
    permitted_tools: list[str] = Field(min_length=1, max_length=24)
    max_actions: int = Field(ge=1, le=512)
    max_seconds: int = Field(ge=1, le=3600)


class ToolMissionEnvironment:
    """Adapt the approved production code/tool or computer actuator to practice.

    Reset, observation and acceptance callbacks belong to the trusted environment
    operator, never a capsule or training model. They must provide their own bounded
    isolation. This adapter cannot create an isolated host sandbox or authority.
    """

    def __init__(
        self,
        executor: ExecutionEnvironment,
        *,
        contract_digest: str,
        reset: Callable[[dict[str, Any]], None],
        observe: Callable[[], dict[str, Any]],
        check: Callable[[ToolEnvironmentTask, dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.executor, self.contract_digest = executor, contract_digest
        self.reset_state, self.read_state, self.check = reset, observe, check
        self.task: ToolEnvironmentTask | None = None
        self.actions, self.started = 0, 0.0
        self.history: list[dict[str, Any]] = []
        self.terminated = False
        self.binding = digest("gym-production-environment", self.identity)

    @property
    def identity(self) -> dict[str, Any]:
        return {
            "adapter": "production-tool-environment/v1",
            "production": self.executor.identity,
            "trusted_reset_observe_check_contract": self.contract_digest,
        }

    @property
    def component(self) -> Literal["live", "executed-local", "simulated"]:
        return self.executor.component

    def reset(self, task: ToolEnvironmentTask) -> dict[str, Any]:
        self.task = ToolEnvironmentTask.model_validate_json(canonical(task))
        self._unchanged()
        self.reset_state(copy.deepcopy(self.task.initial_state))
        self.actions, self.history, self.started, self.terminated = 0, [], time.monotonic(), False
        return self.observe()

    def _unchanged(self) -> None:
        if digest("gym-production-environment", self.identity) != self.binding:
            raise Conflict("production environment changed since the Gym adapter was bound")

    def observe(self) -> dict[str, Any]:
        if self.task is None:
            raise Conflict("tool environment requires reset")
        self._unchanged()
        state = copy.deepcopy(self.read_state())
        if len(canonical(state)) > 750_000:
            raise ValueError("environment observation exceeds frame budget")
        return {
            "state": state,
            "state_digest": digest("gym-observation", state),
            "actions": self.actions,
            "terminated": self.terminated,
            "permitted_actions": self.task.permitted_tools,
        }

    def step(self, action: dict[str, Any], active: Callable[[], bool]) -> dict[str, Any]:
        if self.task is None or self.terminated:
            raise Conflict("tool environment is not executable")
        self._unchanged()
        if set(action) != {"tool", "arguments"} or action["tool"] not in self.task.permitted_tools:
            raise ValueError("tool action outside mission contract")
        if not isinstance(action["arguments"], dict) or len(canonical(action)) > 100_000:
            raise ValueError("tool action must contain bounded JSON arguments")
        if self.actions >= self.task.max_actions or time.monotonic() - self.started >= self.task.max_seconds:
            self.terminated = True
            raise TimeoutError("tool environment budget exhausted")
        if not active():
            self.terminated = True
            raise InterruptedError("tool environment stopped")
        before = self.observe()
        self.actions += 1
        event = {"before": before, "action": copy.deepcopy(action), "status": "attempted-or-uncertain"}
        self.history.append(event)
        try:
            result = self.executor.perform(
                action["tool"],
                copy.deepcopy(action["arguments"]),
                lambda: active() and self.task is not None and time.monotonic() - self.started < self.task.max_seconds,
            )
            if len(canonical(result)) > 750_000:
                raise ValueError("tool result exceeds its frame budget")
            after = self.observe()
            if not active() or time.monotonic() - self.started >= self.task.max_seconds:
                raise InterruptedError("tool outcome requires reconciliation after interruption")
            event.update(status="executed", result=copy.deepcopy(result), after=after)
            if self.actions >= self.task.max_actions:
                self.terminated = True
            return after
        except Exception:
            self.terminated = True
            raise

    def outcome(self) -> dict[str, Any]:
        if self.task is None:
            raise Conflict("tool environment requires reset")
        self._unchanged()
        self.terminated = True
        observation = self.observe()
        certain = all(event["status"] == "executed" for event in self.history)
        return {
            "observation": observation,
            "evidence": copy.deepcopy(self.history),
            "verification": (
                self.check(self.task, copy.deepcopy(observation["state"]))
                if certain
                else {"accepted": False, "reason": "uncertain attempted action requires reconciliation"}
            ),
            "authority_granted": False,
            "production_executor_reused": True,
        }

    def perform(self, name: str, arguments: dict[str, Any], active: Callable[[], bool]) -> dict[str, Any]:
        self.step({"tool": name, "arguments": arguments}, active)
        return copy.deepcopy(self.history[-1]["result"])


class PlacementEnvironment:
    """Reproducible installed code environment, also a production tool adapter."""

    component: Literal["executed-local"] = "executed-local"

    def __init__(self, workflow: PlacementWorkflow) -> None:
        self.workflow = PlacementWorkflow.model_validate_json(canonical(workflow))
        self.task: GymTask | None = None
        self.result: dict[str, Any] | None = None
        self.units = 0
        self.terminated = False

    @property
    def identity(self) -> dict[str, Any]:
        return {"adapter": "placement-environment/v1", "workflow": self.workflow.model_dump()}

    def reset(self, task: GymTask) -> dict[str, Any]:
        self.task = GymTask.model_validate_json(canonical(task))
        self.result, self.units, self.terminated = None, 0, False
        return self.observe()

    def observe(self) -> dict[str, Any]:
        if self.task is None:
            raise Conflict("environment must reset before observation")
        return {
            "initial_state_digest": digest("placement-input", self.task.problem),
            "task": self.task.model_dump(),
            "permitted_actions": [] if self.terminated else ["run-workflow"],
            "logical_units": self.units,
            "terminated": self.terminated,
            "result": copy.deepcopy(self.result),
        }

    def step(self, action: dict[str, Any], active: Callable[[], bool]) -> dict[str, Any]:
        if self.task is None or self.terminated:
            raise Conflict("environment is not in an executable state")
        if action != {"type": "run-workflow"}:
            raise ValueError("only the installed bounded workflow action is permitted")
        task = self.task
        self.terminated = True

        def charge(units: int) -> None:
            self.units += units
            if self.units > task.logical_limit:
                raise TimeoutError("environment work budget exhausted")
            if (self.units == units or self.units % 128 < units) and not active():
                raise InterruptedError("environment interrupted")

        try:
            self.result = execute_workflow(task.problem, self.workflow, charge)
        except (TimeoutError, InterruptedError) as exc:
            self.result = {"status": "failed", "error": type(exc).__name__, "logical_units": self.units}
        return self.observe()

    def outcome(self) -> dict[str, Any]:
        if self.task is None or not self.terminated or self.result is None:
            raise Conflict("no terminal outcome exists")
        return {
            "task_digest": digest("gym-task", self.task),
            "input_digest": digest("placement-input", self.task.problem),
            "workflow_digest": digest("flywheel-program", self.workflow),
            "result": copy.deepcopy(self.result),
            "verification": verify_placement(self.task.problem, self.result),
            "logical_units": self.units,
            "authority_granted": False,
        }

    def perform(self, name: str, arguments: dict[str, Any], active: Callable[[], bool]) -> dict[str, Any]:
        if name != "placement_experiment" or set(arguments) != {"problem"}:
            raise ValueError("tool is outside the installed placement contract")
        instance = PlacementProblem.model_validate(arguments["problem"])
        self.reset(GymTask(task_id="production-placement", partition="transfer", family="production", problem=instance))
        self.step({"type": "run-workflow"}, active)
        result = self.outcome()
        return {"problem": instance.model_dump(), "outcome": result["result"], "verification": result["verification"]}


class GymPlan(StrictModel):
    campaign_id: Identifier
    mission_id: Identifier
    original: PlacementWorkflow
    alternatives: list[PlacementWorkflow] = Field(min_length=1, max_length=32)
    tasks: list[GymTask] = Field(min_length=1, max_length=32)
    max_logical_units: int = Field(ge=1, le=10_000_000)
    max_seconds: int = Field(default=60, ge=1, le=600)
    max_authorized_micro_usd: int = Field(ge=1, le=10**9)
    environment_digest: Digest
    expires_at: int = Field(ge=1)

    @model_validator(mode="after")
    def only_training(self) -> GymPlan:
        if any(task.partition != "training" for task in self.tasks):
            raise ValueError("training plan cannot open protected or transfer partitions")
        if any(candidate.version != self.original.version + 1 for candidate in self.alternatives):
            raise ValueError("every alternative must be an explicit next retained version")
        stamps = [placement_fingerprint(task.problem) for task in self.tasks]
        if len(set(stamps)) != len(stamps):
            raise ValueError("training inputs must be distinct")
        if len(canonical(self)) > 100_000:
            raise ValueError("training plan exceeds its independent frame budget")
        return self


class GymCampaign:
    """One signed, finite, interruption-safe C activity in the existing Journal."""

    def __init__(
        self,
        costs: CostLedger,
        checkpoint: DurableCheckpoint,
        environment_digest: str,
        *,
        current_environment: Callable[[], str],
    ) -> None:
        self.costs, self.journal, self.checkpoint = costs, costs.journal, checkpoint
        self.environment_digest = environment_digest
        self.current_environment = current_environment

    def run(self, signed: SignedEnvelope) -> dict[str, Any]:
        signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
        payload = self.costs.trust.verify(signed, "flywheel-gym-plan", "controller")
        if set(payload) != {"journal_identity", "plan"} or payload["journal_identity"] != self.journal.identity:
            raise ValueError("Gym authorization belongs to another journal or schema")
        plan = GymPlan.model_validate(copy.deepcopy(payload["plan"]))
        if self.current_environment() != self.environment_digest:
            raise Conflict("Gym runtime changed; requalify before training")
        if plan.environment_digest != self.environment_digest or plan.expires_at <= int(time.time()):
            raise ValueError("Gym authorization has expired or names a different environment")
        key, activity = KEY + plan.campaign_id, "gym/" + plan.campaign_id
        state: dict[str, Any] = {
            "plan": signed.model_dump(),
            "status": "training",
            "trials": [],
            "logical_units": 0,
            "original": plan.original.model_dump(),
            "candidate": None,
            "authority_granted": False,
        }
        with self.journal.transaction() as cx:
            self.checkpoint.verify(self.journal, cx)
            try:
                self.journal.latest(key, cx)
            except KeyError:
                pass
            else:
                raise Conflict("campaign already attempted; preserve and reconcile original attempts")
            report = self.costs.report(cx=cx)
            if report["available_funds"] is None or report["available_funds"] < plan.max_authorized_micro_usd:
                raise Conflict("Gym requires reconciled available funds for its entire envelope")
            costs = self.costs.snapshot(cx)
            self.costs.require_open(costs, plan.mission_id, "C")
            if activity in costs["charges"]:
                raise Conflict("Gym activity already charged")
            charge = Charge(
                activity_id=activity,
                mission_id=plan.mission_id,
                bucket="C",
                category="compute",
                accrued_micro_usd=None,
                paid_micro_usd=0,
                basis="unknown",
                evidence_digest=digest("gym-plan", plan),
                note="Additional optional development only; paid delivery A is never charged again. Reconcile all resources.",
            )
            costs["charges"][activity] = {**charge.model_dump(), "signed": signed.model_dump()}
            self.costs._persist(cx, costs)
            head = self.journal.append(cx, key, state)["digest"]
            self.checkpoint.advance(self.journal, cx)
        started = time.monotonic()

        def active() -> bool:
            if self.current_environment() != self.environment_digest:
                raise Conflict("Gym runtime changed during training; preserve its uncertain attempt")
            return (
                time.monotonic() - started < plan.max_seconds
                and int(time.time()) < plan.expires_at
                and self.journal.latest("@control")["state"] == "ready"
            )

        def save() -> None:
            nonlocal head
            with self.journal.transaction() as cx:
                self.checkpoint.verify(self.journal, cx)
                if self.journal.latest(key, cx)["digest"] != head:
                    raise Conflict("competing campaign update; preserve uncertain work")
                head = self.journal.append(cx, key, state)["digest"]
                self.checkpoint.advance(self.journal, cx)

        try:
            scores = []
            for candidate in [plan.original, *plan.alternatives]:
                correct, units = 0, 0
                for task in plan.tasks:
                    if not active():
                        raise InterruptedError("Gym campaign stopped")
                    env = PlacementEnvironment(candidate)
                    env.reset(task)
                    # Save the exact attempt before any executable action.
                    state["pending"] = {"task": task.task_id, "artifact": candidate.model_dump()}
                    save()
                    previous = 0

                    def bounded() -> bool:
                        nonlocal previous
                        state["logical_units"] += env.units - previous
                        previous = env.units
                        if state["logical_units"] > plan.max_logical_units:
                            raise TimeoutError("campaign work budget exhausted")
                        return active()

                    env.step({"type": "run-workflow"}, bounded)
                    bounded()
                    outcome = env.outcome()
                    state["trials"].append({"task_id": task.task_id, **outcome})
                    state["pending"] = None
                    save()
                    if not active() or state["logical_units"] > plan.max_logical_units:
                        raise InterruptedError("Gym exhausted; no partial candidate is frozen")
                    correct += int(outcome["verification"]["accepted_finite_result"])
                    units += outcome["logical_units"]
                scores.append((-correct, units, canonical(candidate), candidate))
            winner_score = min(scores, key=lambda item: item[:3])
            winner = winner_score[3]
            if winner_score[:2] >= scores[0][:2]:
                state.update(status="no-improvement", candidate=None)
            else:
                state.update(
                    status="frozen-awaiting-protected-evaluation",
                    candidate=winner.model_dump(),
                    candidate_digest=digest("flywheel-program", winner),
                )
        except (InterruptedError, TimeoutError) as exc:
            state.update(status="interrupted-or-budget-exhausted", error=type(exc).__name__, candidate=None)
        except Exception as exc:
            state.update(status="failed-or-uncertain", error=type(exc).__name__, candidate=None)
        state["elapsed_ms"] = int(1000 * (time.monotonic() - started))
        state["training_input_digests"] = [digest("placement-input", task.problem) for task in plan.tasks]
        state["training_fingerprints"] = [placement_fingerprint(task.problem) for task in plan.tasks]
        save()
        return copy.deepcopy(state)


def evaluate_frozen(
    frozen: dict[str, Any], tasks: list[GymTask], *, active: Callable[[], bool] = lambda: True
) -> dict[str, Any]:
    """Technical paired evaluation; never self-certifies economic Alpha admission."""
    if frozen.get("status") != "frozen-awaiting-protected-evaluation":
        raise Conflict("protected evaluation requires a completed frozen candidate")
    candidate = PlacementWorkflow.model_validate(copy.deepcopy(frozen["candidate"]))
    if digest("flywheel-program", candidate) != frozen["candidate_digest"]:
        raise ValueError("candidate changed after freeze")
    original = PlacementWorkflow.model_validate(copy.deepcopy(frozen["original"]))
    forbidden = set(frozen["training_fingerprints"])
    rows: list[dict[str, Any]] = []
    for raw in tasks:
        task = GymTask.model_validate_json(canonical(raw))
        stamp = placement_fingerprint(task.problem)
        if task.partition == "training" or stamp in forbidden:
            raise ValueError("protected/transfer tasks must exclude every exposed training input")
        forbidden.add(stamp)
        arms = []
        for workflow in (original, candidate):
            env = PlacementEnvironment(workflow)
            env.reset(task)
            env.step({"type": "run-workflow"}, active)
            arms.append(env.outcome())
        rows.append({"task_id": task.task_id, "family": task.family, "v1": arms[0], "v2": arms[1]})
    return {
        "candidate_digest": frozen["candidate_digest"],
        "cases": rows,
        "training_completed": True,
        "technical_transfer_passed": bool(rows)
        and all(r["v2"]["verification"]["accepted_finite_result"] for r in rows),
        "competent_frontier_beta": "not executed",
        "net_alpha_positive": False,
        "growing_network_advantage": False,
        "live_qualified": False,
        "admission": "do not admit",
    }
