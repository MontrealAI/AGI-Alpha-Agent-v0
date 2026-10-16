# SPDX-License-Identifier: Apache-2.0
"""Explicit source-bound publication intent must precede every write path."""

from __future__ import annotations

import copy
import io
import json
import os
from pathlib import Path
import subprocess
from urllib.error import HTTPError

import pytest
import yaml

from scripts import publication_eligibility as policy

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
OTHER = "b" * 40
VERSION = "1.34.0"
BASE = "repos/" + policy.REPOSITORY


class Reader:
    def __init__(self, state=None):
        self.state = state or {}
        self.calls = []

    def get(self, endpoint, *, missing=False):
        self.calls.append((endpoint, missing))
        if endpoint in self.state:
            value = self.state[endpoint]
            if isinstance(value, Exception):
                raise value
            return copy.deepcopy(value)
        if endpoint == BASE:
            return {"full_name": policy.REPOSITORY, "default_branch": "main", "permissions": {"push": True}}
        if endpoint.endswith("/git/ref/heads/main"):
            return {"ref": "refs/heads/main", "object": {"type": "commit", "sha": SHA}}
        if "/releases?" in endpoint:
            return []
        assert missing
        return None


@pytest.fixture
def approved(tmp_path, monkeypatch):
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {
                "ref": "main",
                "repository": {"full_name": policy.REPOSITORY},
                "inputs": {"publish_version": VERSION, "publish_draft_id": "12"},
            }
        )
    )
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    monkeypatch.setattr(policy, "source_identity", lambda: (SHA, VERSION))
    reader = Reader(
        {
            BASE + "/git/ref/tags/v" + VERSION: tag(),
            BASE + "/releases/12": release(),
            BASE + "/releases?per_page=10&page=1": [release()],
        }
    )
    monkeypatch.setattr(policy, "GitHubReadOnly", lambda: reader)
    return event, reader


def tag(target=SHA, kind="commit"):
    return {"ref": "refs/tags/v" + VERSION, "object": {"type": kind, "sha": target}}


def release(draft=True, target=SHA):
    return {"id": 12, "tag_name": "v" + VERSION, "draft": draft, "prerelease": False, "target_commitish": target}


def test_known_draft_observes_twice_and_still_requires_all_acceptance(approved):
    _, reader = approved
    result = policy.require_eligibility()
    assert result["version"] == VERSION and result["tagCommit"] == SHA and result["draftReleaseId"] == 12
    assert result["acceptanceGatesStillRequired"] is True
    assert len(reader.calls) == 12


@pytest.mark.parametrize("kind", ["commit", "tag"])
def test_matching_tag_and_exact_draft_can_resume(approved, kind):
    _, reader = approved
    reader.state[BASE + "/git/ref/tags/v" + VERSION] = tag("c" * 40 if kind == "tag" else SHA, kind)
    if kind == "tag":
        reader.state[BASE + "/git/tags/" + "c" * 40] = {
            "sha": "c" * 40,
            "tag": "v" + VERSION,
            "object": {"type": "commit", "sha": SHA},
        }
    prior = release()
    reader.state[BASE + "/releases?per_page=10&page=1"] = [prior]
    reader.state[BASE + "/releases/tags/v" + VERSION] = prior
    assert policy.require_eligibility()["draftReleaseId"] == 12


@pytest.mark.parametrize(
    "damage",
    [
        "push",
        "call",
        "blank",
        "other-version",
        "extra",
        "boolean",
        "wrong-ref",
        "wrong-repo",
        "duplicate",
        "missing-inputs",
        "missing-draft-id",
        "blank-draft-id",
        "boolean-draft-id",
        "zero-draft-id",
        "leading-zero-draft-id",
        "too-long-draft-id",
        "numeric-draft-id",
    ],
)
def test_invalid_dispatch_cannot_reach_network_or_write_helper(approved, monkeypatch, damage):
    path, reader = approved
    event = json.loads(path.read_text())
    if damage in {"push", "call"}:
        monkeypatch.setenv("GITHUB_EVENT_NAME", "push" if damage == "push" else "workflow_call")
    elif damage == "blank":
        event["inputs"]["publish_version"] = ""
    elif damage == "other-version":
        event["inputs"]["publish_version"] = "1.33.0"
    elif damage == "extra":
        event["inputs"]["bypass"] = True
    elif damage == "boolean":
        event["inputs"]["publish_version"] = True
    elif damage == "wrong-ref":
        event["ref"] = "other"
    elif damage == "wrong-repo":
        event["repository"]["full_name"] = "other/repo"
    elif damage == "missing-inputs":
        event.pop("inputs")
    elif damage == "missing-draft-id":
        event["inputs"].pop("publish_draft_id")
    elif damage.endswith("draft-id"):
        event["inputs"]["publish_draft_id"] = {
            "blank-draft-id": "",
            "boolean-draft-id": True,
            "zero-draft-id": "0",
            "leading-zero-draft-id": "012",
            "too-long-draft-id": "1" * 20,
            "numeric-draft-id": 12,
        }[damage]
    path.write_text(json.dumps(event) if damage != "duplicate" else '{"ref":"main","ref":"other"}')
    writes = []
    with pytest.raises((ValueError, KeyError)):
        policy.require_eligibility()
        writes.append("unreachable publication")
    assert writes == [] and reader.calls == []


