"""Shared fixtures: a Playwright API client pointed at the running FinAssist ID (BASE_URL)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from playwright.sync_api import APIRequestContext, sync_playwright


def _load_dotenv(path: Path = Path(".env")) -> None:
    """Minimal .env loader (KEY=VALUE lines); real environment variables win. Avoids an extra dependency."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if value.strip():
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
# Model calls on a laptop can take a while (cold model load ~70 s).
TIMEOUT_MS = int(os.getenv("REQUEST_TIMEOUT_MS", "180000"))


@pytest.fixture(scope="session")
def api() -> APIRequestContext:
    with sync_playwright() as p:
        ctx = p.request.new_context(base_url=BASE_URL, timeout=TIMEOUT_MS)
        try:
            ctx.get("/health", timeout=5000)
        except Exception as exc:  # noqa: BLE001 - any connection error means the target is not up
            ctx.dispose()
            pytest.skip(f"FinAssist ID is not reachable at {BASE_URL} ({exc.__class__.__name__}). "
                        "Start it: cd ../finassist-app && BROKER_ALWAYS_OPEN=true docker compose up -d")
        yield ctx
        ctx.dispose()


def pytest_report_header(config):
    return [f"target: {BASE_URL}", f"votes per model-dependent case: {os.getenv('VOTES', '3')}"]
