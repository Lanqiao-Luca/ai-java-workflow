"""Offline reference tests: no model, service, subprocess or build invocation."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.loop_policy import Budget, retry


class RetryCases(unittest.TestCase):
    def setUp(self):
        self.b = Budget(2, 1, 1, 10, 101, 110)
        self.f = dict(outcome="TRANSIENT_FAILURE", authorized=True,
                      identity_current=True, replay_safe=True)

    def decide(self, b=None, **changes):
        return retry(b or self.b, **dict(self.f, **changes))

    def test_read_only_recovery_trace(self):
        b = replace(self.b, used=0, elapsed=0, now=100)
        self.assertEqual(self.decide(b, outcome="NOT_STARTED"), "ATTEMPT")
        # Caller reserves first attempt, receives transient failure.
        self.assertEqual(self.decide(), "ATTEMPT")
        # Caller reserves second attempt, receives actual success.
        self.assertEqual(self.decide(replace(self.b, used=2), outcome="SUCCESS"), "DONE")

    def test_attempt_limit(self):
        self.assertEqual(self.decide(replace(self.b, used=2)), "STOP")

    def test_deadline(self):
        self.assertEqual(self.decide(replace(self.b, now=110)), "STOP")

    def test_time_limit(self):
        self.assertEqual(self.decide(replace(self.b, elapsed=10)), "STOP")

    def test_permission(self):
        self.assertEqual(self.decide(authorized=False), "STOP")

    def test_rejection(self):
        self.assertEqual(self.decide(outcome="REJECTED"), "STOP")

    def test_unknown_never_replays(self):
        self.assertEqual(self.decide(outcome="UNKNOWN"), "HOLD")
        self.assertEqual(self.decide(outcome="UNKNOWN", handle_known=True), "QUERY")
        self.assertEqual(self.decide(outcome="UNKNOWN", handle_known=True, queries_used=1), "HOLD")

    def test_query_allowed_after_attempt_cap(self):
        self.assertEqual(self.decide(replace(self.b, used=2), outcome="UNKNOWN", handle_known=True), "QUERY")

    def test_query_obeys_clock(self):
        self.assertEqual(self.decide(replace(self.b, now=110), outcome="UNKNOWN", handle_known=True), "STOP")

    def test_unsafe_replay(self):
        self.assertEqual(self.decide(replay_safe=False), "HOLD")

    def test_identity_drift(self):
        self.assertEqual(self.decide(identity_current=False, outcome="SUCCESS"), "HOLD")

    def test_invalid_contract(self):
        for b in [replace(self.b, limit=True), replace(self.b, used=3), replace(self.b, elapsed=float("nan")), replace(self.b, seconds=0)]:
            with self.subTest(b=b), self.assertRaises(ValueError): self.decide(b)
        for c in [dict(outcome="made-up"), dict(authorized="yes"), dict(queries_used=2), dict(outcome="NOT_STARTED")]:
            with self.subTest(c=c), self.assertRaises(ValueError): self.decide(**c)


if __name__ == "__main__":
    unittest.main(verbosity=2)
