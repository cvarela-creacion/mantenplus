"""Gestión de riesgo obligatoria.

* Toda operación DEBE tener Stop Loss y Take Profit válidos (si no, se rechaza).
* El tamaño de la posición se calcula para que la pérdida en el SL, *incluyendo
  comisiones y deslizamiento*, no supere ``risk_per_trade_pct`` del capital.
* Límite de posiciones simultáneas y "kill switch" por pérdida diaria.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from .config import RiskSettings


class RiskRejected(Exception):
    """La operación viola alguna regla de riesgo."""


@dataclass(frozen=True)
class MarketLimits:
    min_amount: float | None = None
    min_cost: float | None = None  # nocional mínimo (filtro NOTIONAL de Binance)


@dataclass(frozen=True)
class TradePlan:
    symbol: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    quantity: float
    notional: float
    risk_amount: float
    reward_risk: float


class RiskManager:
    def __init__(self, settings: RiskSettings):
        self.s = settings

    # ------------------------------------------------------------------ #
    def validate_levels(self, entry: float, stop_loss: float | None, take_profit: float | None) -> list[str]:
        errors: list[str] = []
        if stop_loss is None or take_profit is None:
            return ["SL y TP son obligatorios"]
        for name, value in (("entrada", entry), ("SL", stop_loss), ("TP", take_profit)):
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                errors.append(f"{name} inválido: {value!r}")
        if errors:
            return errors
        if not stop_loss < entry < take_profit:
            return [f"para un largo se requiere SL < entrada < TP ({stop_loss} / {entry} / {take_profit})"]

        sl_pct = (entry - stop_loss) / entry
        if sl_pct < self.s.min_sl_pct:
            errors.append(f"SL demasiado ajustado ({sl_pct:.2%} < {self.s.min_sl_pct:.2%})")
        if sl_pct > self.s.max_sl_pct:
            errors.append(f"SL demasiado lejano ({sl_pct:.2%} > {self.s.max_sl_pct:.2%})")
        rr = (take_profit - entry) / (entry - stop_loss)
        if rr < self.s.min_reward_risk:
            errors.append(f"R:R {rr:.2f} < mínimo {self.s.min_reward_risk:.2f}")
        return errors

    # ------------------------------------------------------------------ #
    def size_position(
        self,
        *,
        entry: float,
        stop_loss: float,
        equity: float,
        free_quote: float,
        taker_fee: float,
        slippage_pct: float,
    ) -> float:
        exec_cost = taker_fee + slippage_pct
        # Pérdida por unidad si salta el SL, con costos de entrada y salida.
        loss_per_unit = (entry - stop_loss) + entry * exec_cost + stop_loss * exec_cost
        qty_by_risk = (equity * self.s.risk_per_trade_pct) / loss_per_unit
        max_notional = min(equity * self.s.max_position_pct, free_quote * 0.995 / (1 + exec_cost))
        qty_by_cap = max(max_notional, 0.0) / entry
        return max(min(qty_by_risk, qty_by_cap), 0.0)

    def build_plan(
        self,
        *,
        symbol: str,
        entry: float,
        stop_loss: float,
        take_profit: float,
        equity: float,
        free_quote: float,
        taker_fee: float,
        slippage_pct: float,
        limits: MarketLimits,
        amount_to_precision: Callable[[float], float] = lambda q: q,
    ) -> TradePlan:
        errors = self.validate_levels(entry, stop_loss, take_profit)
        if errors:
            raise RiskRejected("; ".join(errors))
        if equity <= 0 or free_quote <= 0:
            raise RiskRejected("sin capital disponible")

        raw_qty = self.size_position(
            entry=entry, stop_loss=stop_loss, equity=equity, free_quote=free_quote,
            taker_fee=taker_fee, slippage_pct=slippage_pct,
        )
        qty = amount_to_precision(raw_qty)
        if qty <= 0:
            raise RiskRejected("tamaño de posición = 0 tras aplicar precisión")
        if limits.min_amount and qty < limits.min_amount:
            raise RiskRejected(f"cantidad {qty} < mínimo del mercado {limits.min_amount}")
        # El nocional mínimo debe cumplirse incluso en la pata del SL (precio más
        # bajo) y tras descontar una comisión cobrada en el activo base.
        if limits.min_cost and qty * (1 - taker_fee) * stop_loss < limits.min_cost * 1.01:
            raise RiskRejected(
                f"nocional {qty * stop_loss:.2f} insuficiente para el mínimo {limits.min_cost}"
            )

        risk_amount = qty * ((entry - stop_loss) + (entry + stop_loss) * (taker_fee + slippage_pct))
        return TradePlan(
            symbol=symbol,
            side="long",
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            quantity=qty,
            notional=qty * entry,
            risk_amount=risk_amount,
            reward_risk=(take_profit - entry) / (entry - stop_loss),
        )

    # ------------------------------------------------------------------ #
    def can_open_new(
        self, *, open_positions: int, daily_realized_pnl: float, day_start_equity: float
    ) -> tuple[bool, str]:
        if open_positions >= self.s.max_open_positions:
            return False, f"máximo de posiciones abiertas ({self.s.max_open_positions})"
        if day_start_equity > 0 and daily_realized_pnl <= -self.s.max_daily_loss_pct * day_start_equity:
            return False, (
                f"kill switch: pérdida diaria {daily_realized_pnl:.2f} supera "
                f"{self.s.max_daily_loss_pct:.1%} del capital inicial del día"
            )
        return True, ""
