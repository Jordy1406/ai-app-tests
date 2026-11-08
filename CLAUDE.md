# CLAUDE.md — ai-app-tests (P1)

## KONTEKS
Repo ini bagian dari portofolio AI Quality Engineer milik Jordy (sementara di akun GitHub `Jordy1406`; target org
`finassist-quality`). Sistem target bernama **FinAssist ID** (repo `finassist-app`): chatbot RAG atas dokumen publik
pasar modal (Bahasa Indonesia) + agent dengan tools `get_quote`, `get_portfolio`, `place_order` ke MOCK broker (data fiktif).

- **Repo ini:** P1 — AI App Testing.
- **Tujuan:** menguji aplikasi AI end-to-end walau output tidak deterministik.
- **MINIMUM:** 20 test: Playwright (UI/API), schema (Pydantic), rule-based (disclaimer wajib, angka sesuai mock),
  1 jenis judge assertion; CI GitHub Actions.
- **STRETCH:** semantic similarity, strategi flaky lengkap (temperature, sampel ganda, retry policy), 40+ test,
  regression saat ganti prompt/model.
- **Selesai jika:** CI hijau; `docs/STRATEGY.md` 2–3 halaman "Test Strategy for Non-Deterministic Systems";
  3 bug report perilaku model di `docs/bugs/`.
- **Input utama:** `finassist-app/docs/KNOWN_RISKS.md` (R01–R18) = daftar target uji.

## STACK
Python 3.12, pytest, httpx, Pydantic, Playwright (Python), GitHub Actions. Sistem target dijalankan dengan
`docker compose up` di repo `finassist-app` (Ollama di host).

## CARA RUN
```bash
# 1. jalankan target:  cd ../finassist-app && docker compose up -d
# 2. di repo ini:
python -m venv .venv && .venv\Scripts\activate    # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pytest                                            # BASE_URL default http://localhost:8000
```

## ATURAN
- Jelaskan rencana dulu, tunggu persetujuan, baru tulis kode.
- 1 sesi = 1 fitur = 1 commit/PR kecil. Pesan commit format Conventional Commits.
- Kerjakan MINIMUM dulu; STRETCH hanya jika diminta.
- Jangan tambah dependency tanpa alasan; catat di README jika menambah.
- Data hanya publik atau fiktif. Rahasia hanya di `.env` (dan `.env` di `.gitignore`).
- Desain test & eval (strategi, rubrik, ambang, label) diputuskan Jordy; Claude bantu implementasi dan menjelaskan.
- Repo ini **menguji**, tidak memperbaiki: kelemahan yang ditemukan jadi bug report, bukan patch diam-diam di finassist-app.
- Setelah tiap fitur: jalankan test, laporkan hasil (termasuk yang gagal), usulkan pesan commit.
