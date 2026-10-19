# SPDX-License-Identifier: Apache-2.0
"""Independently exercise operator state omitted by bytecode-only commitments."""

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor.transformation import (
    DiscoveryLoop,
    DiscoveryRequest,
    OperatorRegistry,
    SelectionProgram,
    pilot_request,
)

GLOBAL_OPERATOR_CONFIGURATION = {"production": "lead"}


def _external_helper():
    return SelectionProgram(production="lead")


class _ExternalConfiguration:
    production = "lead"


@pytest.mark.parametrize("storage", ["positional-default", "keyword-default", "referenced-global"])
def test_mutable_operator_external_configuration_invalidates_approval(tmp_path, monkeypatch, storage):
    configuration = {"production": "lead"}

    class PositionalDefault:
        identity = "review-default"
        source_digest = "a" * 64

        def propose(self, request, settings=configuration):
            return [SelectionProgram(production=settings["production"])]

    class KeywordDefault:
        identity = "review-keyword"
        source_digest = "b" * 64

        def propose(self, request, *, settings=configuration):
            return [SelectionProgram(production=settings["production"])]

    class ReferencedGlobal:
        identity = "review-global"
        source_digest = "c" * 64

        def propose(self, request):
            return [SelectionProgram(production=GLOBAL_OPERATOR_CONFIGURATION["production"])]

    if storage == "referenced-global":
        monkeypatch.setitem(GLOBAL_OPERATOR_CONFIGURATION, "production", "lead")
    adapter = {
        "positional-default": PositionalDefault,
        "keyword-default": KeywordDefault,
        "referenced-global": ReferencedGlobal,
    }[storage]()
    registry = OperatorRegistry()
    registry.register(adapter)
    loop = DiscoveryLoop(Journal.initialize(tmp_path / "agent"), registry)
    raw = pilot_request().model_dump()
    raw["operator_ids"] = [adapter.identity]
    request = DiscoveryRequest.model_validate(raw)
    created = loop.create(request)
    loop.approve(request.campaign_id, created["binding_digest"])
    if storage == "referenced-global":
        monkeypatch.setitem(GLOBAL_OPERATOR_CONFIGURATION, "production", "weighted")
    else:
        configuration["production"] = "weighted"
    with pytest.raises(Conflict, match="changed"):
        loop.step(request.campaign_id, operation_id="modified-external-configuration")
    assert loop.show(request.campaign_id)["attempts"] == []


@pytest.mark.parametrize("dependency", ["function", "class"])
def test_unbound_external_helpers_require_a_separately_reviewed_driver(tmp_path, dependency):
    class FunctionDependency:
        identity = "review-function"
        source_digest = "d" * 64

        def propose(self, request):
            return [_external_helper()]

    class ClassDependency:
        identity = "review-class"
        source_digest = "e" * 64

        def propose(self, request):
            return [SelectionProgram(production=_ExternalConfiguration.production)]

    adapter = {"function": FunctionDependency, "class": ClassDependency}[dependency]()
    registry = OperatorRegistry()
    registry.register(adapter)
    loop = DiscoveryLoop(Journal.initialize(tmp_path / "agent"), registry)
    raw = pilot_request().model_dump()
    raw["operator_ids"] = [adapter.identity]
    with pytest.raises(ValueError, match="operator configuration|reviewed bounded driver"):
        loop.create(DiscoveryRequest.model_validate(raw))
