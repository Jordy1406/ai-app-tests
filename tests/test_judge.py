"""L3 judge assertions against the live target (P1-04). Costs API credits: run with `pytest -m judge`.

Each case gets one live /chat answer, then Claude judges it against the text of the cited chunks.
"""

import os

import pytest

import judge as j
from contracts import ChatResponse

pytestmark = [
    pytest.mark.judge,
    pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set (see .env.example)"),
]


def answer(api, question: str) -> ChatResponse:
    resp = api.post("/chat", data={"message": question})
    assert resp.status == 200, resp.text()
    return ChatResponse.model_validate(resp.json())


@pytest.mark.parametrize("question", [
    "Apa perbedaan saham biasa dan saham preferen?",
    "Apa itu waran?",
    "Apa tugas OJK?",
    pytest.param("Apa itu sukuk?", marks=pytest.mark.xfail(
        strict=True, reason="R01 / BUG-002: answer cites a statute chunk that never mentions sukuk")),
])
def test_answer_is_relevant_and_supported_by_its_sources(api, question):
    out = answer(api, question)
    assert not out.refused, f"refused: {out.answer[:80]!r}"
    v = j.judge(question, out.answer, [s.id for s in out.sources], label="grounding")
    assert v.passed(), f"relevance={v.relevance} support={v.support}: {v.reason}"


def test_judge_is_consistent_on_the_same_answer(api):
    """Same answer judged 3 times: the pass/fail verdict must not flip (scores are reported, not required equal)."""
    question = "Apa perbedaan saham biasa dan saham preferen?"
    out = answer(api, question)
    verdicts = [j.judge(question, out.answer, [s.id for s in out.sources], label="consistency") for _ in range(3)]
    scores = [(v.relevance, v.support) for v in verdicts]
    assert len({v.passed() for v in verdicts}) == 1, f"judge flipped between pass and fail: {scores}"