@pytest.mark.parametrize(
    "damage",
    [
        "main",
        "repo",
        "tag-other",
        "nested-tag",
        "tag-name",
        "public-same",
        "public-other",
        "draft-without-tag",
        "draft-target",
        "duplicate-release",
        "direct-conflict",
        "list-malformed",
        "list-error",
        "tag-error",
        "release-error",
    ],
)
def test_bad_identity_refuses_before_any_write(approved, damage):
    _, reader = approved
    ref = BASE + "/git/ref/tags/v" + VERSION
    listing = BASE + "/releases?per_page=10&page=1"
    direct = BASE + "/releases/tags/v" + VERSION
    if damage == "main":
        reader.state[BASE + "/git/ref/heads/main"] = {
            "ref": "refs/heads/main",
            "object": {"type": "commit", "sha": OTHER},
        }
    elif damage == "repo":
        reader.state[BASE] = {"full_name": "other/repo", "default_branch": "main"}
    elif damage == "tag-other":
        reader.state[ref] = tag(OTHER)
    elif damage in {"nested-tag", "tag-name"}:
        reader.state[ref] = tag("c" * 40, "tag")
        reader.state[BASE + "/git/tags/" + "c" * 40] = {
            "sha": "c" * 40,
            "tag": "bad" if damage == "tag-name" else "v" + VERSION,
            "object": {"type": "tag", "sha": SHA},
        }
    elif damage in {"public-same", "public-other", "draft-target", "draft-without-tag"}:
        reader.state[ref] = None if damage == "draft-without-tag" else tag(OTHER if damage == "public-other" else SHA)
        reader.state[listing] = [release(damage.startswith("draft"), OTHER if damage == "draft-target" else SHA)]
    elif damage == "duplicate-release":
        reader.state[listing] = [release(), release()]
    elif damage == "direct-conflict":
        reader.state[direct] = release(False)
    elif damage == "list-malformed":
        reader.state[listing] = {"message": "no"}
    elif damage == "list-error":
        reader.state[listing] = RuntimeError("unavailable")
    elif damage == "tag-error":
        reader.state[ref] = RuntimeError("unavailable")
    else:
        reader.state[direct] = RuntimeError("unavailable")
    writes = []
    with pytest.raises((ValueError, RuntimeError)):
        policy.require_eligibility()
        writes.append("unreachable publisher")
    assert not writes


def test_late_main_or_source_or_manifest_drift_refuses(approved, monkeypatch, tmp_path):
    _, reader = approved
    original = reader.get
    seen = 0

    def moving(endpoint, **kwargs):
        nonlocal seen
        if endpoint.endswith("/git/ref/heads/main"):
            seen += 1
            if seen == 2:
                return {"ref": "refs/heads/main", "object": {"type": "commit", "sha": OTHER}}
        return original(endpoint, **kwargs)

    reader.get = moving
    with pytest.raises(ValueError, match="Current main"):
        policy.require_eligibility()
    reader.get = original
    sources = iter([(SHA, VERSION), (OTHER, VERSION)])
    monkeypatch.setattr(policy, "source_identity", lambda: next(sources))
    with pytest.raises(ValueError, match="drifted"):
        policy.require_eligibility()
    monkeypatch.setattr(policy, "source_identity", lambda: (SHA, VERSION))
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"commit": SHA, "version": "1.33.0"}))
    with pytest.raises(ValueError, match="artifact"):
        policy.require_eligibility(path)


