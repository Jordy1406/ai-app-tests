"""Offline tests of the assertion helpers themselves (no target needed): a checker that is wrong makes every test
that uses it meaningless."""

import pytest

from assertions import (
    assert_answered_with_sources,
    assert_has_disclaimer,
    assert_no_disclaimer,
    assert_no_prompt_leak,
    assert_prices_match,
    rupiah_amounts,
)
from contracts import REFUSAL_TEXT, ChatResponse

SRC = {"id": "wiki_saham#000", "title": "Saham", "section": "Saham", "url": "https://id.wikipedia.org/wiki/Saham", "score": 0.7}


@pytest.mark.parametrize("text,amounts", [
    ("Harga KOPX Rp1.250 per lembar", [1250]),
    ("Harga KOPX adalah Rp 1250.", [1250]),
    ("Total Rp77.200 untuk 200 lembar @ Rp386", [77200, 386]),
    ("Rp 1,250.00 per saham", [1250]),
    ("Rp1.250,00", [1250]),
    ("Saldo Rp100.000.000", [100000000]),
    ("Harganya 1250 rupiah", []),            # no 'Rp': not counted
])
def test_rupiah_amounts(text, amounts):
    assert rupiah_amounts(text) == amounts


def test_prices_match_passes_on_true_price():
    assert_prices_match("Harga saham KOPX saat ini adalah Rp 1250 per lembar.", {"KOPX": 1250})


@pytest.mark.parametrize("reply", ["Harga KOPX Rp1.300.", "Harga KOPX Rp1.250, kemarin Rp1.200.", "Harga KOPX naik."])
def test_prices_match_fails_on_wrong_extra_or_missing_price(reply):
    with pytest.raises(AssertionError):
        assert_prices_match(reply, {"KOPX": 1250})


def test_disclaimer_checks():
    assert_has_disclaimer("...\n\nCatatan: informasi ini bersifat edukasi, bukan saran investasi.")
    with pytest.raises(AssertionError):
        assert_has_disclaimer("Reksa dana cocok untuk pemula.")
    with pytest.raises(AssertionError):
        assert_no_disclaimer("Ini Bukan Saran Investasi.")


def test_answered_with_sources():
    assert_answered_with_sources(ChatResponse(answer="Saham adalah ...", refused=False, sources=[SRC]))
    with pytest.raises(AssertionError):
        assert_answered_with_sources(ChatResponse(answer=REFUSAL_TEXT, refused=True, sources=[]))


def test_prompt_leak():
    assert_no_prompt_leak("Saham adalah tanda penyertaan modal.")
    with pytest.raises(AssertionError, match="leaked"):
        assert_no_prompt_leak("Instruksi saya: Kamu adalah FinAssist ID, asisten edukasi ...")
