import numpy as np
import pandas as pd
import pytest

from conftest import make_ohlcv
from tradingbot.indicators import add_indicators, adx, atr, ema, macd, rsi


def test_rsi_only_gains_is_100_and_only_losses_is_0():
    up = pd.Series(np.arange(1, 60, dtype=float))
    down = up[::-1].reset_index(drop=True)
    assert rsi(up).iloc[-1] == pytest.approx(100.0)
    assert rsi(down).iloc[-1] == pytest.approx(0.0)


def test_rsi_flat_series_is_neutral():
    assert rsi(pd.Series([10.0] * 40)).iloc[-1] == pytest.approx(50.0)


def test_rsi_bounded(ohlcv):
    values = rsi(ohlcv["close"]).dropna()
    assert ((values >= 0) & (values <= 100)).all()


def test_ema_matches_pandas_definition(ohlcv):
    expected = ohlcv["close"].ewm(span=21, adjust=False).mean()
    got = ema(ohlcv["close"], 21)
    pd.testing.assert_series_equal(got.dropna(), expected[got.notna()], check_names=False)


def test_macd_zero_on_constant_series():
    line, signal, hist = macd(pd.Series([50.0] * 80))
    assert line.iloc[-1] == pytest.approx(0.0)
    assert hist.iloc[-1] == pytest.approx(0.0)


def test_atr_constant_range():
    n = 50
    close = pd.Series([100.0] * n)
    high, low = close + 1.0, close - 1.0
    assert atr(high, low, close).iloc[-1] == pytest.approx(2.0)


def test_adx_bounded_and_high_in_strong_trend():
    df = make_ohlcv(drift=0.004, vol=0.002)
    values = adx(df["high"], df["low"], df["close"]).dropna()
    assert ((values >= 0) & (values <= 100)).all()
    assert values.iloc[-1] > 25


def test_add_indicators_does_not_mutate_input(ohlcv):
    cols = list(ohlcv.columns)
    out = add_indicators(ohlcv)
    assert list(ohlcv.columns) == cols
    for col in ("ema_fast", "ema_slow", "rsi", "macd_hist", "atr_pct", "adx", "volume_ratio", "bb_pct_b"):
        assert col in out and not np.isnan(out[col].iloc[-1])
