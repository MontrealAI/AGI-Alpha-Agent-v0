# SPDX-License-Identifier: Apache-2.0
"""Read-only, explicit-dispatch eligibility before any release publication path."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import tomllib
from typing import Any
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

REPOSITORY = "MontrealAI/AGI-Alpha-Agent-v0"
SHA = re.compile(r"[0-9a-f]{40}")
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
MAX_BYTES = 2_097_152
MAX_TOTAL_BYTES = 16_777_216


def strict_json(raw: bytes) -> Any:
    """Reject malformed, duplicate-key and oversized identity documents."""
    if len(raw) > MAX_BYTES:
        raise ValueError("Identity document exceeds bound")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate identity field")
            result[key] = value
        return result

    return json.loads(
        raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("JSON constant"))
    )


class NoRedirect(HTTPRedirectHandler):
    """Never send the platform token to a redirected endpoint."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        raise ValueError("GitHub redirect refused")


class GitHubReadOnly:
    """Fixed HTTPS origin, GET only, bounded requests/time/bytes, no retries."""

    def __init__(self) -> None:
        token = os.environ.get("GH_TOKEN", "")
        if not token or "\n" in token or "\r" in token:
            raise ValueError("Platform GitHub token required")
        self.headers = {
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Cache-Control": "no-cache",
        }
        self.opener = build_opener(NoRedirect())
        self.calls = 0
        self.bytes = 0
        self.deadline = time.monotonic() + 120

    def get(self, endpoint: str, *, missing: bool = False) -> Any:
        self.calls += 1
        if self.calls > 32 or time.monotonic() >= self.deadline:
            raise ValueError("GitHub observation budget exhausted")
        if not re.fullmatch(
            r"repos/MontrealAI/AGI-Alpha-Agent-v0(?:/(?:git/ref/heads/main|git/ref/tags/v[0-9.]+|git/tags/[0-9a-f]{40}|releases(?:\?per_page=10&page=[1-9][0-9]?|/tags/v[0-9.]+|/[1-9][0-9]{0,18})))?",
            endpoint,
        ):
            raise ValueError("Read endpoint outside publication scope")
        request = Request("https://api.github.com/" + endpoint, headers=self.headers, method="GET")
        try:
            with self.opener.open(request, timeout=min(20, self.deadline - time.monotonic())) as response:
                if response.status != 200:
                    raise ValueError("Unexpected GitHub status")
                raw = response.read(MAX_BYTES + 1)
                self.bytes += len(raw)
                if self.bytes > MAX_TOTAL_BYTES or time.monotonic() >= self.deadline:
                    raise ValueError("GitHub total byte/deadline bound exceeded")
                return strict_json(raw)
        except HTTPError as error:
            error.close()
            # Only an exact permitted tag/release lookup can have an absent identity.
            if missing and error.code == 404 and ("/git/ref/tags/" in endpoint or "/releases/tags/" in endpoint):
                return None
            raise ValueError("GitHub identity lookup failed") from None


def source_identity() -> tuple[str, str]:
    """Observe the actual HEAD and raw version bytes, with no Git filters/fetch."""
    sha = os.environ.get("GITHUB_SHA", "")
    if (
        os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or not SHA.fullmatch(sha)
    ):
        raise ValueError("Authorized repository main source required")
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_NO_REPLACE_OBJECTS="1",
        GIT_NO_LAZY_FETCH="1",
        GIT_TERMINAL_PROMPT="0",
        GIT_OPTIONAL_LOCKS="0",
        GIT_ALLOW_PROTOCOL="",
    )
    command = ["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=" + os.devnull]
    head = subprocess.check_output(command + ["rev-parse", "--verify", "HEAD"], env=env, timeout=20).decode().strip()
    if head != sha:
        raise ValueError("Checkout HEAD differs from platform source")
    declared_bytes = Path("pyproject.toml").read_bytes()
    tracked = subprocess.check_output(command + ["cat-file", "blob", sha + ":pyproject.toml"], env=env, timeout=20)
    if declared_bytes != tracked:
        raise ValueError("Declared version bytes differ from committed source")
    version = tomllib.loads(declared_bytes.decode())["project"]["version"]
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError("Exact release semantic version required")
    return sha, version


def require_intent(version: str) -> int:
    """Require the platform's explicit native workflow_dispatch input."""
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise ValueError("Publication requires explicit workflow dispatch")
    event = strict_json(Path(os.environ["GITHUB_EVENT_PATH"]).read_bytes())
    if (
        not isinstance(event, dict)
        or event.get("ref") not in ("main", "refs/heads/main")
        or not isinstance(event.get("repository"), dict)
        or event["repository"].get("full_name") != REPOSITORY
    ):
        raise ValueError("Dispatch repository/ref identity differs")
    inputs = event.get("inputs")
    if (
        not isinstance(inputs, dict)
        or set(inputs) != {"publish_version", "publish_draft_id"}
        or inputs["publish_version"] != version
        or not isinstance(inputs["publish_draft_id"], str)
        or not re.fullmatch(r"[1-9][0-9]{0,18}", inputs["publish_draft_id"])
    ):
        raise ValueError("Dispatch publication version/draft identity differs")
    return int(inputs["publish_draft_id"])


