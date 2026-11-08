# Test Strategy for Non-Deterministic Systems — FinAssist ID

*Version 1 · 2026-11-08 · Owner: Jordy · Decisions marked **[D]** were made by the owner in P1-01.*

## 1. What we are testing and why it is hard

**System under test.** FinAssist ID (`finassist-app`), run with `docker compose up`:

- `POST /chat` — RAG over 30 public Indonesian capital-market documents; returns `{answer, sources[], refused}`.
- `POST /agent` — tool-using agent over a mock broker (`get_quote`, `get_portfolio`, `place_order`) with a confirmation
  gate; `GET /agent/{id}/log` and `/state` expose tool calls and broker state.
- Model: `llama3.2:3b` via Ollama at temperature 0 (development); Claude is available for final runs.

**Why ordinary assertions are not enough.** The same question can produce different wording, a different number of
sentences, or a different set of cited chunks. `assert answer == expected` fails on harmless variation and passes on
nothing useful. At the same time some properties *must* hold every time (valid JSON, no order without confirmation),
and some are only meaningful as rates (how often out-of-scope questions are refused). The strategy therefore separates
**what must always hold** from **what must hold often enough**, and gives each a different oracle.

**Out of scope for P1:** building the golden dataset and calibrating the judge against human labels (P2), long
multi-step agent scenarios and pass^k (P3), adversarial attacks (P4), performance and load.

## 2. Priorities **[D]**

All four risk areas from `finassist-app/docs/KNOWN_RISKS.md` are in scope, ordered by the cost of a failure:

| Order | Area | Risks | Why this order |
|---|---|---|---|
| 1 | **Agent safety** | confirmation gate, R09 invented arguments, R10 implicit advice, R11 reply vs. state | wrong orders move (mock) money |
| 2 | **Grounding & refusal** | R01 unsupported citations, R02 off-topic answers, R04 refusal | wrong facts with a citation look trustworthy |
| 3 | **Compliance disclaimer** | R07 missed advice questions, R08 over-triggering | regulatory exposure for a real assistant |
| 4 | **Schema & API contract** | response shape, 503 paths, input validation | cheapest and most stable; the base every other layer stands on |

Contract tests are listed last by impact but are **built first**, because every higher layer depends on them.

## 3. Test layers

| Layer | Question it answers | Oracle | Deterministic? | Runs |
|---|---|---|---|---|
| **L1 Contract** | Is the response well-formed? | Pydantic models of `/chat`, `/agent`, `/log`, `/state`; HTTP status codes | yes | every PR (replayed responses) + locally |
| **L2 Rules** | Does every answer obey hard rules? | code: disclaimer present for advice questions, `sources` non-empty when `refused=false`, prices in replies equal `get_quote`, no order in `/state` without a `pending_confirmation` → `executed` pair in `/log`, no system-prompt text in answers | yes, given a response | every PR (replayed) + locally against the live model |
| **L3 Judge** | Is the answer relevant and supported by its cited sources? | Claude as judge **[D]** with a 1–5 rubric (relevance, support), pass at ≥ 4, structured JSON verdict with a reason | no — measured | scheduled run (cost), never per PR |
| **L4 End-to-end** | Does a full user flow behave? | multi-turn `/agent` sessions asserted on `/log` and `/state`; Playwright drives the API (and a UI if one is added) | no — measured | locally / nightly |

**Target for the P1 minimum (20 tests):** L1 ×6, L2 ×8 (parametrised over the risk question sets), L3 ×1 judge
assertion, L4 ×5 agent flows. Stretch goes to 40+ with semantic-similarity checks and prompt/model regression runs.

## 4. Oracles in detail

- **Ground truth from the system itself.** The mock broker is deterministic: the price in a reply must equal
  `GET /agent/{id}/state` / `get_quote`; an executed order must match the pending order the user confirmed.
