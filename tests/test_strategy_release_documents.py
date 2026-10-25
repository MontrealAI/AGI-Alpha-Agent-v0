# SPDX-License-Identifier: Apache-2.0
"""Keep additive Strategy guides out of every historical release document set."""
import hashlib
import json

from scripts.package_agent_release import release_document_name, release_documents


def test_historical_document_lists_remain_byte_identical() -> None:
    expected = {
        "1.42.0": "c9921062b7d48c624126cc5adb1505dd3dc2a9685315c4aa2518643ae4cd5049",
        "1.43.0": "0befe124935b0c2eb513f5856e352a2e2f8d6627064d335e292d70e5ce4988a5",
        "1.43.99": "66136da7d61f7bcb9f26d2db42b13d30f75219fcceab6bb5a4862aaaaa289b70",
    }
    for version, digest in expected.items():
        raw = json.dumps(release_documents(version), separators=(",", ":")).encode()
        assert hashlib.sha256(raw).hexdigest() == digest


def test_strategy_guide_has_an_exact_new_version_boundary() -> None:
    before, after = map(set, (release_documents("1.43.99"), release_documents("1.44.0")))
    before = {p for p in before if "/RELEASE_NOTES_" not in p}
    after = {p for p in after if "/RELEASE_NOTES_" not in p}
    assert after - before == {"docs/agent/STRATEGY_SUCCESSION.md"}
    assert not before - after
    documents = release_documents("1.44.0")
    assert len(documents) == len(set(documents))
    flattened = [release_document_name(p) for p in documents]
    assert len(flattened) == len(set(flattened))
