"""Offline decision reference. No I/O, execution, persistence or native hooks."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Budget:
    limit: int
    used: int
    elapsed: float
    seconds: float
    now: float
    deadline: float

    def validate(self):
        if type(self.limit) is not int or type(self.used) is not int:
            raise ValueError("integer counters required")
        if self.limit <= 0 or not 0 <= self.used <= self.limit:
            raise ValueError("invalid counters")
        for v in (self.elapsed, self.seconds, self.now, self.deadline):
            if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
                raise ValueError("finite nonnegative times required")
        if self.seconds <= 0:
            raise ValueError("positive time budget required")

    def exhausted(self):
        return self.elapsed >= self.seconds or self.now >= self.deadline


def flags(*values):
    if any(type(v) is not bool for v in values):
        raise ValueError("explicit booleans required")


def retry(budget, *, outcome, authorized, identity_current, replay_safe,
          handle_known=False, queries_used=0, query_limit=1):
    """Decide only; caller reserves/persists counters before acting.

    outcome is trusted evidence from caller, not proof produced here.
    Success may be reported after deadline only for a previously accepted result.
    """
    budget.validate()
    flags(authorized, identity_current, replay_safe, handle_known)
    if outcome not in {"NOT_STARTED", "SUCCESS", "TRANSIENT_FAILURE", "REJECTED", "UNKNOWN"}:
        raise ValueError("unknown outcome")
    if type(query_limit) is not int or type(queries_used) is not int or not 0 <= queries_used <= query_limit:
        raise ValueError("invalid query budget")
    if (outcome == "NOT_STARTED") != (budget.used == 0):
        raise ValueError("outcome inconsistent with attempts")
    if not identity_current:
        return "HOLD"
    if outcome == "SUCCESS":
        return "DONE"
    if not authorized or outcome == "REJECTED" or budget.exhausted():
        return "STOP"
    if outcome == "UNKNOWN":
        return "QUERY" if handle_known and queries_used < query_limit else "HOLD"
    if budget.used == budget.limit:
        return "STOP"
    if outcome == "TRANSIENT_FAILURE" and not replay_safe:
        return "HOLD"
    return "ATTEMPT"


def convergence(budget, *, candidate, evidence_candidate, required, passed,
                open_findings, next_action, authorized, side_effect_unknown,
                evidence_elapsed, evidence_at):
    """Decide from explicit simulated workflow facts; no automatic remediation.

    The caller must provide actual candidate-bound review and verification facts.
    A boolean or this decision cannot prove findings were independently closed.
    """
    budget.validate()
    flags(authorized, side_effect_unknown)
    for value in (candidate, evidence_candidate):
        if not isinstance(value, str) or not value:
            raise ValueError("candidate identities required")
    for values in (required, passed, open_findings):
        if not isinstance(values, (list, tuple)) or any(not isinstance(v, str) or not v for v in values) or len(set(values)) != len(values):
            raise ValueError("unique named evidence required")
    if not required or not set(passed) <= set(required):
        raise ValueError("invalid acceptance scope")
    if next_action not in {"none", "fix", "verify", "diagnose"}:
        raise ValueError("unknown next action")
    for value in (evidence_elapsed, evidence_at):
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("finite evidence times required")
    if budget.used == 0 or evidence_elapsed > budget.elapsed or evidence_at > budget.now:
        raise ValueError("evidence inconsistent with consumed round/time")
    if side_effect_unknown or candidate != evidence_candidate:
        return "HOLD"
    in_time = evidence_elapsed <= budget.seconds and evidence_at <= budget.deadline
    if set(passed) == set(required) and not open_findings and in_time:
        return "DONE"
    if not authorized or budget.exhausted() or budget.used == budget.limit:
        return "STOP"
    return "NEXT_ROUND" if next_action != "none" else "STOP"
