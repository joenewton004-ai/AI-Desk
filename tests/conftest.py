import pytest

from ai_desk.data import add_required_columns, synthetic_prices


@pytest.fixture
def prices():
    # includes a synthetic "vix" column so strategies that need it can be tested
    return add_required_columns(synthetic_prices(n_days=1500, seed=3), ["vix"], source="synthetic")


@pytest.fixture(autouse=True)
def isolated_journal(tmp_path, monkeypatch):
    """Tests never write to the real trade journal or portfolio locks."""
    from ai_desk import tradebook

    monkeypatch.setattr(tradebook, "DIR", tmp_path / "journal")
    # the overnight sleeve's files, and the swap switch (a real activation must not change what tests see)
    from ai_desk import overnight
    from ai_desk.portfolio import methods
    monkeypatch.setattr(overnight, "BOOK", tmp_path / "overnight_book.json")
    monkeypatch.setattr(overnight, "LOCK", tmp_path / "overnight.json")
    monkeypatch.setattr(overnight, "DIR", tmp_path / "journal_overnight")
    monkeypatch.setattr(methods, "OVERNIGHT_SWAP", tmp_path / "overnight_live.json")
    # the overnight buy's regime checks download prices: tests see "buy as usual" unless they set their own
    monkeypatch.setattr(overnight, "check_regime", lambda *a, **k: {"cash": False, "reasons": []})
