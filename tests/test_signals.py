import pytest

from conftest import make_ohlcv
from tradingbot.config import RiskSettings, StrategySettings
from tradingbot.indicators import add_indicators
from tradingbot.signals import SignalEngine, compute_levels, exit_alert, score_entry

P = StrategySettings()

GOOD_LAST = dict(close=105, ema_fast=104, ema_mid=102, ema_slow=100, rsi=58, macd_hist=0.4,
                 atr_pct=0.01, adx=28, volume_ratio=1.8)
GOOD_PREV = dict(rsi=55, macd_hist=0.2)


def test_full_confluence_scores_one():
    r = score_entry(GOOD_LAST, GOOD_PREV, P)
    assert r.score == pytest.approx(1.0)
    assert r.hard_ok and all(r.checks.values())


def test_downtrend_fails_hard_requirement_even_if_other_checks_pass():
    last = {**GOOD_LAST, "close": 95}
    r = score_entry(last, GOOD_PREV, P)
    assert not r.hard_ok


def test_missing_data_scores_zero():
    last = {**GOOD_LAST, "adx": float("nan")}
    assert score_entry(last, GOOD_PREV, P).score == 0.0


def test_levels_respect_min_rr_and_sl_bounds():
    r = RiskSettings()
    sl, tp = compute_levels(100.0, atr_value=0.1, r=r)  # ATR diminuto -> SL mínimo
    assert sl == pytest.approx(100 * (1 - r.min_sl_pct))
    assert (tp - 100) / (100 - sl) >= r.min_reward_risk - 1e-9
    sl, _ = compute_levels(100.0, atr_value=50.0, r=r)  # ATR enorme -> SL máximo
    assert sl == pytest.approx(100 * (1 - r.max_sl_pct))


def test_exit_alert_on_trend_break():
    last = dict(close=99, ema_mid=100, macd_hist=-0.2, rsi=40)
    assert "ruptura" in exit_alert(last, dict(macd_hist=-0.1))
    assert exit_alert({**last, "close": 101}, dict(macd_hist=-0.1)) is None


def test_engine_never_signals_in_downtrend():
    df = add_indicators(make_ohlcv(drift=-0.002, vol=0.003))
    assert SignalEngine(P, RiskSettings()).evaluate("BTC/USDT", df) is None


def test_engine_signal_has_valid_levels_when_present():
    engine = SignalEngine(StrategySettings(min_signal_score=0.0), RiskSettings())
    for seed in range(30):
        df = add_indicators(make_ohlcv(drift=0.002, vol=0.004, seed=seed))
        signal = engine.evaluate("BTC/USDT", df)
        if signal:
            assert signal.stop_loss < signal.price < signal.take_profit
            assert signal.features["rsi"] == pytest.approx(float(df["rsi"].iloc[-1]), rel=1e-6)
            return
    pytest.fail("ninguna serie alcista sintética produjo señal")
