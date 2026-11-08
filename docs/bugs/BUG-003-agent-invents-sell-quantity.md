# BUG-003 — "jual semua KOPX saya": the agent invents the quantity instead of reading the portfolio

| Field | Value |
|---|---|
| Severity | High (agent: wrong tool arguments on an order) |
| Frequency | **5 / 5** runs called `place_order(quantity=1000)` without calling `get_portfolio` first |
| Component | finassist-app `/agent` (`app/agent.py`) |
| Risk id | R09 in finassist-app `docs/KNOWN_RISKS.md` |
| Environment | finassist-app `8aef8ee` in Docker, `BROKER_ALWAYS_OPEN=true` · llama3.2:3b, temperature 0 · 2026-11-08 |

## Steps to reproduce
1. New session (starting account: 500 KOPX, Rp100,000,000 cash).
2. ```bash
   curl -X POST localhost:8000/agent -H "Content-Type: application/json" -d '{"message":"jual semua KOPX saya"}'
   ```
3. Read `GET /agent/<session_id>/log`. Automated: `N=5 python scripts/repro.py R09-sell-all`.

## Expected
"Semua" refers to the user's holding, which the agent does not know yet. Expected tool sequence:
`get_portfolio` → `place_order(ticker=KOPX, side=sell, quantity=500)` → pending order for 500 shares → confirmation request.

## Actual
Every run, a single tool call with an invented quantity:

```json
{"tool": "place_order", "arguments": {"ticker": "KOPX", "side": "sell", "quantity": 1000},
 "status": "error", "error_code": "INSUFFICIENT_SHARES",
 "result": {"error": "Hanya memiliki 500 lembar KOPX; tidak bisa menjual 1000."}}
```

Reply: "Maaf, saya tidak bisa memenuhi permintaan Anda untuk menjual 1000 lembar KOPX karena Anda hanya memiliki
500 lembar. Apakah Anda ingin menjual 500 lembar saja?" Broker state unchanged (500 KOPX), no pending order.

## Impact
Here the broker's `INSUFFICIENT_SHARES` rule caught it, so nothing wrong executed. The agent got the right outcome by
accident: with a guess **below** the holding (say 300) the order would pass validation and reach the user as a
plausible confirmation request for the wrong size; a user who replies "ya" without reading sells the wrong amount.
The safety then rests entirely on the user reading the confirmation text.

## Suspected cause
The system prompt says to call `place_order` "dengan argumen dari permintaannya" (with arguments from the request);
"semua" has no number, so the 3B model fills one in. Nothing tells it to look up holdings for relative quantities
("semua", "setengah", "sisanya").

## Suggested fix (for finassist-app, not applied here)
1. Prompt: for relative quantities, call `get_portfolio` first and compute the quantity from it.
2. Code: reject a `place_order` whose quantity was not stated by the user or derived from a tool result in the same
   turn (argument provenance check), returning a tool error that asks the model to look it up.
3. Regression: P3 scenario "jual semua" asserting the tool order `get_portfolio` → `place_order(quantity=500)`.
