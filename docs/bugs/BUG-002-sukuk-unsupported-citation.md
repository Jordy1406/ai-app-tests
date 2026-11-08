# BUG-002 — "Apa itu sukuk?" gets an unsupported answer with a citation that never mentions sukuk

| Field | Value |
|---|---|
| Severity | High (grounding: a confident, cited, wrong-source answer) |
| Frequency | **5 / 5** runs answered, 5 / 5 cited the same irrelevant chunk; wording differed between run 1 and runs 2–5 |
| Component | finassist-app `/chat` (`app/retrieval.py`, `app/rag.py`) |
| Risk id | R01 (with R05) in finassist-app `docs/KNOWN_RISKS.md` |
| Environment | finassist-app `8aef8ee` in Docker, 30-document corpus (533 chunks) · llama3.2:3b, temperature 0 · 2026-11-08 |

## Steps to reproduce
```bash
curl -X POST localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"Apa itu sukuk?"}'
```
Automated: `N=5 python scripts/repro.py R01-sukuk`.

## Expected
Either an answer grounded in `docs/wiki_sukuk.md` (the corpus has a Sukuk article) citing it, or a refusal. Any cited
chunk must support the claim.

## Actual
`refused: false`, one source: `uu_8_1995_pasar_modal#122` — *UU 8/1995, Penjelasan Umum*, score 0.6254.

| Run | Answer |
|---|---|
| 1 | "Sukuk adalah surat utang yang diterbitkan oleh perusahaan atau lembaga keuangan untuk menanggung utang yang telah dianggap aman dan stabil." |
| 2–5 | "Sukuk adalah surat utang yang diterbitkan oleh perusahaan atau lembaga keuangan untuk menyerahkan hak untuk menerima pembayaran tertentu pada waktu tertentu." |

The cited statute contains the word "sukuk" **0 times** (`grep -ci sukuk docs/uu_8_1995_pasar_modal.md` → 0). Calling
sukuk "surat utang" (a debt instrument) also conflicts with the Sukuk article, which describes sharia certificates of
asset ownership. The Sukuk article was not among the retrieved chunks.

Before the corpus grew to 30 documents (10 documents, same date) the answer was also wrong but different: it described
a *warrant* and cited UU Pasal 61. More documents changed the error, not the outcome.

## Impact
A user gets a definition that is wrong in a way that matters for sharia-compliant investors, and the citation makes it
look verified. This is the failure mode the project exists to catch: hallucination hidden behind a real citation.

## Suspected cause
1. Retrieval: the top-4 for "Apa itu sukuk?" is Bapepam-LK (0.6477), UU Penjelasan Umum (0.6254), Saham › Saham biasa
   (0.6230) and Opsi › Gaya opsi (0.6223). **The Sukuk article is not in the top-4**, although its first sentence is the
   definition ("Sukuk adalah surat berharga komersial berbentuk sertifikat hak milik..."). Generic finance chunks embed
   as close to "Apa itu X?" as the right article does (see R04).
2. Generation: the model answers from background knowledge instead of refusing when the context does not contain the
   term; the code checks that *a* chunk was cited, not that it supports the answer.

## Suggested fix (for finassist-app, not applied here)
1. Retrieval: hybrid search (keyword + embedding) so an exact term like "sukuk" pulls `wiki_sukuk.md`; or boost
   title matches.
2. Grounding check: before returning, verify the key term of the question appears in the cited chunk, or run an
   LLM-as-judge support check (P1-04) and refuse below threshold.
3. Regression: add "Apa itu sukuk?" to the golden set (P2) with `wiki_sukuk.md` as the required source.
