"""LLM-as-judge for FinAssist ID answers (docs/STRATEGY.md, layer L3).

Claude grades one answer on two 1-5 scales against the text of the chunks the answer cites:
  relevance — does the answer address the question?
  support   — is every claim backed by the cited text (not by outside knowledge)?
An answer passes at THRESHOLD (4) on both. The verdict is a validated Pydantic object with a reason, and every verdict
is appended to reports/judge.jsonl so the report keeps the judge's reasoning.

The judge is a different model from the one under test (llama3.2:3b), which avoids self-grading. Design choices:
- `claude-opus-5-5` takes no `temperature`; consistency comes from the schema and a fixed rubric and is measured by
  judging the same answer several times (test_judge.py).
- No server-side model fallback: if Claude declines, the verdict is "inconclusive" instead of being graded silently by
  a different model, which would make scores incomparable.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

JUDGE_MODEL = os.getenv("JUDGE_MODEL", "claude-opus-5-5")
JUDGE_EFFORT = os.getenv("JUDGE_EFFORT", "medium")
THRESHOLD = int(os.getenv("JUDGE_THRESHOLD", "4"))
INDEX_PATH = Path(os.getenv("FINASSIST_INDEX", "../finassist-app/data/index.json"))
LOG_PATH = Path(os.getenv("JUDGE_LOG", "reports/judge.jsonl"))

RUBRIC = """You are grading an answer from FinAssist ID, a Bahasa Indonesia assistant that must answer ONLY from the
cited source text. Grade strictly; you are checking grounding, not writing style.

relevance (1-5): does the answer address the user's question?
  5 directly and completely · 4 mostly, minor gaps · 3 partly · 2 barely · 1 not at all

support (1-5): is every factual claim in the answer stated or directly implied by the CITED SOURCE TEXT below?
Use only the cited text. Do not give credit for claims that are true in general but absent from the cited text.
  5 every claim is in the cited text · 4 all key claims supported, a trivial detail is not · 3 some key claims
  unsupported · 2 most claims unsupported · 1 the cited text does not discuss the subject at all

reason: 1-3 sentences in English naming the unsupported or off-topic claims, if any."""


class Verdict(BaseModel):
    relevance: int = Field(description="1-5")
    support: int = Field(description="1-5")
    reason: str

    def passed(self, threshold: int = THRESHOLD) -> bool:
        return self.relevance >= threshold and self.support >= threshold


class JudgeUnavailable(RuntimeError):
    """The judge could not give a verdict (no API key, refusal, or invalid output)."""


@lru_cache(maxsize=1)
def chunk_texts() -> dict[str, str]:
    if not INDEX_PATH.exists():
        raise JudgeUnavailable(f"FinAssist ID index not found at {INDEX_PATH} (set FINASSIST_INDEX)")
    chunks = json.loads(INDEX_PATH.read_text(encoding="utf-8"))["chunks"]
    return {c["id"]: f"{c['title']} — {c['section']}\n{c['text']}" for c in chunks}


def build_prompt(question: str, answer: str, cited: list[str]) -> str:
    sources = "\n\n".join(f"[{i}] {t}" for i, t in enumerate(cited, start=1)) or "(no sources cited)"
    return f"QUESTION:\n{question}\n\nANSWER:\n{answer}\n\nCITED SOURCE TEXT:\n{sources}"


def make_client():
    import anthropic  # lazy: offline tests never need the SDK configured

    return anthropic.Anthropic()


def judge(question: str, answer: str, source_ids: list[str], client=None, label: str = "") -> Verdict:
    texts = chunk_texts()
    missing = [s for s in source_ids if s not in texts]
    if missing:
        raise JudgeUnavailable(f"cited chunks not in the index (index out of date?): {missing}")
    client = client or make_client()
    resp = client.messages.parse(
        model=JUDGE_MODEL,
        max_tokens=2000,
        system=RUBRIC,
        messages=[{"role": "user", "content": build_prompt(question, answer, [texts[s] for s in source_ids])}],
        output_format=Verdict,
        output_config={"effort": JUDGE_EFFORT},
    )
    if resp.stop_reason == "refusal":
        raise JudgeUnavailable("judge declined to grade (stop_reason=refusal)")
    verdict = resp.parsed_output
    if verdict is None or not (1 <= verdict.relevance <= 5 and 1 <= verdict.support <= 5):
        raise JudgeUnavailable(f"judge returned an invalid verdict: {verdict!r}")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "label": label,
                            "model": JUDGE_MODEL, "question": question, "answer": answer, "sources": source_ids,
                            **verdict.model_dump(), "passed": verdict.passed()}, ensure_ascii=False) + "\n")
    return verdict
