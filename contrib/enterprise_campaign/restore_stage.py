# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def restore(stage: Path, output: Path) -> dict[str, str]:
    record = json.loads((stage / "stage.json").read_text(encoding="utf-8"))
    if record.get("schema") != "catalog-source-stage/v1":
        raise ValueError("Unsupported stage record.")
    files: dict[str, bytes] = {}
    for name, digest_field in [("catalog_product.py", "source_sha256"), ("test_catalog_product.py", "tests_sha256")]:
        source = stage / (name + ".txt")
        if source.is_symlink() or not source.is_file() or source.stat().st_size > 1_000_000:
            raise ValueError("Historical source must be a bounded regular file.")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != record[digest_field]:
            raise ValueError("Historical source digest mismatch.")
        files[name] = data
    output.mkdir(parents=True, exist_ok=False)
    package = output / "contrib" / "enterprise_campaign"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("# SPDX-License-Identifier: Apache-2.0\n", encoding="utf-8")
    for name, data in files.items():
        (package / name).write_bytes(data)
    return {"stage": str(stage), "output": str(output), "source_sha256": record["source_sha256"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore exact historical stage source into a new isolated directory.")
    parser.add_argument("stage", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(restore(args.stage, args.output), sort_keys=True))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"Refused: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
