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
