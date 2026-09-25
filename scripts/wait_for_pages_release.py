# SPDX-License-Identifier: Apache-2.0
"""Wait for the public Pages edge to expose the exact tested release commit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.url != "https://montrealai.github.io/AGI-Alpha-Agent-v0/":
        raise ValueError("Unexpected public release destination")
    for attempt in range(30):
        try:
            request = Request(args.url + "release.json?commit=" + args.commit, headers={"Cache-Control": "no-cache"})
            with urlopen(request, timeout=20) as response:
                manifest = json.load(response)
            if manifest["commit"] == args.commit:
                if args.output:
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(manifest))
                return
        except (OSError, ValueError, KeyError):
            pass
        print(f"Waiting for public Pages commit ({attempt + 1}/30)", flush=True)
        time.sleep(10)
    raise TimeoutError("The public site did not expose the tested commit within five minutes")


if __name__ == "__main__":
    main()
