"""Motor de señales local (costo de IA = 0).

Evalúa la confluencia de varios indicadores sobre la última vela CERRADA y
produce un puntaje 0..1. Solo los puntajes altos generan una ``Signal`` que el
motor podrá llevar al comité de IA. Todo lo demás se descarta localmente.

Estrategia base: seguimiento de tendencia en spot (solo compras / largos):
  tendencia alcista + fuerza de tendencia + impulso MACD + RSI sano +
  confirmación de volumen + volatilidad suficiente para cubrir comisiones.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping

import pandas as pd

from .config import RiskSettings, StrategySettings
from .indicators import min_candles_required

# Pesos de cada condición en el puntaje de confluencia (suman 1.0).
WEIGHTS: dict[str, float] = {
    "trend": 0.25,
    "trend_strength": 0.15,
    "momentum": 0.20,
    "rsi": 0.15,
    "volume": 0.15,
    "volatility": 0.10,
}

FEATURE_COLUMNS = (
    "close", "ema_fast", "ema_mid", "ema_slow", "rsi", "macd", "macd_signal",
    "macd_hist", "atr", "atr_pct", "adx", "bb_pct_b", "volume_ratio",
)


@dataclass(frozen=True)
class ScoreResult:
    score: float
    checks: dict[str, bool]
    hard_ok: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class Signal:
    symbol: str
    side: str  # "long" (spot)
    candle_time: pd.Timestamp
    price: float
    score: float
    stop_loss: float
    take_profit: float
    atr: float
    reasons: tuple[str, ...] = ()
    features: dict[str, float] = field(default_factory=dict)


def _num(row: Mapping, key: str) -> float:
    value = row[key]
    return float(value) if value is not None else math.nan


def score_entry(last: Mapping, prev: Mapping, p: StrategySettings) -> ScoreResult:
    """Puntúa una vela (``last``) usando la anterior (``prev``) como referencia."""
    needed = ("close", "ema_fast", "ema_mid", "ema_slow", "rsi", "macd_hist",
              "atr_pct", "adx", "volume_ratio")
    if any(math.isnan(_num(last, k)) for k in needed) or any(
        math.isnan(_num(prev, k)) for k in ("rsi", "macd_hist")
    ):
        return ScoreResult(0.0, {}, False, ("datos insuficientes",))

    close = _num(last, "close")
    checks = {
        "trend": close > _num(last, "ema_slow") and _num(last, "ema_fast") > _num(last, "ema_mid"),
        "trend_strength": _num(last, "adx") >= p.adx_min,
        "momentum": _num(last, "macd_hist") > 0
        and (_num(prev, "macd_hist") <= 0 or _num(last, "macd_hist") > _num(prev, "macd_hist")),
        "rsi": p.rsi_min <= _num(last, "rsi") <= p.rsi_max and _num(last, "rsi") >= _num(prev, "rsi"),
        "volume": _num(last, "volume_ratio") >= p.volume_ratio_min,
        "volatility": p.min_atr_pct <= _num(last, "atr_pct") <= p.max_atr_pct,
    }
    labels = {
        "trend": "precio sobre EMA lenta y EMA rápida > EMA media",
        "trend_strength": f"ADX >= {p.adx_min:g}",
        "momentum": "histograma MACD positivo y creciente",
        "rsi": f"RSI en [{p.rsi_min:g}, {p.rsi_max:g}] y subiendo",
        "volume": f"volumen >= {p.volume_ratio_min:g}x su media",
        "volatility": "ATR suficiente para cubrir costos",
    }
    score = sum(WEIGHTS[k] for k, ok in checks.items() if ok)
    # Requisito duro: en spot solo compramos a favor de la tendencia.
    hard_ok = checks["trend"] and checks["volatility"]
    reasons = tuple(labels[k] for k, ok in checks.items() if ok)
    return ScoreResult(round(score, 4), checks, hard_ok, reasons)


def compute_levels(price: float, atr_value: float, r: RiskSettings) -> tuple[float, float]:
    """SL/TP basados en ATR, acotados por los límites de riesgo y el R:R mínimo."""
    sl_dist = atr_value * r.atr_sl_multiplier
    sl_dist = min(max(sl_dist, price * r.min_sl_pct), price * r.max_sl_pct)
    tp_dist = max(atr_value * r.atr_tp_multiplier, sl_dist * r.min_reward_risk)
    return price - sl_dist, price + tp_dist


def exit_alert(last: Mapping, prev: Mapping) -> str | None:
    """Detecta deterioro de una posición abierta (para revisión de salida)."""
    try:
        close, ema_mid = _num(last, "close"), _num(last, "ema_mid")
        hist, prev_hist, rsi_ = _num(last, "macd_hist"), _num(prev, "macd_hist"), _num(last, "rsi")
    except KeyError:
        return None
    if any(math.isnan(v) for v in (close, ema_mid, hist, prev_hist, rsi_)):
        return None
    if close < ema_mid and hist < 0 and prev_hist < 0:
        return "ruptura de tendencia: cierre bajo la EMA media con MACD negativo 2 velas"
    if rsi_ >= 78:
        return f"sobrecompra extrema (RSI={rsi_:.1f})"
    return None


class SignalEngine:
    def __init__(self, strategy: StrategySettings, risk: RiskSettings):
        self.strategy = strategy
        self.risk = risk

    def evaluate(self, symbol: str, df: pd.DataFrame) -> Signal | None:
        """``df`` debe contener solo velas cerradas y las columnas de indicadores."""
        if len(df) < min_candles_required(self.strategy):
            return None
        last, prev = df.iloc[-1], df.iloc[-2]
        result = score_entry(last, prev, self.strategy)
        if not result.hard_ok or result.score < self.strategy.min_signal_score:
            return None

        price, atr_value = float(last["close"]), float(last["atr"])
        stop_loss, take_profit = compute_levels(price, atr_value, self.risk)
        features = {
            k: round(float(last[k]), 8) for k in FEATURE_COLUMNS
            if k in last and not math.isnan(float(last[k]))
        }
        return Signal(
            symbol=symbol,
            side="long",
            candle_time=pd.Timestamp(df.index[-1]),
            price=price,
            score=result.score,
            stop_loss=stop_loss,
            take_profit=take_profit,
            atr=atr_value,
            reasons=result.reasons,
            features=features,
        )

    def exit_alert(self, df: pd.DataFrame) -> str | None:
        if len(df) < 2:
            return None
        return exit_alert(df.iloc[-1], df.iloc[-2])