def test_bounded_release_inventory_and_late_duplicate(approved):
    _, reader = approved
    listing = BASE + "/releases?per_page=10&page="
    for page in range(1, 11):
        reader.state[listing + str(page)] = [{"tag_name": f"v0.0.{i}"} for i in range(10)]
    with pytest.raises(ValueError, match="exceeds bound"):
        policy.require_eligibility()
    reader.state[listing + "1"][-1] = release()
    reader.state[listing + "2"] = [release()]
    with pytest.raises(ValueError, match="Conflicting"):
        policy.require_eligibility()


@pytest.mark.parametrize(
    "status,missing,allowed",
    [
        (404, True, True),
        (404, False, False),
        (401, True, False),
        (403, True, False),
        (429, True, False),
        (500, True, False),
    ],
)
def test_http_error_is_never_generic_absence(monkeypatch, status, missing, allowed):
    monkeypatch.setenv("GH_TOKEN", "disposable-local-test-token")
    client = policy.GitHubReadOnly()

    def fail(request, **kwargs):
        assert request.method == "GET" and request.full_url.startswith(
            "https://api.github.com/repos/" + policy.REPOSITORY
        )
        raise HTTPError(request.full_url, status, "fixture", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr(client.opener, "open", fail)
    if allowed:
        assert client.get(BASE + "/git/ref/tags/v1.34.0", missing=missing) is None
    else:
        with pytest.raises(ValueError):
            client.get(BASE + "/git/ref/tags/v1.34.0", missing=missing)
    assert client.calls == 1
    with pytest.raises(ValueError):
        client.get(BASE, missing=True)


def test_transport_refuses_redirect_unscoped_query_budget_and_bad_json(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "disposable-local-test-token")
    client = policy.GitHubReadOnly()
    with pytest.raises(ValueError):
        client.get("repos/other/repo")
    with pytest.raises(ValueError):
        policy.NoRedirect().redirect_request(None, None, 302, "", None, "https://elsewhere.invalid")
    client.calls = 32
    with pytest.raises(ValueError):
        client.get(BASE)
    for raw in [b'{"a":1,"a":2}', b"NaN", b"x" * (policy.MAX_BYTES + 1)]:
        with pytest.raises(ValueError):
            policy.strict_json(raw)


def test_actual_clean_local_git_source_and_tamper_refusal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_LAZY_FETCH="1")

    def git(*args):
        return subprocess.check_output(["git", *args], env=env).decode().strip()

    git("init", "-q")
    git("config", "user.name", "Disposable fixture")
    git("config", "user.email", "fixture@example.invalid")
    Path("pyproject.toml").write_text('[project]\nversion="1.34.0"\n')
    git("add", "pyproject.toml")
    git("commit", "-qm", "fixture")
    sha = git("rev-parse", "HEAD")
    monkeypatch.setenv("GITHUB_REPOSITORY", policy.REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", sha)
    monkeypatch.setenv("GIT_DIR", "/unrelated")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "99")
    assert policy.source_identity() == (sha, VERSION)
    Path("pyproject.toml").write_text('[project]\nversion="1.33.0"\n')
    with pytest.raises(ValueError, match="bytes differ"):
        policy.source_identity()
    monkeypatch.setenv("GITHUB_SHA", OTHER)
    with pytest.raises(ValueError, match="HEAD"):
        policy.source_identity()