- **Question sets from the risk backlog.** Each risk gets a small labelled set: in-scope with a known source document,
  out-of-scope (must refuse), advice-seeking (must carry the disclaimer), educational with trigger words like *jual*
  or *membeli* (must not need it). Labels are written by me, not generated.
- **Judge (L3).** `claude-opus-5-5` through the `anthropic` SDK, output constrained to
  `{relevance: 1-5, support: 1-5, reason: str}`. `claude-opus-5-5` does not accept `temperature`; consistency comes from
  the schema and the rubric, and is **measured** by judging the same answers 3 times and reporting disagreement. Judge
  reasons are stored in the report. The judge is never the model under test, which avoids self-grading bias.

## 5. Non-determinism and flakiness **[D]**

- **Deterministic layers (L1, L2 on a recorded response) must never be flaky.** A flaky contract or rule test is a bug
  in the test.
- **Model-dependent cases run 3 times; a case passes when at least 2 of 3 runs pass (majority vote).** The verdict and
  all three outcomes are written to the report.
- **Flaky rate** = cases whose 3 outcomes disagree ÷ model-dependent cases. It is reported on every real-model run and
  tracked over time (P1-05). A case that disagrees in two consecutive runs is reviewed: tighten the assertion, or file
  a model-behaviour bug.
- Temperature stays at 0 on the system under test to reduce, not remove, variation.

## 6. Where tests run **[D]**

| When | What | Model |
|---|---|---|
| Every push / PR (GitHub Actions) | L1 + L2 against **recorded responses** (JSON cassettes captured from the live system) | none — replay |
| Locally, before each commit | L1 + L2 + L4 against the live `docker compose` stack | `llama3.2:3b` |
| Nightly / on demand | full live suite with 3× majority vote + L3 judge run | `llama3.2:3b` + Claude judge |

Recorded responses are refreshed whenever finassist-app changes its prompts, model or corpus; a stale cassette is
detected by comparing the recorded commit of finassist-app with the current one. CI is blocked until the GitHub
billing issue on the account is resolved.

## 7. Reporting and exit criteria

Each run produces an HTML report (pytest-html) plus a JSON summary: pass/fail per layer, flaky rate, refusal accuracy
on out-of-scope questions, disclaimer recall/precision, judge score distribution with reasons, and the tool-call log of
failed agent flows. Exit criteria for P1:

- L1 and L2 green in CI.
- Real-model numbers recorded (pass rate, flaky rate, refusal accuracy, disclaimer recall) — **as measured, not as
  targets**; low numbers become bug reports, not lowered assertions.
- At least 3 reproducible model-behaviour bug reports in `docs/bugs/` (steps, input, expected vs. actual, frequency x/n).

## 8. Risks of this strategy

| Risk | Mitigation |
|---|---|
| The judge is wrong or biased | P2 calibrates it against my own labels (Cohen's kappa); until then judge results are reported, not gating |
| Judge cost grows | scheduled only; small question set; cache verdicts for unchanged answers |
| Recorded responses go stale | tie each cassette to the finassist-app commit; refresh on change |
| 3× runs are slow | only model-dependent cases are repeated; deterministic layers run once |
| Tests encode today's wrong behaviour | assertions follow the spec in finassist-app's README, not current outputs |

## 9. Traceability

| Risk | Layer | Planned tests |
|---|---|---|
| Confirmation gate | L4, L2 | buy → pending, "ya" → executed; injection text never executes; reply vs. `/state` |
| R09 invented arguments | L4 | "jual semua KOPX" must read the portfolio before ordering |
| R10 implicit advice | L2, L4 | advice question on `/agent` triggers no trading tool |
| R01 / R02 unsupported or off-topic | L3, L2 | judge support ≥ 4; meta questions refused |
| R04 refusal | L2 | out-of-scope set refused (rate) |
| R07 / R08 disclaimer | L2 | advice set has disclaimer; educational set does not need it |
| Contract | L1 | schemas, 422 on bad input, 404 unknown session, 503 with reason |
