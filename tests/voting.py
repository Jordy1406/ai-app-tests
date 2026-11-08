"""Majority vote for model-dependent checks (docs/STRATEGY.md §5).

A check runs VOTES times (default 3) and passes when more than half of the runs pass. Every run's outcome is kept so
the report shows disagreement, and flaky cases (runs that disagree) are recorded for the flaky rate.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

VOTES = int(os.getenv("VOTES", "3"))
FLAKY_LOG = Path(os.getenv("FLAKY_LOG", "reports/votes.jsonl"))


@dataclass
class Vote:
    name: str
    outcomes: list[bool] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return sum(self.outcomes) * 2 > len(self.outcomes)

    @property
    def flaky(self) -> bool:
        return len(set(self.outcomes)) > 1

    def summary(self) -> str:
        marks = "".join("✓" if o else "✗" for o in self.outcomes)
        detail = f"; failures: {self.errors}" if self.errors else ""
        return f"{self.name}: {marks} ({sum(self.outcomes)}/{len(self.outcomes)}){detail}"


def majority(name: str, check: Callable[[], None], votes: int = VOTES) -> Vote:
    """Run `check` `votes` times. `check` raises AssertionError on a failed run."""
    vote = Vote(name)
    for _ in range(votes):
        try:
            check()
            vote.outcomes.append(True)
        except AssertionError as exc:
            vote.outcomes.append(False)
            vote.errors.append(str(exc).splitlines()[0][:200])
    FLAKY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with FLAKY_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"name": name, "outcomes": vote.outcomes, "passed": vote.passed, "flaky": vote.flaky,
                            "errors": vote.errors}, ensure_ascii=False) + "\n")
    return vote