def test_workflow_dispatch_only_gate_covers_package_pages_and_publisher():
    workflow = yaml.safe_load((ROOT / ".github/workflows/agent-release.yml").read_text())
    trigger = workflow.get("on", workflow.get(True))
    jobs = workflow["jobs"]
    assert trigger["workflow_dispatch"]["inputs"]["publish_version"] == {
        "description": "Explicit publication intent: exact declared version; leave empty for qualification only",
        "type": "string",
        "required": False,
        "default": "",
    }
    assert trigger["workflow_dispatch"]["inputs"]["publish_draft_id"] == {
        "description": "Exact previously approved draft release ID; leave empty for qualification only",
        "type": "string",
        "required": False,
        "default": "",
    }
    assert trigger["workflow_call"] is None
    early = jobs["publication-eligibility"]
    assert early["permissions"] == {"contents": "read"}
    for name in ["publication-eligibility", "pages", "publish"]:
        condition = jobs[name]["if"]
        for required in [
            "github.event_name == 'workflow_dispatch'",
            "inputs.publish_version != ''",
            "github.ref == 'refs/heads/main'",
            policy.REPOSITORY,
        ]:
            assert required in condition
    assert "publication-eligibility" not in jobs["package"]["needs"]
    assert len(jobs["package"]["needs"]) == 16
    for name in ["successor-journey", "runtime", "regression", "dependency-audit", "historical-ci"]:
        assert "publication-eligibility" not in jobs[name].get("needs", [])

    def position(name, needle):
        return next(
            i for i, s in enumerate(jobs[name]["steps"]) if needle in s.get("run", "") or needle in s.get("uses", "")
        )

    assert position("package", "scripts.publication_eligibility") < position("package", "scripts.package_agent_release")
    assert position("pages", "scripts.publication_eligibility") < position("pages", "actions/configure-pages@")
    deploy = position("pages", "actions/deploy-pages@")
    assert jobs["pages"]["steps"][deploy - 1]["run"].splitlines() == [
        "python -m scripts.release_context",
        "python -m scripts.publication_eligibility --manifest site/release.json",
    ]
    publisher = position("publish", "scripts.publish_agent_release")
    assert (
        jobs["publish"]["steps"][publisher - 1]["run"]
        == "python -m scripts.publication_eligibility --manifest release/release-manifest.json"
    )
    assert "tests/test_publication_eligibility.py" in str(jobs["runtime"]["steps"])


def test_original_publisher_and_current_main_guards_are_preserved():
    source = (ROOT / "scripts/publish_agent_release.py").read_text()
    assert "existing public tag points to a different commit" in source
    assert source.count("require_current_main()") == 2
    assert "Never move or overwrite an existing tag or published release" in source


def test_dispatch_accepts_only_the_two_exact_main_ref_representations(approved):
    path, _ = approved
    event = json.loads(path.read_text())
    event["ref"] = "refs/heads/main"
    path.write_text(json.dumps(event))
    assert policy.require_eligibility()["version"] == VERSION
    event["ref"] = "refs/tags/main"
    path.write_text(json.dumps(event))
    with pytest.raises(ValueError):
        policy.require_eligibility()


def test_transport_bounds_response_total_bytes_and_deadline(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "disposable-local-test-token")

    class Response:
        status = 200

        def __init__(self, raw):
            self.raw = raw

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self, limit):
            return self.raw[:limit]

    client = policy.GitHubReadOnly()
    monkeypatch.setattr(client.opener, "open", lambda *a, **k: Response(b"{}"))
    assert client.get(BASE) == {}
    client.bytes = policy.MAX_TOTAL_BYTES
    with pytest.raises(ValueError, match="total byte"):
        client.get(BASE)
    client = policy.GitHubReadOnly()
    monkeypatch.setattr(client.opener, "open", lambda *a, **k: Response(b"x" * (policy.MAX_BYTES + 1)))
    with pytest.raises(ValueError, match="exceeds bound"):
        client.get(BASE)
    client.deadline = 0
    with pytest.raises(ValueError, match="budget"):
        client.get(BASE)


def test_existing_133_tag_on_released_source_refuses_new_main(approved, monkeypatch):
    path, reader = approved
    event = json.loads(path.read_text())
    event["inputs"]["publish_version"] = "1.33.0"
    path.write_text(json.dumps(event))
    new_main = "17718b99c08b7d29e66772d2d44658c14a2880f6"
    released = "bd1728f067e3fd1e94d81a19142733d308de1e43"
    monkeypatch.setattr(policy, "source_identity", lambda: (new_main, "1.33.0"))
    reader.state[BASE + "/git/ref/heads/main"] = {
        "ref": "refs/heads/main",
        "object": {"type": "commit", "sha": new_main},
    }
    reader.state[BASE + "/git/ref/tags/v1.33.0"] = {
        "ref": "refs/tags/v1.33.0",
        "object": {"type": "tag", "sha": "c" * 40},
    }
    reader.state[BASE + "/git/tags/" + "c" * 40] = {
        "sha": "c" * 40,
        "tag": "v1.33.0",
        "object": {"type": "commit", "sha": released},
    }
    reached = []
    with pytest.raises(ValueError, match="Existing tag differs"):
        policy.require_eligibility()
        reached.append("Pages or publisher")
    assert reached == []


