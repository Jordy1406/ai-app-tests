"""/chat behaviour that depends on the model: run with a majority vote (VOTES, default 3)."""

import pytest

from contracts import REFUSAL_TEXT, ChatResponse
from voting import majority


def ask(api, question: str) -> ChatResponse:
    resp = api.post("/chat", data={"message": question})
    assert resp.status == 200, resp.text()
    return ChatResponse.model_validate(resp.json())


@pytest.mark.parametrize("question,expected_title", [
    ("Apa perbedaan saham biasa dan saham preferen?", "Saham"),
    ("Apa itu waran?", "Waran"),
])
def test_in_scope_question_is_answered_from_the_right_document(api, question, expected_title):
    def check():
        out = ask(api, question)
        assert not out.refused, f"refused: {out.answer[:80]}"
        titles = [s.title for s in out.sources]
        assert expected_title in titles, f"expected a source titled {expected_title!r}, got {titles}"

    vote = majority(f"in-scope: {question}", check)
    assert vote.passed, vote.summary()


@pytest.mark.parametrize("question", [
    "Bagaimana resep nasi goreng?",
    "Siapa presiden Amerika pertama?",
])
def test_out_of_scope_question_is_refused(api, question):
    def check():
        out = ask(api, question)
        assert out.refused, f"answered instead of refusing: {out.answer[:100]!r} sources={[s.title for s in out.sources]}"
        assert out.answer == REFUSAL_TEXT

    vote = majority(f"out-of-scope: {question}", check)
    assert vote.passed, vote.summary()
