import pandas as pd

from ai_desk.validation import expand_grid, param_sensitivity, split_test, walk_forward


def test_expand_grid():
    assert len(expand_grid({"a": [1, 2, 3], "b": [0, 1]})) == 6


def test_split_test_periods_dont_overlap(prices):
    split = prices.index[900]
    res = split_test(prices, "trend", {}, str(split.date()))
    assert res["in_sample"].equity.index[-1] < split
    assert res["out_of_sample"].equity.index[0] >= split


def test_param_sensitivity_rows(prices):
    table = param_sensitivity(prices, "trend", {"lookback": [50, 100]})
    assert list(table["lookback"]) == [50, 100]


def test_walk_forward_is_contiguous_and_out_of_sample(prices):
    wf = walk_forward(prices, "trend", {"lookback": [50, 100]}, train_years=2, test_years=1)
    assert wf.equity.index.is_monotonic_increasing
    assert not wf.equity.index.duplicated().any()
    # the stitched curve begins only after the first training window
    assert wf.equity.index[0] >= prices.index[0] + pd.DateOffset(years=2) - pd.Timedelta(days=7)
    assert len(wf.windows) >= 2
