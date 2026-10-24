# SPDX-License-Identifier: Apache-2.0
"""Small bounded load samples of the installed standalone fixed worker, without approval."""

import argparse
import concurrent.futures
import copy
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
import os
import pathlib
import resource
import statistics
import subprocess
import sys
import threading
import time
import uuid

from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor import workbench


def tree_rss_bytes():
    """Linux RSS sample of this process and observed descendants; shared pages may be counted twice."""
    parents, rss = {}, {}
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text().rsplit(") ", 1)[1].split()
            parents[int(entry.name)] = int(stat[1])
            rss[int(entry.name)] = int(stat[21]) * os.sysconf("SC_PAGE_SIZE")
        except (OSError, IndexError, ValueError):
            continue
    # /proc can expose host PIDs while os.getpid() returns a namespace PID.
    proc_pid = int(pathlib.Path("/proc/self/stat").read_text().split(" ", 1)[0])
    descendants = {proc_pid}
    while True:
        expanded = descendants | {pid for pid, parent in parents.items() if parent in descendants}
        if expanded == descendants:
            return sum(rss.get(pid, 0) for pid in descendants)
        descendants = expanded


def cpu_seconds():
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime


def storage_bytes(home):
    return sum(path.stat().st_size for path in home.rglob("*") if path.is_file())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    module = pathlib.Path(workbench.__file__).resolve()
    assert module.is_relative_to(pathlib.Path(sys.prefix).resolve()), str(module)
    assert version("alpha-factory-v1") == "1.42.0"
    assert (
        hashlib.sha256(module.read_bytes()).hexdigest()
        == "87ad9f365ebf1b5c1e93edc275e6fe933b6c247e51b848b52dc66c34344a8492"
    )
    root = args.output.resolve()
    root.mkdir(mode=0o700)
    spec = workbench.invoke({"operation": "example", "family": "numerical"})
    samples = []
    for count, concurrency in ((1, 1), (4, 2), (16, 4), (64, 4)):
        home = root / ("load-" + str(count))
        journal = Journal.initialize(home)
        baseline_storage = storage_bytes(home)
        baseline_rss = tree_rss_bytes()
        peak_rss = [baseline_rss]
        stop = threading.Event()

        def monitor():
            while not stop.wait(0.02):
                peak_rss[0] = max(peak_rss[0], tree_rss_bytes())

        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        started, cpu = time.monotonic(), cpu_seconds()

        def execute(index):
            begin = time.monotonic()
            run_id = str(uuid.uuid4())
            try:
                record = workbench.execute(home, copy.deepcopy(spec), run_id)
                assert record["state"] == "review" and record["result_digest"]
                return {
                    "index": index,
                    "run_id": run_id,
                    "state": record["state"],
                    "result_digest": record["result_digest"],
                    "passed": True,
                    "seconds": time.monotonic() - begin,
                }
            except Exception as error:
                return {
                    "index": index,
                    "run_id": run_id,
                    "passed": False,
                    "error_type": type(error).__name__,
                    "error_message": str(error)[:600],
                    "seconds": time.monotonic() - begin,
                }

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            remaining = iter(range(count))
            active = {pool.submit(execute, next(remaining)) for _ in range(min(count, concurrency))}
            while active:
                done, active = concurrent.futures.wait(active, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    results.append(future.result())
                    index = next(remaining, None)
                    if index is not None:
                        active.add(pool.submit(execute, index))
        elapsed = time.monotonic() - started
        consumed_cpu = cpu_seconds() - cpu
        stop.set()
        monitor_thread.join()
        verification_started = time.monotonic()
        checkpoint = journal.verify()
        verification_seconds = time.monotonic() - verification_started
        latencies = sorted(result["seconds"] for result in results)
        errors = sum(not result["passed"] for result in results)
        samples.append(
            {
                "missions": count,
                "max_in_flight": concurrency,
                "unbounded_submission_queue": False,
                "elapsed_seconds": elapsed,
                "successful_missions_per_second": (count - errors) / elapsed,
                "latency_seconds": {
                    "median": statistics.median(latencies),
                    "p95": latencies[math.ceil(0.95 * count) - 1],
                    "maximum": max(latencies),
                },
                "errors": errors,
                "error_rate": errors / count,
                "sampled_process_tree_rss": {
                    "baseline_bytes": baseline_rss,
                    "peak_bytes": peak_rss[0],
                    "growth_bytes": peak_rss[0] - baseline_rss,
                    "interval_seconds": 0.02,
                },
                "cpu_seconds_python_and_waited_children": consumed_cpu,
                "max_single_completed_child_rss_process_lifetime_bytes": resource.getrusage(
                    resource.RUSAGE_CHILDREN
                ).ru_maxrss
                * 1024,
                "max_python_rss_process_lifetime_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                "retained_storage_bytes": storage_bytes(home),
                "storage_growth_bytes": storage_bytes(home) - baseline_storage,
                "journal_verification_seconds": verification_seconds,
                "journal_checkpoint": checkpoint,
                "operator_interventions_during_sample": 0,
                "results_awaiting_local_review": count - errors,
                "results": sorted(results, key=lambda result: result["index"]),
            }
        )
        print(
            json.dumps({"missions": count, "concurrency": concurrency, "errors": errors, "seconds": elapsed}),
            flush=True,
        )
    receipt = {
        "schema": "agialpha.standalone-installed-load-sample.v1",
        "commit": args.commit,
        "version": "1.42.0",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "node": subprocess.check_output(["node", "--version"], text=True).strip(),
        "module": str(module),
        "python": sys.version,
        "samples": samples,
        "passed": all(sample["errors"] == 0 for sample in samples),
        "scope": "Synthetic numerical example on one local installed Alpha journal per level; existing worker/locks only",
        "limits": [
            "One sample per load level; not a general scale or comparative performance qualification",
            "RSS is sampled, may miss peaks and double-count shared pages; Linux only",
            "rusage high-water values cover process lifetime and individual children, not a simultaneous combined peak",
            "Submission count and in-flight work are finite; no Fleet, provider, contract or settlement adapter",
            "Every successful result remains awaiting local review; no independent admission or production authority",
        ],
        "unknown_costs": ["human_review_seconds", "allocated_machine_price", "external_service_cost"],
        "authority": [],
        "full_harness_qualification": False,
        "four_installed_tuple_qualification": False,
    }
    (root / "load-samples.json").write_text(json.dumps(receipt, indent=2) + "\n")
    assert receipt["passed"], "Load sample failed; inspect the retained error counts"


if __name__ == "__main__":
    main()
