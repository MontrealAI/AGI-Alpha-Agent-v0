# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any
import venv
import zipfile


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(repo: Path, output: Path) -> dict[str, Any]:
    repo, output = repo.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    temporary = output / "tmp"
    temporary.mkdir()
    receipts: list[dict[str, Any]] = []
    env = dict(
        os.environ, PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1", PIP_DISABLE_PIP_VERSION_CHECK="1", TMPDIR=str(temporary)
    )

    def run(
        label: str, args: list[str], cwd: Path, expected: int = 0, extra: dict[str, str] | None = None
    ) -> dict[str, Any]:
        started = time.perf_counter()
        result = subprocess.run(args, cwd=cwd, env=env | (extra or {}), capture_output=True, text=True, timeout=180)
        (output / (label + ".stdout.txt")).write_text(result.stdout)
        (output / (label + ".stderr.txt")).write_text(result.stderr)
        receipt = dict(
            label=label,
            argv=args,
            cwd=str(cwd),
            returncode=result.returncode,
            expected_returncode=expected,
            passed=result.returncode == expected,
            elapsed_seconds=time.perf_counter() - started,
        )
        receipts.append(receipt)
        return receipt

    campaign = repo / "contrib/enterprise_campaign"
    sources = [
        repo / "pyproject.toml",
        *sorted(campaign.glob("*.py")),
        *sorted(campaign.glob("*.json")),
        *sorted(path for path in campaign.glob("stages/*/*") if path.suffix in {".txt", ".json"}),
    ]
    identity = {str(path.relative_to(repo)): sha256(path) for path in sources}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    build = run(
        "wheel-build",
        [sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(output / "wheel")],
        repo,
    )
    if not build["passed"]:
        report = dict(status="BUILD FAILED", source_commit=commit, sources=identity, commands=receipts)
        (output / "INSTALLATION.json").write_text(json.dumps(report, indent=2) + "\n")
        return report
    (wheel,) = (output / "wheel").glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        for path in sources[1:]:
            name = str(path.relative_to(repo))
            if name.startswith("contrib/") and archive.read(name) != path.read_bytes():
                raise AssertionError("Wheel source mismatch: " + name)
    clean, shared = output / "clean-venv", output / "runtime-venv"
    venv.create(clean, with_pip=True, system_site_packages=False)
    venv.create(shared, with_pip=True, system_site_packages=True)
    clean_python, runtime_python = str(clean / "bin/python"), str(shared / "bin/python")
    outside = output / "outside-checkout"
    outside.mkdir()
    for label, python in (("clean", clean_python), ("runtime", runtime_python)):
        run(label + "-install", [python, "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)], outside)
        run(label + "-pip-check", [python, "-m", "pip", "check"], outside)
    cli = str(clean / "bin/alpha-enterprise-campaign")
    run("installed-help", [cli, "--help"], outside)
    run(
        "installed-identity",
        [
            clean_python,
            "-c",
            (
                "import hashlib,json,importlib.metadata as m;from pathlib import Path;"
                "import contrib.enterprise_campaign.catalog_product as p;"
                "print(json.dumps({'module':p.__file__,'sha256':hashlib.sha256(Path(p.__file__).read_bytes()).hexdigest(),"
                "'distribution_version':m.version('alpha-factory-v1'),'generation':p.CAPABILITY_GENERATION}))"
            ),
        ],
        outside,
    )
    before = '\ufeffsku,title,price\r\nA,"Thé, vert",2.00\r\nB,Café,3.50\r\n'
    after = 'sku,title,price\nA,"Thé, vert",2.50\nC,Chocolat,4.00\n'
    before_path, after_path = outside / "before.csv", outside / "after.csv"
    before_path.write_bytes(before.encode())
    after_path.write_bytes(after.encode())
    package_path = outside / "package.json"
    run(
        "installed-production",
        [cli, "reconcile", str(before_path), str(after_path), "--keys", "sku", "--output", str(package_path)],
        outside,
    )
    package = json.loads(package_path.read_text())
    proof = package["proof_digest"]
    common = [str(before_path), str(package_path), "--expected-package-digest", proof]
    run(
        "revoked-authority-refusal",
        [cli, "apply", *common, "--output", str(outside / "unauthorized.csv")],
        outside,
        expected=2,
    )
    run(
        "stale-approval-refusal",
        [
            cli,
            "apply",
            str(before_path),
            str(package_path),
            "--authorize",
            "--expected-package-digest",
            "0" * 64,
            "--output",
            str(outside / "stale-approval.csv"),
        ],
        outside,
        expected=2,
    )
    applied = outside / "applied.csv"
    run("installed-apply", [cli, "apply", *common, "--authorize", "--output", str(applied)], outside)
    restarted = outside / "after-process-restart.csv"
    run("restart-repeat", [cli, "apply", *common, "--authorize", "--output", str(restarted)], outside)
    run(
        "existing-output-refusal", [cli, "apply", *common, "--authorize", "--output", str(applied)], outside, expected=2
    )
    rolled = outside / "rollback.csv"
    run(
        "installed-rollback",
        [
            cli,
            "rollback",
            str(applied),
            str(package_path),
            "--authorize",
            "--expected-package-digest",
            proof,
            "--output",
            str(rolled),
        ],
        outside,
    )
    bad = dict(package, changes=[])
    bad_path = outside / "tampered-package.json"
    bad_path.write_text(json.dumps(bad))
    run(
        "tampered-package-refusal",
        [
            cli,
            "apply",
            str(before_path),
            str(bad_path),
            "--authorize",
            "--expected-package-digest",
            proof,
            "--output",
            str(outside / "tampered.csv"),
        ],
        outside,
        expected=2,
    )
    stale = outside / "stale.csv"
    stale.write_text("sku,title,price\nA,Different,1\n")
    run(
        "stale-source-refusal",
        [
            cli,
            "apply",
            str(stale),
            str(package_path),
            "--authorize",
            "--expected-package-digest",
            proof,
            "--output",
            str(outside / "stale-output.csv"),
        ],
        outside,
        expected=2,
    )
    symlink = outside / "symlink.csv"
    symlink.symlink_to(before_path)
    run(
        "symlink-input-refusal",
        [
            cli,
            "reconcile",
            str(symlink),
            str(after_path),
            "--keys",
            "sku",
            "--output",
            str(outside / "symlink-output.json"),
        ],
        outside,
        expected=2,
    )
    for label, text in (("duplicate", "sku,title,price\nA,x,1\nA,y,2\n"), ("malformed", 'sku,title,price\nA,"bad,1\n')):
        path = outside / (label + ".csv")
        path.write_text(text)
        run(
            label + "-input-refusal",
            [
                cli,
                "reconcile",
                str(path),
                str(after_path),
                "--keys",
                "sku",
                "--output",
                str(outside / (label + "-output.json")),
            ],
            outside,
            expected=2,
        )
    clean_assertions = {
        "exact_output": applied.read_bytes() == after.encode(),
        "restart_same_result": restarted.read_bytes() == applied.read_bytes(),
        "exact_rollback": rolled.read_bytes() == before.encode(),
        "original_source_unchanged": before_path.read_bytes() == before.encode(),
        "refused_writes_absent": not any(
            (outside / name).exists()
            for name in (
                "unauthorized.csv",
                "stale-approval.csv",
                "tampered.csv",
                "stale-output.csv",
                "symlink-output.json",
                "duplicate-output.json",
                "malformed-output.json",
            )
        ),
    }
    run("alpha-agent-help", [str(shared / "bin/alpha-agent"), "--help"], outside)
    run("runtime-init", [str(shared / "bin/alpha-agent"), "--home", str(outside / "agent"), "init"], outside)
    run("runtime-verify", [str(shared / "bin/alpha-agent"), "--home", str(outside / "agent"), "verify"], outside)
    copied = output / "copied-tests"
    shutil.copytree(repo / "tests/runtime", copied / "tests/runtime")
    shutil.copytree(repo / "scripts", copied / "scripts")
    fixture = "alpha_factory_v1/core/runtime/chain.py"
    with zipfile.ZipFile(wheel) as archive:
        fixture_path = copied / fixture
        fixture_path.parent.mkdir(parents=True)
        fixture_path.write_bytes(archive.read(fixture))
    run(
        "runtime-import-identity",
        [
            runtime_python,
            "-c",
            (
                "import json;import alpha_factory_v1.core.runtime.chain as c;"
                "import alpha_factory_v1.core.runtime.successor.flywheel_enterprise as e;"
                "print(json.dumps({'chain':c.__file__,'enterprise':e.__file__}))"
            ),
        ],
        outside,
    )
    runtime_tests = [
        "test_flywheel_authority.py",
        "test_flywheel_enterprise_authority.py",
        "test_flywheel_enterprise_command_authority.py",
        "test_flywheel_invocation_cost_authority.py",
        "test_flywheel_reconciliation_closure.py",
    ]
    run(
        "installed-runtime-boundaries",
        [
            runtime_python,
            "-m",
            "pytest",
            "--noconftest",
            "-o",
            "addopts=",
            *[str(copied / "tests/runtime" / name) for name in runtime_tests],
            "-q",
        ],
        outside,
        extra={"PYTHONPATH": str(copied) + os.pathsep + str(copied / "tests/runtime")},
    )
    installed_identity = json.loads((output / "installed-identity.stdout.txt").read_text())
    clean_assertions["installed_source_matches"] = (
        installed_identity["sha256"] == identity["contrib/enterprise_campaign/catalog_product.py"]
    )
    clean_assertions["installed_outside_checkout"] = not installed_identity["module"].startswith(str(repo))
    generation = installed_identity["generation"]
    if generation >= 1:
        fresh_before = outside / "fresh-before.csv"
        fresh_after = outside / "fresh-after.csv"
        fresh_package = outside / "fresh-package.json"
        fresh_before.write_text("sku,locale,price\nA,en,2.00\nA,fr,3.50\n")
        fresh_after.write_text(
            "code,prix,locale\nA,2.0,en\nA,3.75,fr\nC,6.25,en\n"
            if generation >= 2
            else "sku,locale,price\nA,en,2.00\nA,fr,3.75\nC,en,6.25\n"
        )
        args = [
            cli,
            "reconcile",
            str(fresh_before),
            str(fresh_after),
            "--keys",
            "sku",
            "locale",
            "--generation",
            str(generation),
            "--output",
            str(fresh_package),
        ]
        if generation >= 2:
            args += ["--decimal-columns", "price", "--aliases", '{"code":"sku","prix":"price"}']
        run("installed-constructed-successor", args, outside)
        if fresh_package.exists():
            fresh = json.loads(fresh_package.read_text())
            expected = "sku,locale,price\nA,en,2.00\nA,fr,3.75\nC,en,6.25\n"
            clean_assertions["constructed_successor_exact_output"] = fresh["output_csv"] == expected
            fresh_applied = outside / "fresh-applied.csv"
            run(
                "installed-successor-apply",
                [
                    cli,
                    "apply",
                    str(fresh_before),
                    str(fresh_package),
                    "--authorize",
                    "--expected-package-digest",
                    fresh["proof_digest"],
                    "--output",
                    str(fresh_applied),
                ],
                outside,
            )
            run(
                "installed-successor-rollback",
                [
                    cli,
                    "rollback",
                    str(fresh_applied),
                    str(fresh_package),
                    "--authorize",
                    "--expected-package-digest",
                    fresh["proof_digest"],
                    "--output",
                    str(outside / "fresh-rollback.csv"),
                ],
                outside,
            )
            clean_assertions["constructed_successor_rollback"] = (
                outside / "fresh-rollback.csv"
            ).read_bytes() == fresh_before.read_bytes()
    failures = [
        receipt["label"]
        for receipt in receipts
        if not receipt["passed"] and not receipt["label"].endswith("-pip-check")
    ]
    dependency_failures = [
        receipt["label"] for receipt in receipts if not receipt["passed"] and receipt["label"].endswith("-pip-check")
    ]
    report = dict(
        status="SCOPED INSTALLED PRODUCT PASS" if not failures and all(clean_assertions.values()) else "SCOPED FAILURE",
        source_commit=commit,
        dirty_source_identity=identity,
        wheel=str(wheel),
        wheel_sha256=sha256(wheel),
        installed=installed_identity,
        assertions=clean_assertions,
        commands=receipts,
        failures=failures,
        dependency_failures=dependency_failures,
        test_fixture="Copied paid_origin tests require chain.py as text. Exact wheel bytes supplied without package "
        "__init__.py; runtime import locations separately confirm installed code is executed.",
        dependency_qualification="HOLD: clean venv installs root wheel without dependencies for stdlib product only; "
        "runtime tests use system-site-packages. Pip-check failures remain separate failed dependency gates.",
        release_qualification="HOLD: no full hosted CI, required review, locked dependency-clean matrix, "
        "signed release, publication or deployment performed by this helper.",
        boundaries="Actual local build/install/process invocations and bytes. No customer, payment or production authority.",
    )
    (output / "INSTALLATION.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and qualify the scoped product outside its source checkout.")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = qualify(args.repo, args.output)
    print(json.dumps({"status": report["status"], "report": str(args.output / "INSTALLATION.json")}))
    return 0 if report["status"] == "SCOPED INSTALLED PRODUCT PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