def test_source_git_environment_never_fetches_or_executes_filter(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    raw = b'[project]\nversion="1.34.0"\n'
    Path("pyproject.toml").write_bytes(raw)
    monkeypatch.setenv("GITHUB_REPOSITORY", policy.REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GIT_INDEX_FILE", "/unrelated")
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", "/unrelated")
    calls = []

    def git(args, **kwargs):
        calls.append(args)
        env = kwargs["env"]
        assert env["GIT_NO_LAZY_FETCH"] == "1" and env["GIT_ALLOW_PROTOCOL"] == ""
        assert "GIT_INDEX_FILE" not in env and "GIT_OBJECT_DIRECTORY" not in env
        assert not any(word in args for word in ["status", "diff", "checkout", "fetch"])
        return (SHA + "\n").encode() if "rev-parse" in args else raw

    monkeypatch.setattr(policy.subprocess, "check_output", git)
    assert policy.source_identity() == (SHA, VERSION) and len(calls) == 2


@pytest.mark.parametrize("same_source", [True, False])
def test_unchanged_final_publisher_preserves_public_assets(tmp_path, monkeypatch, same_source):
    from scripts import publish_agent_release as publisher

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", policy.REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_SHA", SHA)
    Path("pyproject.toml").write_text('[project]\nversion="1.34.0"\n')
    Path("release").mkdir()
    Path("release/release-manifest.json").write_text(json.dumps({"commit": SHA, "version": VERSION}))
    calls = []

    def gh(*args):
        calls.append(args)
        assert len(args) == 2 and args[0] == "api"
        if args[1].endswith("/releases?per_page=100"):
            return json.dumps(
                [{"tag_name": "v" + VERSION, "draft": False, "html_url": "https://example.invalid/release"}]
            )
        assert args[1].endswith("/git/ref/tags/v" + VERSION)
        return json.dumps({"object": {"type": "commit", "sha": SHA if same_source else OTHER}})

    monkeypatch.setattr(publisher, "gh", gh)
    monkeypatch.setattr(publisher.subprocess, "run", lambda *a, **k: pytest.fail("Write helper reached"))
    if same_source:
        publisher.main()
    else:
        with pytest.raises(ValueError, match="existing public tag"):
            publisher.main()
    assert len(calls) == 2


def test_cli_failure_never_echoes_event_or_token(tmp_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_LAZY_FETCH="1")

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, env=env).decode().strip()

    git("init", "-q")
    git("config", "user.name", "Disposable fixture")
    git("config", "user.email", "fixture@example.invalid")
    (tmp_path / "pyproject.toml").write_text('[project]\nversion="1.34.0"\n')
    git("add", "pyproject.toml")
    git("commit", "-qm", "fixture")
    event = tmp_path / "event.json"
    event.write_text('{"secret":"DO_NOT_ECHO_EVENT_SENTINEL",')
    env.update(
        GITHUB_REPOSITORY=policy.REPOSITORY,
        GITHUB_REF="refs/heads/main",
        GITHUB_SHA=git("rev-parse", "HEAD"),
        GITHUB_EVENT_NAME="workflow_dispatch",
        GITHUB_EVENT_PATH=str(event),
        GH_TOKEN="DO_NOT_ECHO_TOKEN_SENTINEL",
        PYTHONPATH=str(ROOT),
        PYTHONDONTWRITEBYTECODE="1",
    )
    result = subprocess.run(
        [os.sys.executable, "-m", "scripts.publication_eligibility"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 1 and result.stdout == ""
    assert result.stderr.strip() == "Publication eligibility refused; no publication action is authorized."
    assert "SENTINEL" not in result.stderr


@pytest.mark.parametrize("permissions", [None, {"push": False}, {"push": 1}, {"push": True}])
def test_actor_permissions_are_not_used_as_draft_visibility_proof(approved, permissions):
    _, reader = approved
    reader.state[BASE] = {"full_name": policy.REPOSITORY, "default_branch": "main", "permissions": permissions}
    assert policy.require_eligibility()["draftReleaseId"] == 12
    reader.state[BASE + "/releases/12"] = None
    with pytest.raises(ValueError, match="Known draft identity"):
        policy.require_eligibility()


@pytest.mark.parametrize(
    "damage",
    [
        "wrong-id",
        "missing",
        "public",
        "different-source",
        "branch-only-source",
        "wrong-tag",
        "prerelease",
        "published-time",
        "hidden-list",
        "wrong-listed-id",
    ],
)
def test_exact_known_draft_is_mandatory_before_write(approved, damage):
    _, reader = approved
    known = reader.state[BASE + "/releases/12"]
    if damage == "missing":
        reader.state[BASE + "/releases/12"] = ValueError("known draft unavailable")
    elif damage == "hidden-list":
        reader.state[BASE + "/releases?per_page=10&page=1"] = []
    elif damage == "wrong-listed-id":
        reader.state[BASE + "/releases?per_page=10&page=1"][0]["id"] = 13
    else:
        key, value = {
            "wrong-id": ("id", 13),
            "public": ("draft", False),
            "different-source": ("target_commitish", OTHER),
            "branch-only-source": ("target_commitish", "main"),
            "wrong-tag": ("tag_name", "v1.33.0"),
            "prerelease": ("prerelease", True),
            "published-time": ("published_at", "2026-10-16T12:00:00Z"),
        }[damage]
        known[key] = value
    writes = []
    with pytest.raises(ValueError):
        policy.require_eligibility()
        writes.append("unreachable publication")
    assert not writes


def test_late_known_draft_or_intent_drift_refuses(approved):
    path, reader = approved
    original = reader.get
    seen = 0

    def moving(endpoint, **kwargs):
        nonlocal seen
        value = original(endpoint, **kwargs)
        if endpoint == BASE + "/releases/12":
            seen += 1
            if seen == 2:
                value["draft"] = False
        return value

    reader.get = moving
    with pytest.raises(ValueError, match="Known draft"):
        policy.require_eligibility()
    seen = 0

    def changing_intent(endpoint, **kwargs):
        nonlocal seen
        value = original(endpoint, **kwargs)
        if endpoint == BASE + "/releases/12":
            seen += 1
            if seen == 2:
                event = json.loads(path.read_text())
                event["inputs"]["publish_draft_id"] = "13"
                path.write_text(json.dumps(event))
        return value

    reader.get = changing_intent
    with pytest.raises(ValueError, match="draft intent drifted"):
        policy.require_eligibility()


def test_known_draft_404_is_never_absence_even_when_requested(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "disposable-local-test-token")
    client = policy.GitHubReadOnly()

    def fail(request, **kwargs):
        raise HTTPError(request.full_url, 404, "fixture", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr(client.opener, "open", fail)
    with pytest.raises(ValueError, match="lookup failed"):
        client.get(BASE + "/releases/12", missing=True)


@pytest.mark.parametrize(
    "event,version,publication",
    [
        ("push", None, False),
        ("workflow_call", None, False),
        ("workflow_dispatch", "", False),
        ("workflow_dispatch", VERSION, True),
    ],
)
def test_qualification_package_remains_independent_of_publication_intent(event, version, publication):
    jobs = yaml.safe_load((ROOT / ".github/workflows/agent-release.yml").read_text())["jobs"]
    expected = "github.event_name == 'workflow_dispatch' && inputs.publish_version != '' && github.ref == 'refs/heads/main' && github.repository == 'MontrealAI/AGI-Alpha-Agent-v0'"
    assert jobs["publication-eligibility"]["if"] == expected
    assert "if" not in jobs["package"]
    assert set(jobs["package"]["needs"]) == {
        "mark-wallet",
        "runtime",
        "regression",
        "browser-contracts",
        "real-model",
        "gallery",
        "native-demos",
        "sovereign-lab",
        "finance-lab",
        "muzero-lab",
        "demo-distribution",
        "quality",
        "historical-ci",
        "dependency-audit",
        "successor-workbench",
        "successor-journey",
    }
    guard = next(s for s in jobs["package"]["steps"] if s.get("run") == "python -m scripts.publication_eligibility")
    assert guard["if"] == expected and not guard.get("continue-on-error", False)
    # All original package/install/archive checks remain runnable after their old16 gates.
    package_steps = str(jobs["package"]["steps"])
    for command in [
        "scripts.package_agent_release",
        "scripts/install_agent.py",
        "sha256sum -c SHA256SUMS",
        "actions/upload-artifact@",
    ]:
        assert command in package_steps
    actual_intent = event == "workflow_dispatch" and version not in (None, "")
    assert actual_intent == publication
    for name in ["pages", "publish"]:
        assert jobs[name]["if"] == expected
        assert "publication-eligibility" in jobs[name]["needs"] and "package" in jobs[name]["needs"]
        assert not jobs[name].get("continue-on-error", False)
