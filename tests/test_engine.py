from dataclasses import replace

import pytest

from conftest import (FakeCommittee, FakeExchange, StubSignals, approve, exit_verdict, make_ohlcv,
                      make_settings, make_signal, reject)
from tradingbot.ai_committee import CommitteeResult
from tradingbot.engine import TradingEngine
from tradingbot.state import StateStore

NOW = 1_767_484_800.0  # 2026-01-04 00:00 UTC


def build(tmp_path, *, committee=None, signal="default", alert=None, quote=10_000.0, **settings_overrides):
    df = make_ohlcv()
    settings = make_settings(tmp_path, **settings_overrides)
    exchange = FakeExchange(df, price=100.0, quote_balance=quote)
    committee = committee or FakeCommittee()
    sig = make_signal(df=df) if signal == "default" else signal
    engine = TradingEngine(settings, exchange, committee, StateStore(settings.env_state_dir),
                           signal_engine=StubSignals(sig, alert), clock=lambda: NOW)
    return engine, exchange, committee


def test_no_signal_means_zero_ai_calls(tmp_path):
    engine, exchange, committee = build(tmp_path, signal=None)
    engine.run_cycle()
    assert committee.entry_calls == 0 and not exchange.orders


def test_approved_trade_is_bought_and_protected_with_oco(tmp_path):
    engine, exchange, committee = build(tmp_path)
    engine.run_cycle()
    assert committee.entry_calls == 1
    assert exchange.orders[0][0] == "buy"
    oco = exchange.ocos[0]
    assert oco["sl"] == 98.0 and oco["tp"] == 104.0 and oco["type"] == "STOP_LOSS"
    pos = engine.store.positions["BTC/USDT"]
    assert pos["oco_list_id"] == 42 and pos["ai_cost_usd"] == pytest.approx(0.04)
    # La cantidad protegida descuenta la comisión cobrada en BTC.
    assert oco["amount"] <= exchange.orders[0][2] * (1 - 0.001) + 1e-9
    assert engine.tracker.calls_total == 1 and engine.tracker.approvals_total == 1


def test_same_candle_is_not_evaluated_twice(tmp_path):
    engine, exchange, committee = build(tmp_path, committee=FakeCommittee(reject()))
    engine.run_cycle()
    engine.run_cycle()
    assert committee.entry_calls == 1


def test_tiny_trade_is_discarded_before_ai(tmp_path):
    engine, exchange, committee = build(tmp_path, quote=60.0)
    engine.run_cycle()
    assert committee.entry_calls == 0 and not exchange.orders
    assert engine.tracker.spend_today == 0.0


def test_ai_reject_or_error_means_no_trade(tmp_path):
    for result in (reject(), CommitteeResult(None, cost_usd=0.02, error="refusal")):
        engine, exchange, committee = build(tmp_path / str(id(result)), committee=FakeCommittee(result))
        engine.run_cycle()
        assert committee.entry_calls == 1 and not exchange.orders
        assert engine.tracker.spend_today == pytest.approx(result.cost_usd)


def test_ai_levels_violating_risk_rules_are_rejected(tmp_path):
    # La IA propone un SL a 10 % (máximo permitido 4 %).
    engine, exchange, _ = build(tmp_path, committee=FakeCommittee(approve(sl=90.0, tp=120.0)))
    engine.run_cycle()
    assert not exchange.orders


def test_low_ai_probability_fails_post_ai_filter(tmp_path):
    engine, exchange, _ = build(tmp_path, committee=FakeCommittee(approve(p=0.40)))
    engine.run_cycle()
    assert not exchange.orders


def test_price_drift_aborts_entry(tmp_path):
    engine, exchange, _ = build(tmp_path)
    exchange.price = 101.0  # 1 % > MAX_ENTRY_DRIFT_PCT (0.3 %)
    engine.run_cycle()
    assert not exchange.orders


def test_oco_failure_triggers_emergency_close(tmp_path):
    engine, exchange, _ = build(tmp_path)
    exchange.fail_oco = True
    engine.run_cycle()
    assert [o[0] for o in exchange.orders] == ["buy", "sell"]
    assert "BTC/USDT" not in engine.store.positions
    journal = engine.store.journal_path.read_text(encoding="utf-8")
    assert "emergencia" in journal


def test_take_profit_fill_records_net_pnl_including_ai_cost(tmp_path):
    engine, exchange, _ = build(tmp_path)
    engine.run_cycle()
    pos = dict(engine.store.positions["BTC/USDT"])
    exchange.oco_result = {"leg": "take_profit", "price": 104.0, "amount": pos["quantity"],
                           "fee_cost": pos["quantity"] * 104.0 * 0.001, "fee_currency": "USDT"}
    engine.run_cycle()
    assert "BTC/USDT" not in engine.store.positions
    gross = pos["quantity"] * 4.0
    expected = gross - pos["entry_fee_quote"] - pos["quantity"] * 104.0 * 0.001 - 0.04
    assert engine.store.daily("2026-01-04")["realized_pnl"] == pytest.approx(expected)


def test_kill_switch_blocks_new_entries(tmp_path):
    engine, exchange, committee = build(tmp_path)
    daily = engine.store.daily("2026-01-04")
    daily.update(start_equity=10_000.0, realized_pnl=-400.0)
    engine.run_cycle()
    assert committee.entry_calls == 0 and not exchange.orders


def test_daily_ai_budget_blocks_consultation(tmp_path):
    engine, exchange, committee = build(tmp_path)
    engine.tracker.roll_day("2026-01-04")
    engine.tracker.spend_today = engine.cfg.ai.daily_budget_usd
    engine.run_cycle()
    assert committee.entry_calls == 0


def test_ai_disabled_never_trades(tmp_path):
    base = make_settings(tmp_path)
    engine, exchange, committee = build(tmp_path, ai=replace(base.ai, enabled=False))
    engine.run_cycle()
    assert committee.entry_calls == 0 and not exchange.orders


def test_exit_review_close_cancels_oco_and_sells(tmp_path):
    committee = FakeCommittee(approve(), exit_result=exit_verdict("CLOSE"))
    engine, exchange, _ = build(tmp_path, committee=committee, alert="ruptura de tendencia")
    engine.run_cycle()   # abre
    engine.run_cycle()   # revisa salida
    assert committee.exit_calls == 1 and exchange.cancelled == [42]
    assert [o[0] for o in exchange.orders] == ["buy", "sell"]
    assert "BTC/USDT" not in engine.store.positions
    assert engine.tracker.calls_total == 1  # la revisión de salida no altera la tasa de aprobación


def test_dry_run_simulates_without_orders_and_hits_stop(tmp_path):
    base = make_settings(tmp_path)
    engine, exchange, _ = build(tmp_path, trading=replace(base.trading, dry_run=True, paper_equity=10_000.0))
    engine.run_cycle()
    pos = engine.store.positions["BTC/USDT"]
    assert pos["mode"] == "paper" and not exchange.orders and not exchange.ocos
    exchange.price = 97.5  # perfora el SL
    engine.run_cycle()
    assert "BTC/USDT" not in engine.store.positions
    assert engine.store.daily("2026-01-04")["realized_pnl"] < 0


def test_state_survives_restart(tmp_path):
    engine, exchange, committee = build(tmp_path)
    engine.run_cycle()
    reloaded = StateStore(engine.cfg.env_state_dir)
    assert "BTC/USDT" in reloaded.positions
    assert reloaded.data["ai_ledger"]["calls_total"] == 1
