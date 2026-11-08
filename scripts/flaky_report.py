"""P1-05: run the suite RUNS times with VOTES=1 and report tests whose outcome changes between runs.

VOTES=1 matters: the in-test majority vote would hide single-run flakiness, which is what we want to measure here.

Usage:  python scripts/flaky_report.py            # RUNS=5 by default
Output: reports/flaky/run_<n>.xml (JUnit per run), reports/flaky/summary.json, reports/flaky/summary.md
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

RUNS = int(os.getenv("RUNS", "5"))
OUT = Path("reports/flaky")


def outcome(case: ET.Element) -> str:
    if case.find("skipped") is not None:
        msg = case.find("skipped").get("message", "")
        return "xfail" if "xfail" in case.find("skipped").get("type", "") or msg.startswith("R") else "skipped"
    if case.find("failure") is not None or case.find("error") is not None:
        return "failed"
    return "passed"


def run_once(i: int) -> tuple[dict[str, str], float]:
    xml = OUT / f"run_{i}.xml"
    t0 = time.time()
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}"],
                   env={**os.environ, "VOTES": "1"}, check=False)
    seconds = time.time() - t0
    results = {}
    for case in ET.parse(xml).getroot().iter("testcase"):
        results[f"{case.get('classname')}::{case.get('name')}"] = outcome(case)
    return results, seconds


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    per_test: dict[str, list[str]] = defaultdict(list)
    durations = []
    for i in range(1, RUNS + 1):
        print(f"--- run {i}/{RUNS}", flush=True)
        results, seconds = run_once(i)
        durations.append(round(seconds, 1))
        for name, res in results.items():
            per_test[name].append(res)

    flaky = {n: o for n, o in per_test.items() if len(set(o)) > 1}
    model_dependent = [n for n in per_test if not n.startswith(("tests.test_contract", "tests.test_assertions_unit"))]
    summary = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runs": RUNS, "votes_per_case": 1, "durations_s": durations,
        "tests": len(per_test), "model_dependent_tests": len(model_dependent),
        "flaky_tests": len(flaky),
        "flaky_rate_all": round(len(flaky) / len(per_test), 4) if per_test else 0,
        "flaky_rate_model_dependent": round(len([n for n in flaky if n in model_dependent]) / len(model_dependent), 4)
        if model_dependent else 0,
        "flaky": flaky,
        "always_failed": [n for n, o in per_test.items() if set(o) == {"failed"}],
        "outcomes": dict(per_test),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# Flakiness report — {RUNS} runs, VOTES=1", "",
             f"- Tests: {summary['tests']} ({summary['model_dependent_tests']} model-dependent)",
             f"- Flaky: {summary['flaky_tests']} → rate {summary['flaky_rate_all']:.1%} of all, "
             f"{summary['flaky_rate_model_dependent']:.1%} of model-dependent",
             f"- Run durations (s): {durations}", "", "| Test | Outcomes per run |", "|---|---|"]
    lines += [f"| `{n}` | {' · '.join(o)} |" for n, o in flaky.items()] or ["| (none) | |"]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
