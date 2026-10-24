# SPDX-License-Identifier: Apache-2.0
"""Anonymous byte readback for the actual software site and retained preferred paper."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import pathlib
import subprocess
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--checkout", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    base = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"
    records = []
    for path in (
        "release.json",
        "index.html",
        "successor/index.html",
        "successor/alpha/index.html",
        "successor/work/index.html",
        "start/index.html",
        "try/index.html",
        "research-papers.json",
        "papers/successor-omega-harness-detector-v1.pdf",
    ):
        request = urllib.request.Request(base + path, headers={"User-Agent": "Alpha-public-patch-verifier"})
        with urllib.request.urlopen(request, timeout=90) as response:
            assert response.status == 200
            body = response.read()
            record = {
                "url": base + path,
                "http": response.status,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "content_type": response.headers.get("Content-Type"),
            }
            if path == "release.json":
                release = json.loads(body)
                assert release["version"] == "1.42.0" and release["commit"] == args.commit, release
                record["software_identity"] = release
            else:
                expected = subprocess.check_output(["git", "show", args.commit + ":docs/" + path], cwd=args.checkout)
                assert body == expected, path
                record["exact_merged_source_bytes"] = True
            if path.endswith(".pdf"):
                assert response.headers.get_content_type() == "application/pdf"
                assert "attachment" not in response.headers.get("Content-Disposition", "").lower()
                assert record["sha256"] == "326762251ff24993a8fc5baeaa6316a33a1bb08ba9f5475f5c0b17a05b6b357e"
            records.append(record)
    result = {
        "schema": "agialpha.patch-public-site-readback.v1",
        "passed": True,
        "version": "1.42.0",
        "commit": args.commit,
        "anonymous": True,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "records": records,
        "scope": "Exact served software identity/selected page and paper bytes. Browser behavior is separately recorded by the release public-pages gate.",
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": True, "pages": len(records), "commit": args.commit}))


if __name__ == "__main__":
    main()
