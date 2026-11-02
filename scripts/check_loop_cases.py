"""Offline reference tests: no model, service, subprocess or build invocation."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.loop_policy import Budget, retry, convergence
import json


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


class ConvergenceCases(unittest.TestCase):
    def setUp(self):
        self.b = Budget(2, 1, 5, 60, 1005, 1060)
        self.f = dict(candidate="candidate-a", evidence_candidate="candidate-a",
                      required=["save", "reject"], passed=["save"],
                      open_findings=["F-1"], next_action="fix", authorized=True,
                      side_effect_unknown=False, evidence_elapsed=5, evidence_at=1005)

    def decide(self, b=None, **changes):
        return convergence(b or self.b, **dict(self.f, **changes))

    def test_complete_trace(self):
        path = Path(__file__).resolve().parents[1] / "loops/examples/review-trace.json"
        trace = json.loads(path.read_text())["steps"]
        self.assertEqual(len(trace), 3)
        self.assertEqual([s["budget"]["used"] for s in trace], [1, 2, 2])
        self.assertEqual(len({s["budget"]["deadline"] for s in trace}), 1)
        for step in trace:
            with self.subTest(step=step["name"]):
                self.assertEqual(convergence(Budget(**step["budget"]), **step["facts"]), step["expected"])

    def test_continue_with_concrete_action(self):
        self.assertEqual(self.decide(), "NEXT_ROUND")

    def test_missing_acceptance_is_incomplete(self):
        self.assertEqual(self.decide(open_findings=[], next_action="none"), "STOP")

    def test_open_finding_is_incomplete(self):
        self.assertEqual(self.decide(passed=["save", "reject"], next_action="none"), "STOP")

    def test_candidate_drift(self):
        self.assertEqual(self.decide(candidate="candidate-b", passed=["save", "reject"], open_findings=[]), "HOLD")

    def test_no_progress(self):
        self.assertEqual(self.decide(next_action="none"), "STOP")

    def test_round_limit(self):
        self.assertEqual(self.decide(replace(self.b, used=2)), "STOP")

    def test_elapsed_limit(self):
        self.assertEqual(self.decide(replace(self.b, elapsed=60)), "STOP")

    def test_deadline(self):
        self.assertEqual(self.decide(replace(self.b, now=1060)), "STOP")

    def test_no_authority(self):
        self.assertEqual(self.decide(authorized=False), "STOP")

    def test_unknown_side_effect(self):
        self.assertEqual(self.decide(side_effect_unknown=True, passed=["save", "reject"], open_findings=[]), "HOLD")

    def test_valid_completion_at_limit_needs_no_new_action(self):
        self.assertEqual(self.decide(replace(self.b, used=2, elapsed=60, now=1060), passed=["save", "reject"], open_findings=[]), "DONE")

    def test_late_evidence_cannot_complete(self):
        self.assertEqual(self.decide(replace(self.b, elapsed=61, now=1061), passed=["save", "reject"], open_findings=[], evidence_elapsed=61, evidence_at=1061), "STOP")

    def test_old_candidate_does_not_refresh_budget(self):
        self.assertEqual(self.decide(replace(self.b, used=2), candidate="candidate-b"), "HOLD")
        self.assertEqual(self.decide(replace(self.b, used=2), candidate="candidate-b", evidence_candidate="candidate-b"), "STOP")

    def test_invalid_contract(self):
        for c in [dict(required=[]), dict(passed=["other"]), dict(open_findings=["F-1", "F-1"]), dict(evidence_at=1006), dict(side_effect_unknown="no"), dict(evidence_elapsed=float("inf"))]:
            with self.subTest(c=c), self.assertRaises(ValueError):self.decide(**c)


if __name__ == "__main__":
    unittest.main(verbosity=2)
