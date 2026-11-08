"""L1 contract tests: shapes and status codes. Deterministic; one run each."""

import pytest

from contracts import AgentLog, AgentResponse, AgentState, ChatResponse


def test_health_is_ok(api):
    resp = api.get("/health")
    assert resp.status == 200
    assert resp.json() == {"status": "ok"}


def test_chat_response_matches_contract(api):
    resp = api.post("/chat", data={"message": "Apa itu saham?"})
    assert resp.status == 200, resp.text()
    ChatResponse.model_validate(resp.json())


@pytest.mark.parametrize("payload", [{"message": ""}, {"message": "x" * 4001}, {}, {"msg": "salah field"}])
def test_chat_rejects_invalid_input_with_422(api, payload):
    assert api.post("/chat", data=payload).status == 422


def test_agent_response_log_and_state_match_contract(api):
    resp = api.post("/agent", data={"message": "Berapa saldo saya?"})
    assert resp.status == 200, resp.text()
    body = AgentResponse.model_validate(resp.json())
    AgentLog.model_validate(api.get(f"/agent/{body.session_id}/log").json())
    AgentState.model_validate(api.get(f"/agent/{body.session_id}/state").json())


@pytest.mark.parametrize("path", ["/agent/does-not-exist/log", "/agent/does-not-exist/state"])
def test_unknown_session_is_404(api, path):
    assert api.get(path).status == 404


def test_message_to_unknown_session_is_404(api):
    assert api.post("/agent", data={"message": "ya", "session_id": "does-not-exist"}).status == 404
