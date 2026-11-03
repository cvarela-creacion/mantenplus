"""Indicadores técnicos calculados localmente con pandas (costo de IA = 0).

Se implementan a mano (sin pandas-ta / TA-Lib) para no depender de librerías
nativas y para que el cálculo sea transparente y verificable con pruebas.
Todas las medias "de Wilder" usan ``ewm(alpha=1/n)``, igual que TradingView.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import StrategySettings


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def _wilder(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = _wilder(gain, period)
    avg_loss = _wilder(loss, period)
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    # Sin pérdidas en la ventana -> RSI = 100; sin movimiento -> 50.
    out = out.where(avg_loss != 0.0, 100.0)
    out = out.where(~((avg_gain == 0.0) & (avg_loss == 0.0)), 50.0)
    return out.where(avg_gain.notna())


def macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    line = ema(close, fast) - ema(close, slow)
    signal_line = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return line, signal_line, line - signal_line


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    ranges = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    )
    return ranges.max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    return _wilder(true_range(high, low, close), period)


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    atr_ = atr(high, low, close, period)
    plus_di = 100 * _wilder(plus_dm, period) / atr_
    minus_di = 100 * _wilder(minus_dm, period) / atr_
    di_sum = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    return _wilder(dx.fillna(0.0), period)


def bollinger(
    close: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = sma(close, window)
    std = close.rolling(window=window, min_periods=window).std(ddof=0)
    return mid, mid + num_std * std, mid - num_std * std


def add_indicators(df: pd.DataFrame, params: StrategySettings | None = None) -> pd.DataFrame:
    """Devuelve una copia del OHLCV con todas las columnas de indicadores."""
    p = params or StrategySettings()
    out = df.copy()
    close, high, low = out["close"], out["high"], out["low"]

    out["ema_fast"] = ema(close, p.ema_fast)
    out["ema_mid"] = ema(close, p.ema_mid)
    out["ema_slow"] = ema(close, p.ema_slow)
    out["rsi"] = rsi(close, p.rsi_period)
    out["macd"], out["macd_signal"], out["macd_hist"] = macd(close)
    out["atr"] = atr(high, low, close)
    out["atr_pct"] = out["atr"] / close
    out["adx"] = adx(high, low, close)
    out["bb_mid"], out["bb_upper"], out["bb_lower"] = bollinger(close)
    band_width = (out["bb_upper"] - out["bb_lower"]).replace(0.0, np.nan)
    out["bb_pct_b"] = (close - out["bb_lower"]) / band_width
    out["volume_ratio"] = out["volume"] / sma(out["volume"], 20)
    return out


def min_candles_required(params: StrategySettings | None = None) -> int:
    """Velas necesarias para que la EMA lenta y el resto estén 'calientes'."""
    p = params or StrategySettings()
    return p.ema_slow + 30
