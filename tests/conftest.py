"""Dobles de prueba: exchange falso, comité falso y datos sintéticos."""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from tradingbot.ai_committee import CommitteeResult, EntryVerdict, ExitVerdict
from tradingbot.config import (
    AISettings, CostSettings, ExchangeSettings, RiskSettings, Settings,
    StrategySettings, TradingSettings,
)
from tradingbot.risk import MarketLimits
from tradingbot.signals import Signal


def make_ohlcv(n: int = 300, start: float = 100.0, drift: float = 0.0005, vol: float = 0.004,
               seed: int = 7, freq: str = "15min") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, n)
    close = start * np.exp(np.cumsum(rets))
    open_ = np.concatenate([[start], close[:-1]])
    spread = np.abs(rng.normal(0, vol / 2, n)) * close
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    volume = rng.uniform(80, 120, n)
    idx = pd.date_range("2026-01-01", periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)


def make_settings(tmp_path: Path, **overrides: Any) -> Settings:
    base = Settings(
        exchange=ExchangeSettings(sandbox_mode=True, api_key="k", api_secret="s"),
        trading=TradingSettings(symbols=("BTC/USDT",)),
        strategy=StrategySettings(),
        risk=RiskSettings(),
        costs=CostSettings(),
        ai=AISettings(enabled=True, daily_budget_usd=5.0),
        state_dir=tmp_path,
    )
    return replace(base, **overrides)


class FakeExchange:
    environment = "TESTNET"
    is_sandbox = True

    def __init__(self, df: pd.DataFrame, price: float = 100.0, quote_balance: float = 10_000.0):
        self.df = df
        self.price = price
        self.balances = {"USDT": {"free": quote_balance, "total": quote_balance}, "BTC": {"free": 0.0, "total": 0.0}}
        self.fail_oco = False
        self.oco_result: dict | None = None
        self.orders: list[tuple[str, str, float]] = []
        self.ocos: list[dict] = []
        self.cancelled: list[Any] = []
        self.limits = MarketLimits(min_amount=0.00001, min_cost=5.0)

    # datos
    def fetch_ohlcv_df(self, symbol, timeframe, limit):
        return self.df

    def fetch_last_price(self, symbol):
        return self.price

    def get_fee_rates(self, symbol, maker, taker):
        return maker, taker

    def market_limits(self, symbol):
        return self.limits

    def amount_to_precision(self, symbol, amount):
        return math.floor(amount * 1e5) / 1e5

    # cuenta
    def fetch_balances(self):
        return self.balances

    def free_balance(self, asset, balances=None):
        return float(self.balances.get(asset, {}).get("free", 0.0))

    def equity_in_quote(self, quote, symbols, balances=None):
        return self.balances[quote]["total"] + self.balances["BTC"]["total"] * self.price

    # órdenes
    def market_buy(self, symbol, amount):
        self.orders.append(("buy", symbol, amount))
        fee = amount * 0.001
        self.balances["USDT"]["free"] -= amount * self.price
        self.balances["USDT"]["total"] -= amount * self.price
        self.balances["BTC"]["free"] += amount - fee
        self.balances["BTC"]["total"] += amount - fee
        return {"id": "B1", "filled": amount, "average": self.price, "status": "closed",
                "fee": {"cost": fee, "currency": "BTC"}}

    def market_sell(self, symbol, amount):
        self.orders.append(("sell", symbol, amount))
        return {"id": "S1", "filled": amount, "average": self.price, "status": "closed",
                "fee": {"cost": amount * self.price * 0.001, "currency": "USDT"}}

    def place_oco_sell(self, symbol, amount, take_profit, stop_loss, stop_type="STOP_LOSS", stop_limit_buffer_pct=0.002):
        if self.fail_oco:
            raise RuntimeError("OCO rechazado")
        self.ocos.append({"symbol": symbol, "amount": amount, "tp": take_profit, "sl": stop_loss, "type": stop_type})
        return {"orderListId": 42}

    def oco_fill(self, symbol, order_list_id):
        return self.oco_result

    def cancel_oco(self, symbol, order_list_id):
        self.cancelled.append(order_list_id)


class FakeCommittee:
    def __init__(self, entry_result: CommitteeResult | None = None, exit_result: CommitteeResult | None = None,
                 call_cost: float = 0.05):
        self.entry_result = entry_result or approve()
        self.exit_result = exit_result
        self.call_cost = call_cost
        self.entry_calls = 0
        self.exit_calls = 0
        self.last_entry_kwargs: dict | None = None

    def estimated_call_cost(self):
        return self.call_cost

    def review_entry(self, **kwargs):
        self.entry_calls += 1
        self.last_entry_kwargs = kwargs
        return self.entry_result

    def review_exit(self, **kwargs):
        self.exit_calls += 1
        return self.exit_result


def approve(sl: float = 98.0, tp: float = 104.0, p: float = 0.6, cost: float = 0.04) -> CommitteeResult:
    verdict = EntryVerdict(decision="APPROVE", win_probability=p, stop_loss=sl, take_profit=tp,
                           confidence="high", risk_flags=[], rationale="Tendencia sólida.")
    return CommitteeResult(verdict, cost_usd=cost, input_tokens=2000, output_tokens=1500, model="claude-opus-5-5")


def reject(cost: float = 0.03) -> CommitteeResult:
    verdict = EntryVerdict(decision="REJECT", win_probability=0.3, stop_loss=98.0, take_profit=104.0,
                           confidence="medium", risk_flags=["resistencia cercana"], rationale="Resistencia.")
    return CommitteeResult(verdict, cost_usd=cost, model="claude-opus-5-5")


def exit_verdict(decision: str, cost: float = 0.03) -> CommitteeResult:
    return CommitteeResult(ExitVerdict(decision=decision, risk_flags=[], rationale="Deterioro."), cost_usd=cost)


class StubSignals:
    """Motor de señales controlado por la prueba."""

    def __init__(self, signal: Signal | None, alert: str | None = None):
        self.signal = signal
        self.alert = alert

    def evaluate(self, symbol, df):
        return self.signal

    def exit_alert(self, df):
        return self.alert


def make_signal(price: float = 100.0, sl: float = 98.0, tp: float = 104.0, df: pd.DataFrame | None = None) -> Signal:
    ts = df.index[-1] if df is not None else pd.Timestamp("2026-01-04", tz="UTC")
    return Signal(symbol="BTC/USDT", side="long", candle_time=ts, price=price, score=0.85,
                  stop_loss=sl, take_profit=tp, atr=1.2, reasons=("tendencia",), features={"rsi": 55.0})


@pytest.fixture
def ohlcv() -> pd.DataFrame:
    return make_ohlcv()
