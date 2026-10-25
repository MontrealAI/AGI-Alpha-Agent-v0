# SPDX-License-Identifier: Apache-2.0
"""Development fault injections for the bounded local custody/accounting component."""

from __future__ import annotations

import hashlib
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from custody import Custody, CustodyError, digest


def main() -> None:
    root = Path(__file__).parent
    rows = []
    source = hashlib.sha256((root / "custody.py").read_bytes()).hexdigest()
    accepted = {"valid": True, "qualified": True, "result": {"residual": "1e-14"}}
    failed = {"valid": False, "qualified": False, "error": "counterexample"}
    request = digest({"task": "development"})
    deps = {"scipy": "1.17.0", "checker": "separate-development-checker"}

    def expect(code, function):
        try:
            function()
            raise AssertionError("Expected " + code)
        except CustodyError as error:
            assert str(error) == code, (code, str(error))

    with tempfile.TemporaryDirectory(prefix="earned-custody-") as temporary:
        base = Path(temporary)

        def fresh(name, **kwargs):
            return Custody(base / name, source, 100, 20, 30, dependencies=deps, **kwargs)

        with fresh("duplicate") as c:
            assert c.reserve("service-1", "service", 20, request)["execute"]
            first = c.commit("service-1", 4, accepted)
            second = c.reserve("service-1", "service", 20, request)
            assert not second["execute"] and second["receipt"] == accepted
            assert c.status()["accounts"]["service"]["spent_us"] == 4000
            expect("REQUEST_BINDING_CHANGED", lambda: c.reserve("service-1", "service", 20, "1" * 64))
            checkpoint = c.checkpoint()
        with fresh("duplicate") as c:
            duplicate = c.reserve("service-1", "service", 20, request)
            assert duplicate["receipt_digest"] == first["receipt_digest"] and not duplicate["execute"]
            assert c.checkpoint() == checkpoint
        rows.append({"case": "lost_ack_restart_and_duplicate_no_repeat", "passed": True})

        with fresh("pending") as c:
            c.reserve("unclean", "improvement", 12, request)
        with fresh("pending") as c:
            recovered = c.reserve("unclean", "improvement", 12, request)
            assert recovered["status"] == "QUARANTINED" and not recovered["execute"]
            assert c.status()["accounts"]["improvement"]["spent_us"] == 12000
            assert recovered["actual_cpu_us"] is None
        rows.append({"case": "pending_restart_charges_ceiling_and_quarantines", "passed": True})

        with fresh("tamper") as c:
            c.reserve("a", "service", 10, request)
            c.commit("a", 2, accepted)
        journal = base / "tamper" / "journal.jsonl"
        damaged = journal.read_text().replace('"1e-14"', '"forged"')
        journal.write_text(damaged)
        expect("JOURNAL_INTEGRITY", lambda: fresh("tamper"))
        rows.append({"case": "changed_receipt_rejected_by_journal", "passed": True})

        expect("DEPENDENCY_CHANGED", lambda: Custody(base / "duplicate", source, 100, 20, 30, dependencies={"scipy": "changed"}))
        rows.append({"case": "changed_dependency_refused", "passed": True})
        expect("SOURCE_CHANGED", lambda: Custody(base / "duplicate", "2" * 64, 100, 20, 30, dependencies=deps))
        rows.append({"case": "changed_source_refused", "passed": True})

        with fresh("budgets") as c:
            before = c.status()["accounts"]["service"]
            expect("ACCOUNT_EXHAUSTED", lambda: c.reserve("too-large", "improvement", 21, request))
            assert c.status()["accounts"]["service"] == before
            c.reserve("research-fails", "improvement", 20, request)
            c.commit("research-fails", 20, failed)
            expect("ACCOUNT_EXHAUSTED", lambda: c.reserve("retry", "improvement", 1, request))
            assert c.status()["accounts"]["service"] == before
            assert c.reserve("delivery", "service", 100, request)["execute"]
            c.commit("delivery", 5, accepted)
        rows.append({"case": "failed_research_cannot_borrow_service_budget", "passed": True})

        with fresh("stop") as c:
            initial = c.checkpoint()
            c.stop("test")
            expect("STOPPED", lambda: c.reserve("a", "service", 10, request))
        with fresh("stop") as c:
            assert c.status()["stopped"]
            c.resume()
            assert c.status()["stop_generation"] == 1 and not c.status()["stopped"]
            expect("STALE_CHECKPOINT", lambda: c.verify_checkpoint(initial))
            c.reserve("a", "service", 10, request)
            c.commit("a", 1, accepted)
        rows.append({"case": "persistent_STOP_explicit_resume_preserves_history", "passed": True})
        rows.append({"case": "stale_external_checkpoint_rejected", "passed": True})

        with fresh("expiry", expires_at=time.time() - 1) as c:
            expect("EXPIRED_AUTHORITY", lambda: c.reserve("a", "service", 10, request))
            expect("EXPIRED_AUTHORITY", c.resume)
        rows.append({"case": "expired_authority_cannot_start_or_resume", "passed": True})
        with fresh("deadline", deadline_at=time.time() - 1) as c:
            expect("EXHAUSTED_DEADLINE", lambda: c.reserve("a", "service", 10, request))
        rows.append({"case": "expired_absolute_deadline_refused", "passed": True})

        expiry = time.time() + 100
        with fresh("expiry-during", expires_at=expiry) as c:
            c.reserve("a", "service", 10, request)
            with patch("custody.time.time", return_value=expiry + 1):
                r = c.commit("a", 3, accepted)
            assert r["acceptance_blocker"] == "EXPIRED_AUTHORITY" and not r["accepted"]
            assert c.status()["accounts"]["service"]["spent_us"] == 3000
        rows.append({"case": "expiry_during_work_preserves_cost_refuses_admission", "passed": True, "clock": "explicit development clock injection"})

        with fresh("assets") as c:
            c.reserve("parent", "improvement", 5, request)
            c.commit("parent", 2, accepted)
            c.retain_asset("parent", "3" * 64, "parent", scope="finite matrices")
            c.select_asset("3" * 64)
            c.reserve("child", "improvement", 5, request)
            c.commit("child", 2, accepted)
            c.retain_asset("child", "4" * 64, "child", scope="rank-two update", parent_digest="3" * 64)
            c.select_asset("4" * 64)
            c.rollback("3" * 64)
            c.reject_asset("4" * 64, "negative fresh result")
        with fresh("assets") as c:
            assert c.status()["selected_asset"] == "3" * 64
            expect("REJECTED_ASSET", lambda: c.select_asset("4" * 64))
            expect("REJECTED_ASSET", lambda: c.retain_asset("retry-child", "4" * 64, "child", scope="retry"))
            assert c.status()["assets"]["3" * 64]["authority"] == []
        rows.append({"case": "rollback_retains_incumbent_rejected_child_cannot_reenter", "passed": True})

        with fresh("earned") as c:
            expect("ACCOUNT_EXHAUSTED", lambda: c.reserve("unearned", "earned", 1, request))
            c.reserve("first", "service", 50, request)
            c.commit("first", 10, accepted)
            c.release_capacity("first", 25, evidence_digest=request)
            assert c.status()["accounts"]["earned"]["external_us"] == 0
            c.reserve("successor", "earned", 20, request)
            c.commit("successor", 18, accepted)
            expect("RELEASE_CAPACITY_EXCEEDED", lambda: c.release_capacity("first", 6))
            c.reserve("failure", "service", 5, request)
            c.commit("failure", 1, failed)
            expect("CAPACITY_REQUIRES_ACCEPTED_SERVICE", lambda: c.release_capacity("failure", 1))
            status = c.status()
            assert sum(a["available_us"] + a["spent_us"] + a["reserved_us"] for a in status["accounts"].values()) == 120000
        rows.append({"case": "real_quota_transfer_conserves_endowment_and_funds_successor", "passed": True})

        with fresh("overrun") as c:
            c.reserve("a", "improvement", 5, request)
            r = c.commit("a", 7, accepted)
            assert r["status"] == "OVERRUN" and not r["accepted"]
            assert c.status()["accounts"]["service"]["available_us"] == 100000
            assert c.status()["accounts"]["improvement"]["spent_us"] == 7000
            expect("TERMINAL_ACCOUNTING_HOLD", c.resume)
        rows.append({"case": "overrun_charged_without_cross_account_borrowing", "passed": True})

        with fresh("rollback-files") as c:
            old = (base / "rollback-files" / "journal.jsonl").read_bytes()
            c.stop()
        (base / "rollback-files" / "journal.jsonl").write_bytes(old)
        expect("STALE_OR_CORRUPT_CHECKPOINT", lambda: fresh("rollback-files"))
        rows.append({"case": "journal_rollback_against_separate_anchor_refused", "passed": True})

        with fresh("writer") as c:
            expect("ACTIVE_WRITER", lambda: fresh("writer"))
            c.reserve("bad-receipt", "service", 10, request)
            expect("INVALID_RECEIPT", lambda: c.commit("bad-receipt", 1, {"valid": False, "qualified": True}))
            assert c.status()["requests"]["bad-receipt"]["status"] == "PENDING"
        rows.append({"case": "exclusive_writer_and_invalid_receipt_fail_closed", "passed": True})

    record = {"scope": "development fault injections only; no numerical confirmation", "source_sha256": source,
        "tests": rows, "passed": len(rows), "limitations": [
            "CPU reservations do not physically preempt native calls; actual overruns are recorded and refused.",
            "Released quota is a reassignment of external service endowment, not money or proof of causal saving.",
            "Local unsigned journal/anchor share host control; independently retain checkpoints to detect whole-directory rollback.",
            "History/provenance never grants institutional proof status or production authority."]}
    destination = root / "development_custody_tests.json"
    destination.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"passed": len(rows), "source_sha256": source, "record": str(destination)}))


if __name__ == "__main__":
    main()
