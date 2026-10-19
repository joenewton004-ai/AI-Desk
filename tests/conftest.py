import pytest

from ai_desk.data import add_required_columns, synthetic_prices


@pytest.fixture
def prices():
    # includes a synthetic "vix" column so strategies that need it can be tested
    return add_required_columns(synthetic_prices(n_days=1500, seed=3), ["vix"], source="synthetic")