def observe(client: GitHubReadOnly, sha: str, version: str, draft_id: int) -> dict[str, Any]:
    """Read current main and exact public/draft/tag identities without mutations."""
    base = "repos/" + REPOSITORY
    repo = client.get(base)
    if not isinstance(repo, dict) or repo.get("full_name") != REPOSITORY or repo.get("default_branch") != "main":
        raise ValueError("Repository identity differs")
    # Repository actor permissions are not proof of this token's draft visibility.
    # Only a successful exact-ID draft read below can supply that observation.
    main = client.get(base + "/git/ref/heads/main")
    if (
        not isinstance(main, dict)
        or main.get("ref") != "refs/heads/main"
        or main.get("object", {}).get("type") != "commit"
        or main["object"].get("sha") != sha
    ):
        raise ValueError("Current main differs from tested source")
    tag = "v" + version
    ref = client.get(base + "/git/ref/tags/" + tag, missing=True)
    target = None
    if ref is not None:
        if not isinstance(ref, dict) or ref.get("ref") != "refs/tags/" + tag or not isinstance(ref.get("object"), dict):
            raise ValueError("Tag identity is malformed")
        obj = ref["object"]
        if obj.get("type") == "tag":
            tag_sha = obj.get("sha")
            if not isinstance(tag_sha, str) or not SHA.fullmatch(tag_sha):
                raise ValueError("Annotated tag identity is malformed")
            annotated = client.get(base + "/git/tags/" + tag_sha)
            if not isinstance(annotated, dict) or annotated.get("sha") != tag_sha or annotated.get("tag") != tag:
                raise ValueError("Annotated tag name/object differs")
            obj = annotated.get("object", {})
        if not isinstance(obj, dict) or obj.get("type") != "commit" or obj.get("sha") != sha:
            raise ValueError("Existing tag differs from tested source; use a new release version")
        target = sha
    if target != sha:
        raise ValueError("Known draft requires an existing exact-source tag")
    direct = client.get(base + "/releases/tags/" + tag, missing=True)
    # No missing=True: inaccessible/absent known drafts, including 404, fail closed.
    known = client.get(base + "/releases/" + str(draft_id))

    def draft_identity(value: Any) -> dict[str, Any]:
        if (
            not isinstance(value, dict)
            or type(value.get("id")) is not int
            or value["id"] != draft_id
            or value.get("tag_name") != tag
            or value.get("draft") is not True
            or value.get("prerelease") is not False
            or value.get("target_commitish") != sha
            or value.get("published_at") is not None
        ):
            raise ValueError("Known draft identity/source differs or is already public")
        return {
            key: value.get(key) for key in ("id", "tag_name", "draft", "prerelease", "target_commitish", "published_at")
        }

    known_identity = draft_identity(known)
    matches = []
    for page in range(1, 11):
        releases = client.get(base + f"/releases?per_page=10&page={page}")
        if (
            not isinstance(releases, list)
            or len(releases) > 10
            or any(not isinstance(item, dict) or not isinstance(item.get("tag_name"), str) for item in releases)
        ):
            raise ValueError("Release listing is malformed")
        matches.extend(item for item in releases if item["tag_name"] == tag or item.get("id") == draft_id)
        if len(releases) < 10:
            break
    else:
        raise ValueError("Release inventory exceeds bound")
    if len(matches) != 1:
        raise ValueError("Conflicting or missing listed known draft identity")
    if draft_identity(matches[0]) != known_identity:
        raise ValueError("Known and listed release identities differ")
    # The by-tag endpoint may omit drafts. Its absence is never used as proof of
    # draft absence; the positive exact-ID read and listing remain mandatory.
    if direct is not None and draft_identity(direct) != known_identity:
        raise ValueError("Direct and known release identities differ")
    return {
        "commit": sha,
        "version": version,
        "tag": tag,
        "tagCommit": target,
        "draftReleaseId": draft_id,
        "knownDraftIdentity": known_identity,
    }


def require_eligibility(manifest: Path | None = None) -> dict[str, Any]:
    """Gate only; downstream publication still requires every existing acceptance."""
    sha, version = source_identity()
    draft_id = require_intent(version)
    if manifest is not None:
        value = strict_json(manifest.read_bytes())
        if not isinstance(value, dict) or value.get("commit") != sha or value.get("version") != version:
            raise ValueError("Publication artifact source/version differs")
    client = GitHubReadOnly()
    before = observe(client, sha, version, draft_id)
    if observe(client, sha, version, draft_id) != before or source_identity() != (sha, version):
        raise ValueError("Publication identity drifted during observation")
    if require_intent(version) != draft_id:
        raise ValueError("Publication draft intent drifted during observation")
    return {
        "schema": "agialpha.publication-eligibility.v1",
        **before,
        "publicationIntent": "platform-workflow-dispatch-exact-version-and-draft",
        "acceptanceGatesStillRequired": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    print(json.dumps(require_eligibility(args.manifest), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Event/provider contents and the token are never echoed to logs.
        raise SystemExit("Publication eligibility refused; no publication action is authorized.") from None
