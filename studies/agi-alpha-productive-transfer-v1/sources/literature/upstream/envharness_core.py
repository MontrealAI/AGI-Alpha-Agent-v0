# Copyright 2026 The EnvHarness Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""EnvHarness -- the composable middleware ABC.

EnvHarness IS-A ActionableEnv that wraps another ActionableEnv. Because the
wrapped object (`self.inner`) is itself an ActionableEnv -- which may be a
raw bench or another EnvHarness -- harnesses stack arbitrarily::

    env = Toy24Env()                        # ActionableEnv
    env = Setup(env, actions=[...])         # ActionableEnv (with replay-from-reset)
    env = Rules(env)                      # ActionableEnv (with 6 hooks)
    # subclass _Rules(Rules) at load-time, overriding hooks

Save/load is layered. Each harness contributes only ITS OWN state -- the
inner env's state is saved by the env. The persistence module
(envharness.persistence.checkpoint) walks the stack and emits::

    {
      "env": {"type": "<env_type>", "state": <env.save_state()>},
      "harnesses": [
        {"type": "<inner harness tag>",  "state": <its .save_state()>},
        ...
        {"type": "<outer harness tag>", "state": <its .save_state()>}
      ]
    }

`harnesses[0]` is the layer closest to the env; `harnesses[-1]` is what
the agent sees.

Subclassing contract for a new EnvHarness::

    @register_harness("my_harness")
    class MyHarness(EnvHarness):
        def __init__(self, inner=None, my_field=None):
            super().__init__(inner)
            self.my_field = my_field
        # override reset / step / observe / evaluate as needed
        def save_state(self) -> dict:
            return {"my_field": self.my_field}
        @classmethod
        def from_state(cls, state: dict, inner) -> "MyHarness":
            return cls(inner=inner, my_field=state.get("my_field"))

The default reset/step/observe/evaluate delegate to `inner` so a harness
that only changes one axis only needs to override that one method.
"""
from __future__ import annotations

from abc import abstractmethod
from typing import Any

from envharness.core.actionable_env import ActionableEnv
from envharness.core.types import (
    Action, EnvResetResponse, EnvResponse, EvaluationResult, Observation,
    StepInfo,
)


class EnvHarness(ActionableEnv):
    """ABC: a composable wrapper around an inner ActionableEnv."""

    def __init__(self, inner: ActionableEnv | None = None) -> None:
        self._inner: ActionableEnv | None = inner

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    #
    # Both `env_type` (inherited from ActionableEnv) and `harness_type` are
    # required on every EnvHarness subclass. `env_type` lets a harness be
    # used in places that take an ActionableEnv tag (it returns the
    # harness's own tag by default); `harness_type` is what appears in the
    # checkpoint's `harnesses[].type` list.

    # Not @abstractmethod: same reasoning as ActionableEnv.env_type --
    # the @register_harness decorator injects the implementation after
    # the class is constructed, so ABC's abstract-method check would
    # block instantiation. Subclasses that forget to register fail
    # loudly at the first save/load attempt instead.

    @classmethod
    def harness_type(cls) -> str:
        """Stable string tag for this harness, set by @register_harness."""
        raise NotImplementedError(
            f"{cls.__name__}.harness_type() is not set. Decorate the "
            "class with @register_harness('<tag>') or override "
            "harness_type() manually."
        )

    @classmethod
    def env_type(cls) -> str:
        """A harness can technically be saved as the top-level env, in
        which case its env_type equals its harness_type. The checkpoint
        format does not currently use this path -- it always splits
        `env` from `harnesses` -- but the override keeps the ABC contract
        consistent."""
        return cls.harness_type()

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    @property
    def inner(self) -> ActionableEnv:
        if self._inner is None:
            raise RuntimeError(
                f"{type(self).__name__} has no inner env bound. "
                "Pass `inner=` at construction, or use the persistence "
                "loader which attaches inner during stack construction."
            )
        return self._inner

    def attach(self, inner: ActionableEnv) -> "EnvHarness":
        """Bind an inner ActionableEnv after construction. Useful when the
        harness is instantiated by user code (e.g. a Rules-subclassed
        `_Rules()` constructor that the LLM wrote with no args). Returns
        self so callers can chain."""
        self._inner = inner
        return self

    # ------------------------------------------------------------------
    # Default ActionableEnv impl: delegate everything to inner.
    # Subclasses override only the axes they affect.
    # ------------------------------------------------------------------

    def reset(self, seed: int | None = None,
              options: dict[str, Any] | None = None) -> EnvResetResponse:
        return self.inner.reset(seed, options)

    def step(self, action: Action) -> EnvResponse:
        return self.inner.step(action)

    def observe(self) -> Observation:
        return self.inner.observe()

    def evaluate(self) -> EvaluationResult:
        return self.inner.evaluate()

    def get_env_state(self) -> Any:
        return self.inner.get_env_state()

    def step_reward(self, step_info: StepInfo) -> float:
        """Default: delegate to inner so a deep stack still surfaces the
        innermost reward signal. Rules overrides this with its own
        hook implementation."""
        return self.inner.step_reward(step_info)

    def notify_replay_complete(self) -> None:
        """Delegate to inner so the notification reaches the base env
        through an arbitrarily deep harness stack."""
        self.inner.notify_replay_complete()

    def default_reset_args(self) -> tuple[int | None, dict]:
        """Forward to inner -- harnesses don't carry reset args of their
        own; the underlying env does."""
        return self.inner.default_reset_args()

    def reset_after_load(self) -> bool:
        return self.inner.reset_after_load()

    def close(self) -> None:
        try:
            self.inner.close()
        finally:
            self._inner = None

    @classmethod
    def env_state_schema(cls) -> str:
        # Walking through the stack at runtime is what the orchestrator
        # actually does to build a schema; this default is a placeholder
        # used only when an EnvHarness class is introspected before being
        # attached to an inner env.
        return "(see inner env's env_state_schema())"

    # ------------------------------------------------------------------
    # Save / load (harness-owned state; inner env is saved separately)
    # ------------------------------------------------------------------
    #
    # ActionableEnv defines `save_state` and `from_state` as abstract; we
    # repeat the abstract markers here so subclasses can't accidentally
    # forget them. Note that `from_state` for harnesses takes an additional
    # `inner` argument (the already-loaded inner ActionableEnv) -- the
    # persistence loader will provide it.

    @abstractmethod
    def save_state(self) -> dict:
        """Return ONLY this harness's own fields. Do NOT include inner's
        state -- the persistence walker handles that."""
        ...

    @classmethod
    @abstractmethod
    def from_state(cls, state: dict,  # type: ignore[override]
                   inner: ActionableEnv | None = None) -> "EnvHarness":
        """Reconstruct from save dict and attach to `inner`. The trailing
        `inner` parameter is the deliberate diverge from the parent
        ActionableEnv.from_state signature: harnesses always need an inner
        to be functional."""
        ...
