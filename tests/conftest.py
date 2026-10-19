import pytest

from ai_desk.data import synthetic_prices


@pytest.fixture
def prices():
    return synthetic_prices(n_days=1500, seed=3)
