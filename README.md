# ai-app-tests

Test suite for **[FinAssist ID](https://github.com/Jordy1406/finassist-app)** — a Bahasa Indonesia RAG assistant and
tool-using trading agent on a mock broker. The point of this repo: testing an AI application end to end even though
its output is not deterministic. Strategy: **[docs/STRATEGY.md](docs/STRATEGY.md)**.

> Status: P1, week 1. Contract tests and the first live behaviour tests are in place (19 tests).
> Rule-based assertions (P1-03), the LLM-as-judge assertion (P1-04), flakiness measurement (P1-05) and CI (P1-06) are next.

## How the tests work

| Layer | File | What it checks | Runs |
|---|---|---|---|
| L1 Contract | `tests/test_contract.py` | `/health`, response shapes of `/chat`, `/agent`, `/log`, `/state` (Pydantic, unknown fields fail), 422 on bad input, 404 on unknown sessions | once (deterministic) |
| L2/L4 Behaviour | `tests/test_chat.py` | in-scope questions answered from the expected document; out-of-scope questions refused with the fixed text | **3× majority vote** |
| L4 Agent | `tests/test_agent.py` | an order is parked until "ya", the executed order equals the pending one, "batal" leaves nothing, no order executes in the same message (incl. an injection attempt) | 3× vote; the same-message check runs once |

- **API client:** Playwright's `APIRequestContext` (no browser needed; FinAssist ID has no UI yet, so there is no UI test).
- **Contracts** (`tests/contracts.py`) are written from FinAssist ID's README spec, not copied from observed output.
- **Majority vote** (`tests/voting.py`): a model-dependent check runs `VOTES` times (default 3) and passes when more than
  half pass. Every run's outcome is appended to `reports/votes.jsonl`, which gives the flaky rate.
- Agent assertions read the tool-call log and broker state, never the wording of the reply.

## Run

```bash
# target (in ../finassist-app); BROKER_ALWAYS_OPEN lets orders through outside 09:00-15:50 WIB
BROKER_ALWAYS_OPEN=true docker compose up -d

# tests
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest                                                 # BASE_URL=http://localhost:8000, VOTES=3
```

All tests skip with a message if the target is not reachable; order tests skip if the target's market is closed.

## Results

Run on 2026-11-08 against finassist-app `1c57ca0` (llama3.2:3b, temperature 0, laptop GPU):

| Number | Value | Source |
|---|---|---|
| Tests passing | **19 / 19** | `pytest` → `19 passed in 66.34s` |
| Model-dependent cases | 7 cases × 3 votes = 21 runs, all passed | `reports/votes.jsonl` |
| Flaky rate | **0 / 7** cases on this run | `reports/votes.jsonl` (cases whose 3 outcomes disagree) |
| Orders executed without a separate confirmation | 0 (2 probes incl. an injection attempt) | `test_order_is_never_executed_in_the_same_message` |

The question sets are still small; P1-05 repeats the suite 5 times and reports the flaky rate over more cases.

## Roadmap

- [x] P1-01 Test strategy ([docs/STRATEGY.md](docs/STRATEGY.md))
- [x] P1-02 Playwright API client, contracts, first live tests
- [ ] P1-03 Rule-based assertions: disclaimer on advice questions, sources, prices equal the mock broker, no prompt leak
- [ ] P1-04 LLM-as-judge assertion (Claude) with reasons in the report
- [ ] P1-05 Flakiness: 5 repeated runs, flaky rate
- [ ] P1-06 CI: contract and rule tests on recorded responses per PR, live suite nightly (blocked by GitHub billing)
- [ ] P1-07 Three model-behaviour bug reports in `docs/bugs/`
