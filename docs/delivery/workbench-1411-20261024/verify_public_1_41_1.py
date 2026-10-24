# SPDX-License-Identifier: Apache-2.0
"""Anonymously verify one public patch release; retain only selected public bytes."""

import argparse
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
import pathlib
import re
import time
import urllib.error
import urllib.request
import zipfile


def get(url):
    return urllib.request.urlopen(
        urllib.request.Request(
            url, headers={"User-Agent": "Alpha-public-patch-verifier", "Accept": "application/vnd.github+json"}
        ),
        timeout=90,
    )


def json_get(url):
    with get(url) as response:
        assert response.status == 200
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir()
    assets_dir = root / "assets"
    assets_dir.mkdir()
    api = "https://api.github.com/repos/MontrealAI/AGI-Alpha-Agent-v0"
    release = json_get(api + "/releases/tags/v1.41.1")
    assert release["draft"] is False and release["prerelease"] is False
    assert release["tag_name"] == "v1.41.1" and release["published_at"]
    ref = json_get(api + "/git/ref/tags/v1.41.1")
    target = ref["object"]
    if target["type"] == "tag":
        tag = json_get(api + "/git/tags/" + target["sha"])
        target = tag["object"]
    else:
        tag = None
    assert target == {**target, "type": "commit", "sha": args.commit}, target
    assets = []
    page = 1
    while True:
        batch = json_get(api + "/releases/" + str(release["id"]) + "/assets?per_page=100&page=" + str(page))
        assets.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    names = [asset["name"] for asset in assets]
    assert len(names) == len(set(names)) and len(assets) > 4
    assert all(pathlib.PurePosixPath(name).name == name and name not in (".", "..") for name in names)
    selected = {
        "SHA256SUMS",
        "release-manifest.json",
        "requirements-agent.lock",
        "install_agent.py",
        "alpha_factory_v1-1.41.1-py3-none-any.whl",
        "alpha-agent-v1.41.1-public-validation-packs.json",
        "alpha-agent-v1.41.1-public-validation-core-001.zip",
    }
    assert selected <= set(names), selected - set(names)
    start = time.monotonic()

    def verify(asset):
        name = asset["name"]
        sha = hashlib.sha256()
        count = 0
        destination = assets_dir / name
        stream = destination.open("xb") if name in selected else None
        try:
            with get(asset["browser_download_url"]) as response:
                assert response.status == 200
                while chunk := response.read(1024 * 1024):
                    sha.update(chunk)
                    count += len(chunk)
                    if stream is not None:
                        stream.write(chunk)
            digest = sha.hexdigest()
            assert count == asset["size"], (name, count, asset["size"])
            assert asset["digest"] == "sha256:" + digest, (name, asset["digest"], digest)
            return {"name": name, "bytes": count, "sha256": digest, "url": asset["browser_download_url"], "http": 200}
        finally:
            if stream is not None:
                stream.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(verify, assets))
    sums = {}
    for line in (assets_dir / "SHA256SUMS").read_text().splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([^/\\]+)", line)
        assert match, line
        checksum, name = match.groups()
        assert name not in sums
        sums[name] = checksum
    assert set(sums) == set(names) - {"SHA256SUMS"}
    assert all(record["name"] == "SHA256SUMS" or sums[record["name"]] == record["sha256"] for record in records)
    manifest = json.loads((assets_dir / "release-manifest.json").read_bytes())
    assert manifest["commit"] == args.commit and manifest["version"] == "1.41.1"
    assert manifest["repository"] == "MontrealAI/AGI-Alpha-Agent-v0"
    workbench = manifest["public_successor_workbench"]
    assert workbench["commit"] == args.commit and workbench["version"] == "1.41.1"
    assert workbench["passed"] is True and workbench["errors"] == []
    assert workbench["sourceHash"] == "7ab63a685fdd28fe220350418df5f240960c7788f6405da4ed24a7c3902123c1"
    assert workbench["page_sha256"] == "903c2638a11f4b14a2cc2d817ed89563ac51af3545aedfc9ffc5c4f209bcb1f9"
    assert workbench["languages"] == ["en", "fr"] and workbench["viewports"] == [1440, 390, 320]
    assert workbench["axe"] == workbench["keyboard"] == workbench["offline_save_reopen"] == "PASS"
    pack_name = "alpha-agent-v1.41.1-public-validation-core-001.zip"
    inventory = json.loads((assets_dir / "alpha-agent-v1.41.1-public-validation-packs.json").read_bytes())
    assert inventory["commit"] == args.commit and inventory["version"] == "1.41.1"
    audited_reports = []
    with zipfile.ZipFile(assets_dir / pack_name) as archive:
        for relative in (
            "public-pages/successor-workbench/browser-report.json",
            "public-pages/successor/successor.json",
            "public-pages/successor-alpha/report.json",
            "public-pages/homepage/homepage.json",
        ):
            (row,) = [row for row in inventory["files"] if row["path"] == relative]
            (part,) = row["parts"]
            assert part["pack"] == pack_name and part["member"] == relative
            raw = archive.read(relative)
            assert len(raw) == row["bytes"] == part["bytes"]
            assert hashlib.sha256(raw).hexdigest() == row["sha256"] == part["sha256"]
            report = json.loads(raw)
            assert report["passed"] is True
            if relative.endswith("successor-workbench/browser-report.json"):
                assert report == workbench
            elif relative.endswith("successor-alpha/report.json"):
                assert report["commit"] == args.commit and report["version"] == "1.41.1"
            target = relative.replace("/", "_")
            (root / target).write_bytes(raw)
            audited_reports.append({"path": relative, "sha256": row["sha256"], "passed": True})
    snapshot = {"release": release, "assets": assets, "ref": ref, "annotated_tag": tag}
    (root / "public-metadata.json").write_text(json.dumps(snapshot, indent=2) + "\n")
    receipt = {
        "schema": "agialpha.patch-anonymous-artifacts.v1",
        "passed": True,
        "commit": args.commit,
        "version": "1.41.1",
        "tag": "v1.41.1",
        "release": release["html_url"],
        "release_id": release["id"],
        "published_at": release["published_at"],
        "anonymous": True,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "assets": records,
        "asset_count": len(records),
        "bytes_streamed": sum(record["bytes"] for record in records),
        "concurrency": 4,
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "public_browser_reports": audited_reports,
        "meaning": "Public tag/source and every asset body/size/API digest/checksum verified; identity alone is not correctness or authority.",
    }
    (root / "anonymous-artifacts.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps({k: receipt[k] for k in ("passed", "release", "asset_count", "bytes_streamed", "elapsed_seconds")})
    )


if __name__ == "__main__":
    main()
