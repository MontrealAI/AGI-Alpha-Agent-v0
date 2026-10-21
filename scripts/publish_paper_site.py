# SPDX-License-Identifier: Apache-2.0
"""Overlay verified papers on a PUBLIC software release without republishing it.

This module never creates tags, releases, wheels, source archives or pack schemas.
Preparation and public-edge waiting happen outside the shared Pages lock. The
short deployment job must call ``guard`` again after obtaining that lock.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import tomllib
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.release_packs import digest, restore, safe_name, unique_object

REPOSITORY = "MontrealAI/AGI-Alpha-Agent-v0"
PUBLIC_URL = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
SCHEMA = "agialpha.paper-publication.v1"
PLAN_SCHEMA = "agialpha.paper-publication-plan.v1"
WORKERS = (
    "service-worker.js",
    "assets/service-worker.js",
    "alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js",
)
GENERATED = ("index.html", *WORKERS)
METADATA = {"release.json", "paper-publication.json"}


class Deferred(ValueError):
    """No deployment is safe yet; a successful full release can retry later."""


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes(), object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "--no-replace-objects", "-C", str(root), *args], timeout=60)


def source_bytes(root: Path, commit: str, name: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("An exact source commit is required")
    return git(root, "show", f"{commit}:{safe_name(name)}")


def ancestor(root: Path, older: str, newer: str) -> bool:
    if not all(re.fullmatch(r"[0-9a-f]{40}", item) for item in (older, newer)):
        raise ValueError("Invalid ancestry identity")
    result = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(root), "merge-base", "--is-ancestor", older, newer], check=False
    )
    if result.returncode not in (0, 1):
        raise Deferred("Cannot establish the live publication's ancestry")
    return result.returncode == 0


def require_clean_source(root: Path, head: str) -> None:
    if git(root, "rev-parse", "HEAD").decode().strip() != head or git(root, "diff", "HEAD", "--"):
        raise ValueError("Paper source must be the exact clean checkout identified by the plan")


def require_context(event: dict[str, Any], environment: dict[str, str]) -> None:
    """workflow_run never trusts a fork, PR, arbitrary workflow or branch."""
    if environment.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise ValueError("Paper publication is restricted to the authorized repository")
    name = environment.get("GITHUB_EVENT_NAME")
    if name in {"push", "workflow_dispatch"}:
        if environment.get("GITHUB_REF") != "refs/heads/main":
            raise ValueError("Paper publication requires main")
    elif name == "workflow_run":
        run = event.get("workflow_run", {})
        if (
            event.get("action") != "completed"
            or run.get("name") != "Agent release acceptance"
            or run.get("conclusion") != "success"
            or run.get("head_branch") != "main"
            or run.get("head_repository", {}).get("full_name") != REPOSITORY
            or run.get("repository", {}).get("full_name") != REPOSITORY
            or run.get("event") not in {"push", "workflow_dispatch", "workflow_call"}
            or not re.fullmatch(r"[0-9a-f]{40}", run.get("head_sha", ""))
        ):
            raise ValueError("Untrusted release-completion event")
    else:
        raise ValueError("Unsupported paper publication event")


def api(endpoint: str, *, missing: bool = False) -> Any:
    result = subprocess.run(
        ["gh", "api", f"repos/{REPOSITORY}/{endpoint}", "-H", "Cache-Control: no-cache"],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if result.returncode:
        if missing and "(HTTP 404)" in result.stderr:
            raise Deferred("The matching software release is not public yet")
        raise RuntimeError(f"GitHub read failed for {endpoint}: {result.stderr.strip()}")
    return json.loads(result.stdout, object_pairs_hook=unique_object)


def current_main() -> str:
    ref = api("git/ref/heads/main")
    obj = ref.get("object", {})
    if ref.get("ref") != "refs/heads/main" or obj.get("type") != "commit":
        raise ValueError("Invalid main reference")
    head = obj.get("sha", "")
    if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("Invalid main identity")
    return head


def public_release(version: str) -> tuple[dict[str, Any], str]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Invalid software version")
    release = api(f"releases/tags/v{version}", missing=True)
    if release.get("draft") is not False or release.get("prerelease") is not False or not release.get("published_at"):
        raise Deferred("The matching software release is not fully public")
    if release.get("tag_name") != f"v{version}" or release.get("html_url") != (
        f"https://github.com/{REPOSITORY}/releases/tag/v{version}"
    ):
        raise ValueError("Unexpected public release identity")
    obj = api(f"git/ref/tags/v{version}")["object"]
    if obj.get("type") == "tag":
        obj = api(f"git/tags/{obj['sha']}")["object"]
    if obj.get("type") != "commit" or not re.fullmatch(r"[0-9a-f]{40}", obj.get("sha", "")):
        raise ValueError("Software tag must identify an exact commit")
    return release, obj["sha"]


def fetch_public(name: str) -> bytes:
    url = PUBLIC_URL + safe_name(name) + f"?paper-check={time.time_ns()}"
    request = Request(url, headers={"Cache-Control": "no-cache"})
    with urlopen(request, timeout=30) as response:
        if response.geturl() != url or response.status != 200:
            raise ValueError("Unexpected public-site response")
        raw = response.read()
        if not isinstance(raw, bytes):
            raise ValueError("Expected binary public-site content")
        return raw


def live_release() -> dict[str, Any]:
    value = json.loads(fetch_public("release.json"), object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise ValueError("Invalid live release manifest")
    pointer = value.get("paper_publication")
    if pointer is not None:
        if not isinstance(pointer, dict) or set(pointer) != {"path", "sha256", "paper_commit", "catalog_sha256"}:
            raise Deferred("Unsupported live paper-publication reference")
        raw = fetch_public("paper-publication.json")
        publication = json.loads(raw, object_pairs_hook=unique_object)
        if (
            pointer["path"] != "paper-publication.json"
            or pointer["sha256"] != sha256(raw)
            or publication.get("schema") != SCHEMA
            or publication.get("paper", {}).get("commit") != pointer["paper_commit"]
            or publication.get("paper", {}).get("catalog_sha256") != pointer["catalog_sha256"]
            or publication.get("software", {}).get("commit") != value.get("commit")
            or publication.get("software", {}).get("version") != value.get("version")
        ):
            raise Deferred("Live paper metadata is inconsistent; do not replace it")
    return value


def require_live_order(root: Path, plan: dict[str, Any], live: dict[str, Any]) -> bool:
    """True means advance; False is already current. Never roll content back."""
    if (live.get("commit"), live.get("version")) != (plan["software"]["commit"], plan["software"]["version"]):
        raise Deferred("Live software differs from the public baseline; never roll it back")
    pointer = live.get("paper_publication")
    if pointer is None:
        return True
    previous = pointer["paper_commit"]
    candidate = plan["paper"]["commit"]
    if previous == candidate:
        if pointer["catalog_sha256"] != plan["paper"]["catalog_sha256"]:
            raise ValueError("The same paper commit has conflicting catalog evidence")
        return False
    if not ancestor(root, previous, candidate):
        raise Deferred("Live paper publication is newer or divergent; never roll it back")
    return True


def inventory(site: Path) -> dict[str, dict[str, Any]]:
    if site.is_symlink() or not site.is_dir():
        raise ValueError("Site must be an ordinary directory")
    result: dict[str, dict[str, Any]] = {}
    names: set[str] = set()
    for path in sorted(site.rglob("*")):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError("Site contains a link or special file")
        if path.is_file():
            name = safe_name(path.relative_to(site).as_posix())
            if name.casefold() in names:
                raise ValueError("Case-ambiguous site inventory")
            names.add(name.casefold())
            result[name] = {"bytes": path.stat().st_size, "sha256": digest(path)}
    return result


def verify_delta(before: dict[str, Any], after: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    """Prove the complete complement unchanged, not merely selected demo files."""
    removed = sorted(set(before) - set(after))
    if removed:
        raise ValueError(f"Paper overlays cannot remove site files: {removed}")
    changed = sorted(name for name in set(before) | set(after) if before.get(name) != after.get(name))
    unexpected = set(changed) - allowed
    if unexpected:
        raise ValueError(f"Paper overlay changed unrelated inventory: {sorted(unexpected)}")
    unchanged = {name: before[name] for name in sorted(before) if name not in allowed}
    return {
        "files": [{"path": name, "before": before.get(name), "after": after[name]} for name in changed],
        "unchanged_files": len(unchanged),
        "unchanged_inventory_sha256": sha256(canonical(unchanged)),
        "removed": [],
    }


def site_assets(assets: dict[str, str]) -> dict[str, str]:
    result = {}
    for name, checksum in assets.items():
        safe_name(name)
        if not name.startswith("docs/") or Path(name).suffix.lower() not in {".pdf", ".tex"}:
            raise ValueError("Only catalog-referenced docs PDF/TEX files may be overlaid")
        if not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError("Invalid catalog asset digest")
        result[name.removeprefix("docs/")] = checksum
    return result


def compose_site(
    root: Path,
    site: Path,
    *,
    software_commit: str,
    baseline: dict[str, Any],
    old_assets: dict[str, str],
    new_assets: dict[str, str],
) -> dict[str, Any]:
    """Overlay only immutable catalog assets and exact source-generated files."""
    if inventory(site) != baseline:
        raise ValueError("Restored site differs from its verified source-bound inventory")
    old, new = site_assets(old_assets), site_assets(new_assets)
    if any(new.get(name) != checksum for name, checksum in old.items()):
        raise ValueError("Historical catalog assets must remain present and byte-identical")
    for name, checksum in old.items():
        if baseline.get(name, {}).get("sha256") != checksum:
            raise Deferred(f"Unsupported baseline: released paper differs from catalog: {name}")
    for name in GENERATED:
        # Copying source workers must preserve the actual baseline cache policy.
        if (site / name).read_bytes() != source_bytes(root, software_commit, "docs/" + name):
            raise Deferred(f"Unsupported baseline: released generated file differs from source: {name}")
    for name, checksum in new.items():
        source = root / "docs" / name
        if source.is_symlink() or digest(source) != checksum:
            raise ValueError(f"Catalog asset differs from checked source: {name}")
        if name in baseline and name not in old and baseline[name]["sha256"] != checksum:
            raise ValueError(f"New paper would overwrite an unrelated baseline file: {name}")
        (site / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, site / name)
    for name in GENERATED:
        source = root / "docs" / name
        if source.is_symlink() or not source.is_file():
            raise ValueError("Generated source must be an ordinary file")
        shutil.copyfile(source, site / name)
    return verify_delta(baseline, inventory(site), set(new) | set(GENERATED))


def download_release_assets(release: dict[str, Any], names: list[str], folder: Path) -> None:
    available = {item["name"] for item in release["assets"]}
    if len(available) != len(release["assets"]) or not set(names) <= available:
        raise Deferred("Public software release lacks an unambiguous supported site distribution")
    folder.mkdir(parents=True, exist_ok=True)
    command = ["gh", "release", "download", release["tag_name"], "--repo", REPOSITORY, "--dir", str(folder)]
    for name in names:
        if safe_name(name) != Path(name).name:
            raise ValueError("Release asset must be a flat safe filename")
        command += ["--pattern", name]
    subprocess.run(command, check=True, timeout=1200)


def verify_metadata(folder: Path) -> dict[str, str]:
    """Verify small metadata before trusting its pack download inventory."""
    checksums = {}
    for line in (folder / "SHA256SUMS").read_text().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^/\\]+)", line)
        if not match or match[2] in checksums:
            raise ValueError("Invalid or duplicate software release checksum")
        checksums[safe_name(match[2])] = match[1]
    for name in ("release-manifest.json", "site-packs.json"):
        path = folder / name
        if path.is_symlink() or not path.is_file() or checksums.get(name) != digest(path):
            raise ValueError(f"Public release metadata checksum differs: {name}")
    return checksums


def verify_distribution(folder: Path, software: str, version: str) -> dict[str, Any]:
    checksums = verify_metadata(folder)
    manifest = read_json(folder / "release-manifest.json")
    distribution = read_json(folder / "site-packs.json")
    if (
        manifest.get("repository") != REPOSITORY
        or (manifest.get("commit"), manifest.get("version")) != (software, version)
        or (distribution.get("commit"), distribution.get("version")) != (software, version)
        or manifest.get("distributions", {}).get("site", {}).get("manifest") != "site-packs.json"
    ):
        raise ValueError("Public software and site-pack source identities differ")
    assets = {item["name"]: item for item in manifest["assets"]}
    if len(assets) != len(manifest["assets"]):
        raise ValueError("Duplicate software release inventory")
    for name in ["release-manifest.json", "site-packs.json", *(item["name"] for item in distribution["packs"])]:
        path = folder / safe_name(name)
        if path.is_symlink() or not path.is_file() or checksums.get(name) != digest(path):
            raise ValueError(f"Public release checksum differs: {name}")
        if name != "release-manifest.json" and assets.get(name) != {
            "name": name,
            "bytes": path.stat().st_size,
            "sha256": digest(path),
        }:
            raise ValueError(f"Software release inventory differs: {name}")
    return distribution


def prepare(root: Path, folder: Path, site: Path) -> dict[str, Any]:
    from scripts.paper_changes import prove_paper_descendants
    from scripts.research_papers import CATALOG, asset_hashes, load_catalog, render, verify_files

    head = git(root, "rev-parse", "HEAD").decode().strip()
    require_clean_source(root, head)
    if current_main() != head:
        raise Deferred("Main advanced before preparation; a newer run owns publication")
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    release, software = public_release(version)
    try:
        proof = prove_paper_descendants(root, software, head)
    except ValueError as error:
        raise Deferred(f"Main requires full software acceptance, not a paper overlay: {error}") from error
    if proof.get("mode") != "paper" or software == head:
        raise Deferred("No paper-only descendant needs publication")
    catalog = load_catalog(root)
    verify_files(root, catalog)
    render(root, check=True)
    old_catalog = json.loads(source_bytes(root, software, CATALOG), object_pairs_hook=unique_object)
    names = ["SHA256SUMS", "release-manifest.json", "site-packs.json"]
    download_release_assets(release, names, folder)
    verify_metadata(folder)
    pack_manifest = read_json(folder / "site-packs.json")
    pack_names = [item["name"] for item in pack_manifest["packs"]]
    if not pack_names or any(
        not re.fullmatch(r"site-(?:core|models|media|research)-[0-9]{3,}\.zip", name) for name in pack_names
    ):
        raise ValueError("Unsupported site pack asset names")
    download_release_assets(release, pack_names, folder)
    distribution = verify_distribution(folder, software, version)
    identity = restore(folder / "site-packs.json", site)
    if (identity["commit"], identity["version"]) != (software, version):
        raise ValueError("Restored source identity differs")
    original_release = read_json(site / "release.json")
    if (
        original_release.get("commit") != software
        or original_release.get("version") != version
        or "paper_publication" in original_release
        or (site / "paper-publication.json").exists()
    ):
        raise Deferred("Unsupported baseline: site packs do not contain a pristine software release")
    before = inventory(site)
    if before != {row["path"]: {"bytes": row["bytes"], "sha256": row["sha256"]} for row in distribution["files"]}:
        raise ValueError("Restored inventory differs from the source-bound pack manifest")
    current_assets = asset_hashes(catalog)
    delta = compose_site(
        root,
        site,
        software_commit=software,
        baseline=before,
        old_assets=asset_hashes(old_catalog),
        new_assets=current_assets,
    )
    plan = {
        "schema": PLAN_SCHEMA,
        "status": "ready",
        "sealed": False,
        "software": {
            "commit": software,
            "version": version,
            "release_id": release["id"],
            "release_url": release["html_url"],
            "release_manifest_sha256": digest(folder / "release-manifest.json"),
            "site_packs_sha256": digest(folder / "site-packs.json"),
        },
        "paper": {
            "commit": head,
            "catalog_path": CATALOG,
            "catalog_sha256": digest(root / CATALOG),
            "files": site_assets(current_assets),
        },
        "proof": proof,
        "baseline_inventory": before,
        "original_release": original_release,
        "delta": delta,
        "run_url": f"https://github.com/{REPOSITORY}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
    }
    if not require_live_order(root, plan, live_release()):
        raise Deferred("This paper commit is already live")
    return plan


def seal(site: Path, plan: dict[str, Any], homepage: Path) -> dict[str, Any]:
    from scripts.homepage_evidence import verify_report

    report = read_json(homepage)
    verify_report(report, plan["paper"]["commit"], plan["software"]["version"], "local project subpath")
    allowed = set(plan["paper"]["files"]) | set(GENERATED)
    delta = verify_delta(plan["baseline_inventory"], inventory(site), allowed)
    if delta != plan["delta"]:
        raise ValueError("Site changed after the paper overlay was prepared")
    publication = {
        "schema": SCHEMA,
        "software": plan["software"],
        "paper": plan["paper"],
        "delta": delta,
        "evidence": {
            "scope": "paper-site-only",
            "software_acceptance_reused": True,
            "strict_paper_ancestry": plan["proof"],
            "run_url": plan["run_url"],
            "homepage": {"passed": True, "sha256": digest(homepage), "commit": plan["paper"]["commit"]},
        },
    }
    raw = canonical(publication)
    (site / "paper-publication.json").write_bytes(raw)
    pointer = {
        "path": "paper-publication.json",
        "sha256": sha256(raw),
        "paper_commit": plan["paper"]["commit"],
        "catalog_sha256": plan["paper"]["catalog_sha256"],
    }
    (site / "release.json").write_bytes(canonical({**plan["original_release"], "paper_publication": pointer}))
    after = inventory(site)
    verify_delta(plan["baseline_inventory"], after, allowed | METADATA)
    return {
        **plan,
        "sealed": True,
        "publication": pointer,
        "site_inventory_sha256": sha256(canonical(after)),
        "served_files": {name: after[name]["sha256"] for name in sorted(allowed | METADATA)},
    }


def remote_metadata_digest(release: dict[str, Any], name: str) -> str:
    """Read immutable public metadata again; release IDs alone do not bind assets."""
    matches = [item for item in release["assets"] if item["name"] == name]
    if len(matches) != 1 or not 0 < matches[0]["size"] <= 64 * 1024 * 1024:
        raise Deferred("Public baseline metadata is missing or unsupported")
    raw = subprocess.check_output(
        [
            "gh",
            "api",
            f"repos/{REPOSITORY}/releases/assets/{matches[0]['id']}",
            "-H",
            "Accept: application/octet-stream",
        ],
        timeout=60,
    )
    return sha256(raw)


def guard(root: Path, plan: dict[str, Any]) -> bool:
    """Call under github-pages immediately before deploy; never wait here."""
    from scripts.paper_changes import prove_paper_descendants

    if plan.get("schema") != PLAN_SCHEMA or plan.get("status") != "ready" or plan.get("sealed") is not True:
        raise ValueError("Only a sealed paper publication can deploy")
    head, software = plan["paper"]["commit"], plan["software"]
    require_clean_source(root, head)
    if current_main() != head:
        raise Deferred("Main advanced while this run awaited the Pages lock")
    release, source = public_release(software["version"])
    if source != software["commit"] or release["id"] != software["release_id"]:
        raise Deferred("Public baseline changed while this run awaited the Pages lock")
    for name, key in (("release-manifest.json", "release_manifest_sha256"), ("site-packs.json", "site_packs_sha256")):
        if remote_metadata_digest(release, name) != software[key]:
            raise Deferred("Public baseline metadata changed while this run awaited the Pages lock")
    if prove_paper_descendants(root, source, head) != plan["proof"]:
        raise ValueError("Paper ancestry proof changed")
    return require_live_order(root, plan, live_release())


def verify_live(plan: dict[str, Any]) -> dict[str, Any]:
    """Wait only in a separate, unlocked verification job for CDN propagation."""
    for attempt in range(30):
        try:
            live = live_release()
            if live.get("paper_publication") == plan["publication"]:
                for name, expected in plan["served_files"].items():
                    if sha256(fetch_public(name)) != expected:
                        raise ValueError(f"Public paper-site byte mismatch: {name}")
                return {
                    "scope": "paper-site-only",
                    "passed": True,
                    "software": plan["software"],
                    "paper": plan["paper"],
                }
        except (OSError, HTTPError, ValueError):
            pass
        if attempt < 29:
            time.sleep(10)
    raise TimeoutError("The public edge did not expose the verified paper publication within five minutes")


def output(name: str, value: str) -> None:
    if "GITHUB_OUTPUT" in os.environ:
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
            stream.write(f"{name}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "seal", "guard", "verify-live"))
    parser.add_argument("--plan", type=Path, default=Path("paper-state/plan.json"))
    parser.add_argument("--site", type=Path, default=Path("paper-site"))
    parser.add_argument("--downloads", type=Path, default=Path("paper-downloads"))
    parser.add_argument("--homepage", type=Path, default=Path("evidence/paper-homepage/homepage.json"))
    parser.add_argument("--output", type=Path, default=Path("evidence/paper-public.json"))
    args = parser.parse_args()
    require_context(read_json(Path(os.environ["GITHUB_EVENT_PATH"])), dict(os.environ))
    root = Path.cwd()
    try:
        if args.operation == "prepare":
            plan = prepare(root, args.downloads, args.site)
            args.plan.parent.mkdir(parents=True, exist_ok=True)
            args.plan.write_bytes(canonical(plan))
            output("head", plan["paper"]["commit"])
            output("ready", "true")
        elif args.operation == "seal":
            args.plan.write_bytes(canonical(seal(args.site, read_json(args.plan), args.homepage)))
        elif args.operation == "guard":
            ready = guard(root, read_json(args.plan))
            output("ready", str(ready).lower())
            print("Paper overlay is current and ordered" if ready else "Paper overlay is already live; no deployment")
        else:
            result = verify_live(read_json(args.plan))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(canonical(result))
            print(json.dumps(result))
    except Deferred as error:
        if args.operation not in {"prepare", "guard"}:
            raise
        output("ready", "false")
        print(f"Deferred without deployment: {error}")
        if args.operation == "prepare":
            args.plan.parent.mkdir(parents=True, exist_ok=True)
            args.plan.write_bytes(canonical({"schema": PLAN_SCHEMA, "status": "deferred", "reason": str(error)}))


if __name__ == "__main__":
    main()
