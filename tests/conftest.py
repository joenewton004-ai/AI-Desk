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
