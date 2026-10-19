# SPDX-License-Identifier: Apache-2.0
"""Portable JSON keeps exact inert metadata while rejecting structured credentials."""

import json

import pytest

from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor.transformation import (
    DiscoveryLoop,
    DiscoveryRequest,
    assert_public_content,
    pilot_request,
)


@pytest.mark.parametrize("value", [{"value": "synthetic-fixture-only"}, ["synthetic-fixture-only"], True, False, 0, 7])
@pytest.mark.parametrize("key", ["api_key", "x-api-key", "authorization"])
def test_structured_credential_values_refuse_raw_and_double_encoded_json(key, value):
    raw = json.dumps({key: value})
    for text in (raw, json.dumps(raw)):
        with pytest.raises(ValueError, match="credential"):
            assert_public_content(text)
        request = pilot_request().model_dump()
        request["development"][0]["claims"][0]["text"] = text
        with pytest.raises(ValueError, match="credential"):
            DiscoveryRequest.model_validate(request)


def test_only_exact_inert_native_authorization_survives_serialization(tmp_path):
    loop = DiscoveryLoop(Journal.initialize(tmp_path / "agent"))
    request = pilot_request()
    loop.create(request)
    envelope = loop.envelope(request.campaign_id)
    assert_public_content(envelope)
    assert_public_content(json.dumps(envelope))
    assert_public_content(json.dumps(json.dumps(envelope)))
    envelope["authorization"]["authority_expansion"] = 0
    with pytest.raises(ValueError, match="credential"):
        assert_public_content(json.dumps(envelope))


def test_inert_looking_auth_without_native_schema_is_not_a_credential_exception():
    value = {"authorization": {"scope": "local-bounded", "binding": None, "authority_expansion": False}}
    with pytest.raises(ValueError, match="credential"):
        assert_public_content(json.dumps(value))
