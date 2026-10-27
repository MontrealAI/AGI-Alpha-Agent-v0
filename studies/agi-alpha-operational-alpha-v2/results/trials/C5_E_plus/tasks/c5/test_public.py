import hashlib
import unittest
from engine import audit


def sample_packet():
    return {
        "version": 1, "initial_credits": {"alpha": 100}, "capacity": 5,
        "jobs": [{"owner": "alpha", "job": "job-a", "cap": 40, "cost": 2, "deps": [], "artifact": "report"}],
        "journal_events": [
            {"id": "reserve-a", "job": "job-a", "owner": "alpha", "kind": "reserve", "amount": 40},
            {"id": "settle-a", "job": "job-a", "owner": "alpha", "kind": "settle", "amount": 12}],
        "schedule_commands": [
            {"action": "claim", "owner": "alpha", "job": "job-a", "lease": "lease-a"},
            {"action": "finish", "owner": "alpha", "job": "job-a", "lease": "lease-a", "success": True}],
        "artifacts": [{"owner": "alpha", "upload": "report", "size": 3,
                       "digest": hashlib.sha256(b"abc").hexdigest(), "state": "committed", "cells": [97, 98, 99]}],
        "settlements": [{"request": "settlement:job-a", "operations": [{"from": "alpha", "to": "__usage__", "amount": 12}],
                         "expected": {"alpha": 0, "__usage__": 0}}],
    }


class Smoke(unittest.TestCase):
    def test_delivery(self):
        result = audit(sample_packet())
        self.assertEqual(result["decision"], "release")
        self.assertEqual(result["summary"]["usage_sink"], 12)
        self.assertEqual(result["summary"]["artifact_bytes"], 3)


if __name__ == "__main__":
    unittest.main()
