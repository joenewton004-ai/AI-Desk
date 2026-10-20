import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import winners  # noqa: E402


def _prices(n=80, cols=("A", "B", "C")):
    idx = pd.date_range("2018-01-31", periods=n, freq="ME")
    rng = np.random.default_rng(3)
    return pd.DataFrame(100 * np.cumprod(1 + rng.normal(0.01, 0.05, (n, len(cols))), axis=0), index=idx, columns=list(cols))


def test_forward_return_and_rank_corr():
    px = _prices()
    start = px.index[10]
    f = winners.forward_return(px, start, 5)
    assert abs(f["A"] - (px["A"].iloc[70] / px["A"].iloc[10] - 1)) < 1e-12
    assert winners.forward_return(px, px.index[-3], 5).empty                 # window not finished yet
    a = pd.Series([1, 2, 3, 4.0])
    assert winners.rank_corr(a, a ** 3) == 1.0 and winners.rank_corr(a, -a) == -1.0


def test_price_features_use_only_the_past():
    px = _prices(n=60)
    start = px.index[40]
    base = winners.price_features(px, start)
    future = px.copy()
    future.iloc[41:] *= np.linspace(0.2, 5, 19)[:, None]
    pd.testing.assert_frame_equal(base, winners.price_features(future, start))


def test_lift_is_one_when_the_trait_changes_nothing_and_above_one_when_it_helps():
    rng = np.random.default_rng(0)
    pct = pd.Series(rng.random(4000))
    flat = pd.Series(rng.random(4000) < 0.1)
    assert abs(winners.lift(pct, flat, 0.8, 1.0) - 1) < 0.25
    helped = pd.Series(rng.random(4000) < np.where(pct > 0.8, 0.3, 0.05))
    assert winners.lift(pct, helped, 0.8, 1.0) > 2


def test_walk_forward_only_learns_from_finished_windows():
    rng = np.random.default_rng(1)

    def fake(start, n=300):
        df = pd.DataFrame({"fwd": rng.normal(0.3, 0.5, n)})
        df["annual"] = df["fwd"]
        df["winner"] = df["fwd"].rank(ascending=False) <= n * 0.1
        df["bust"] = df["fwd"].rank() <= n * 0.1
        for f in winners.FEATURES:
            df[f"p_{f}"] = winners.pct_rank(pd.Series(rng.random(n)) + (df["fwd"] if f == "roic_avg" else 0))
        return df

    wins = {pd.Timestamp(d): fake(d) for d in pd.date_range("2014-03-31", periods=14, freq="QE")}
    wf = winners.walk_forward(wins, 1, pd.Timestamp("2016-03-31"))
    assert len(wf) and (wf["trained_on"] > 0).all()
    first = wf.iloc[0]
    # a 1-year window ends 4 quarters after it starts, so the 2016-03-31 test can learn from the five
    # windows that started 2014-03 .. 2015-03 (the last one ends exactly at the test start) and none later
    assert first["trained_on"] == 5 and first["features_used"] >= 1
