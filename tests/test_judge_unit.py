"""Offline tests of the judge plumbing with a fake Claude client (no API key, no network)."""

import json

import pytest

import judge as j


class _Resp:
    def __init__(self, parsed, stop_reason="end_turn"):
        self.parsed_output, self.stop_reason = parsed, stop_reason


class FakeClient:
    def __init__(self, resp):
        self.resp, self.sent = resp, None
        outer = self

        class _Messages:
            def parse(self, **kwargs):
                outer.sent = kwargs
                return outer.resp

        self.messages = _Messages()


@pytest.fixture(autouse=True)
def tiny_index(tmp_path, monkeypatch):
    index = {"chunks": [{"id": "wiki_waran#000", "title": "Waran", "section": "Waran",
                         "text": "Waran adalah hak untuk membeli saham dengan harga yang telah ditentukan."}]}
    path = tmp_path / "index.json"
    path.write_text(json.dumps(index), encoding="utf-8")
    monkeypatch.setattr(j, "INDEX_PATH", path)
    monkeypatch.setattr(j, "LOG_PATH", tmp_path / "judge.jsonl")
    j.chunk_texts.cache_clear()
    yield
    j.chunk_texts.cache_clear()


def test_request_carries_rubric_schema_and_cited_text():
    fake = FakeClient(_Resp(j.Verdict(relevance=5, support=5, reason="ok")))
    v = j.judge("Apa itu waran?", "Waran adalah hak membeli saham.", ["wiki_waran#000"], client=fake)
    assert v.passed()
    assert fake.sent["model"] == "claude-opus-5-5"
    assert fake.sent["output_format"] is j.Verdict
    assert fake.sent["system"] == j.RUBRIC
    assert "temperature" not in fake.sent                      # rejected by claude-opus-5-5
    prompt = fake.sent["messages"][0]["content"]
    assert "Waran adalah hak untuk membeli saham" in prompt and "QUESTION:\nApa itu waran?" in prompt


@pytest.mark.parametrize("rel,sup,passed", [(5, 5, True), (4, 4, True), (5, 3, False), (3, 5, False)])
def test_threshold_applies_to_both_scales(rel, sup, passed):
    assert j.Verdict(relevance=rel, support=sup, reason="").passed() is passed


def test_verdict_and_reason_are_logged():
    fake = FakeClient(_Resp(j.Verdict(relevance=4, support=2, reason="claim X not in source")))
    j.judge("q", "a", ["wiki_waran#000"], client=fake, label="unit")
    row = json.loads(j.LOG_PATH.read_text(encoding="utf-8").strip())
    assert row["reason"] == "claim X not in source" and row["passed"] is False and row["label"] == "unit"


def test_refusal_is_inconclusive_not_a_score():
    with pytest.raises(j.JudgeUnavailable, match="refusal"):
        j.judge("q", "a", ["wiki_waran#000"], client=FakeClient(_Resp(None, stop_reason="refusal")))


def test_out_of_range_verdict_is_rejected():
    with pytest.raises(j.JudgeUnavailable, match="invalid"):
        j.judge("q", "a", ["wiki_waran#000"], client=FakeClient(_Resp(j.Verdict(relevance=7, support=5, reason=""))))


def test_unknown_chunk_id_is_reported():
    with pytest.raises(j.JudgeUnavailable, match="not in the index"):
        j.judge("q", "a", ["wiki_sukuk#000"], client=FakeClient(_Resp(None)))
