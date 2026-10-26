# SPDX-License-Identifier: Apache-2.0
"""Small synthetic counterexamples for the packaging verifier; no real mission.

Only this imported test instance substitutes a one-file synthetic production
seal. The real script, study, immutable manifest and recorded data are untouched.
"""

import argparse
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import warnings
import zipfile

sys.dont_write_bytecode = True
import build_companion as subject  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, help="New receipt outside study root")
    args = parser.parse_args()
    receipt_path = subject.outside_study(args.receipt, "Synthetic test receipt")
    original_script_hash = subject.digest(Path(subject.__file__))["sha256"]
    outcomes = []
    payload = b"Synthetic packaging verifier fixture. No production observation.\n"
    row = {"path": "production/fixture.txt", "bytes": len(payload),
           "sha256": hashlib.sha256(payload).hexdigest()}
    sealed = subject.json_bytes({"files": [row]})
    subject.SEALED_SHA256 = hashlib.sha256(sealed).hexdigest()
    subject.SEALED_COUNT = 1
    members = {row["path"]: payload, subject.SEALED_PATH: sealed}
    rows = [{"path": name, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
            for name, body in members.items()]
    manifest = {"archive_root": "fixture", "files": rows}

    def make_zip(mode):
        current = json.loads(json.dumps(manifest))
        if mode == "wrong_payload_hash":
            current["files"][0]["sha256"] = "0" * 64
        body = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(body, "w", compression=zipfile.ZIP_STORED) as zf:
                values = dict(members)
                values[subject.ARCHIVE_MANIFEST] = subject.json_bytes(current)
                if mode == "unmanifested_member":
                    values["extra.txt"] = b"unexpected"
                for name, data in values.items():
                    info = zipfile.ZipInfo("fixture/" + name)
                    info.external_attr = (stat.S_IFREG | 0o644) << 16
                    zf.writestr(info, data)
                if mode == "duplicate_member":
                    zf.writestr("fixture/production/fixture.txt", payload)
                if mode == "path_traversal":
                    zf.writestr("fixture/../escape.txt", b"unsafe")
        result = body.getvalue()
        if mode == "truncated_central_directory":
            result = result[:-22]
        if mode == "crc_corruption":
            offset = result.index(payload)
            result = result[:offset] + bytes([result[offset] ^ 1]) + result[offset + 1:]
        return result

    with tempfile.TemporaryDirectory(prefix="agialpha-packager-counterexamples-") as temporary:
        work = Path(temporary)
        for mode in ("valid", "wrong_payload_hash", "unmanifested_member", "duplicate_member",
                     "path_traversal", "truncated_central_directory", "crc_corruption"):
            archive = work / (mode + ".zip")
            archive.write_bytes(make_zip(mode))
            record = subject.new_receipt("synthetic-fixture")
            error = None
            try:
                result = subject.verify_archive(archive, work / (mode + "-extracted"), record)
            except (ValueError, zipfile.BadZipFile, KeyError) as exc:
                error = type(exc).__name__ + ": " + str(exc)
            passed = (error is None) if mode == "valid" else (error is not None)
            outcomes.append({"case": mode, "passed": passed, "expected": "accept" if mode == "valid" else "reject", "observed_error": error})
            if not passed:
                raise AssertionError(f"Synthetic custody case failed: {mode}")
        # A long signed-download secret is blocked, while the scanner's own
        # source and a public Git commit URL must not trigger a false positive.
        secret_file = work / "synthetic-credential.json"
        secret_file.write_text(json.dumps({"url": "https://example.invalid/?X-Amz-" + "Signature=" + "a" * 64}))
        blocked = False
        try:
            subject.check_credentials(secret_file, "synthetic-credential.json")
        except ValueError:
            blocked = True
        subject.check_credentials(Path(subject.__file__), "packaging/build_companion.py")
        outcomes.append({"case": "synthetic_signed_url_blocked_without_self_match", "passed": blocked})
        if not blocked:
            raise AssertionError("Synthetic credential was not blocked")
    receipt = {"schema": "agialpha-packaging-counterexamples/v1", "created_at": subject.utcnow(),
               "script_sha256": original_script_hash, "synthetic_seal_only": True,
               "real_sealed_production_modified": False, "final_companion_created": False,
               "new_primary_missions": 0, "new_customer_jobs": 0,
               "passed": all(x["passed"] for x in outcomes), "checks": outcomes}
    subject.write_new_json(receipt_path, receipt)
    print(json.dumps({"passed": receipt["passed"], "checks": len(outcomes), "receipt": str(receipt_path), "final_companion_created": False}))


if __name__ == "__main__":
    main()
