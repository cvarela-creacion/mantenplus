import pytest

from tradingbot.config import CostSettings, RiskSettings
from tradingbot.costs import AICostTracker, CostModel, ProfitabilityFilter
from tradingbot.risk import MarketLimits, RiskManager, RiskRejected

COSTS = CostSettings()


def breakdown(qty=10.0, entry=100.0, sl=98.0, tp=104.0, ai=0.1):
    return CostModel(COSTS).evaluate(entry_price=entry, stop_loss=sl, take_profit=tp, quantity=qty,
                                     maker_fee=0.001, taker_fee=0.001, ai_cost=ai)


def test_cost_breakdown_arithmetic():
    b = breakdown()
    assert b.entry_fee == pytest.approx(1.0)          # 1000 * 0.1 %
    assert b.entry_slippage == pytest.approx(0.5)     # 1000 * 0.05 %
    assert b.tp_exit_fee == pytest.approx(1.04)       # 1040 * 0.1 % (maker)
    assert b.costs_tp_path == pytest.approx(1.0 + 0.5 + 1.04 + 0.1)
    assert b.net_profit_tp == pytest.approx(40 - b.costs_tp_path)
    assert b.net_loss_sl == pytest.approx(20 + 1.0 + 0.5 + 0.98 + 0.49 + 0.1)
    # VE en la probabilidad de equilibrio = 0
    assert b.expected_value(b.breakeven_probability) == pytest.approx(0.0, abs=1e-9)


def test_pre_ai_rejects_when_costs_eat_the_profit():
    # Operación diminuta: el costo de IA domina.
    tiny = breakdown(qty=0.05, ai=0.15)
    result = ProfitabilityFilter(COSTS).pre_ai(tiny)
    assert not result.ok
    assert any("beneficio" in r for r in result.reasons)


def test_pre_ai_accepts_healthy_trade():
    assert ProfitabilityFilter(COSTS).pre_ai(breakdown()).ok


def test_post_ai_requires_probability_edge_and_ev():
    f = ProfitabilityFilter(COSTS)
    b = breakdown()
    assert f.post_ai(b, 0.65).ok
    low = f.post_ai(b, b.breakeven_probability + 0.01)
    assert not low.ok and any("prob. IA" in r for r in low.reasons)


def test_ai_tracker_amortization_and_budget():
    t = AICostTracker(daily_budget_usd=0.10, prior_approval_rate=0.5, prior_weight=4)
    assert t.amortized_cost(0.05) == pytest.approx(0.10)
    for _ in range(6):
        t.record(0.01, approved=False)
    assert t.approval_rate() == pytest.approx(2 / 10)
    assert t.amortized_cost(0.05) == pytest.approx(0.25)
    assert not t.can_spend(0.05)  # 0.06 gastado + 0.05 > 0.10
    t.roll_day("2026-11-04")
    assert t.can_spend(0.05)
    t.record(0.02, approved=False, entry_review=False)  # revisión de salida
    assert t.calls_total == 6


def test_ai_tracker_cooldown_and_persistence():
    t = AICostTracker(daily_budget_usd=1.0)
    t.mark_consulted("entry:BTC/USDT", 1000.0)
    assert t.in_cooldown("entry:BTC/USDT", 1000.0 + 59 * 60, 60)
    assert not t.in_cooldown("entry:BTC/USDT", 1000.0 + 61 * 60, 60)
    clone = AICostTracker(daily_budget_usd=1.0)
    clone.load(t.to_dict())
    assert clone.last_consult_at == t.last_consult_at


# ---------------------------------------------------------------- riesgo -- #
RISK = RiskSettings()
LIMITS = MarketLimits(min_amount=0.0001, min_cost=5.0)


@pytest.mark.parametrize("sl,tp,msg", [
    (None, 104, "obligatorios"),
    (98, None, "obligatorios"),
    (101, 104, "SL < entrada < TP"),
    (99.9, 104, "ajustado"),
    (90, 130, "lejano"),
    (98, 101, "R:R"),
])
def test_invalid_levels_are_rejected(sl, tp, msg):
    errors = RiskManager(RISK).validate_levels(100.0, sl, tp)
    assert errors and any(msg in e for e in errors)


def test_position_size_caps_loss_at_risk_budget():
    rm = RiskManager(RiskSettings(max_position_pct=1.0))  # sin tope de nocional
    plan = rm.build_plan(symbol="BTC/USDT", entry=100.0, stop_loss=98.0, take_profit=104.0,
                         equity=100_000.0, free_quote=100_000.0, taker_fee=0.001,
                         slippage_pct=0.0005, limits=LIMITS)
    assert plan.risk_amount == pytest.approx(100_000 * RISK.risk_per_trade_pct, rel=1e-6)
    assert plan.reward_risk == pytest.approx(2.0)


def test_position_size_capped_by_max_position_and_free_balance():
    rm = RiskManager(RISK)
    plan = rm.build_plan(symbol="BTC/USDT", entry=100.0, stop_loss=98.0, take_profit=104.0,
                         equity=10_000.0, free_quote=1_000.0, taker_fee=0.001,
                         slippage_pct=0.0005, limits=LIMITS)
    assert plan.notional <= 1_000.0
    assert plan.risk_amount < 10_000 * RISK.risk_per_trade_pct


def test_below_min_notional_is_rejected():
    with pytest.raises(RiskRejected, match="nocional"):
        RiskManager(RISK).build_plan(symbol="X/USDT", entry=100.0, stop_loss=98.0, take_profit=104.0,
                                     equity=20.0, free_quote=20.0, taker_fee=0.001,
                                     slippage_pct=0.0005, limits=LIMITS)


def test_kill_switch_and_max_positions():
    rm = RiskManager(RISK)
    assert rm.can_open_new(open_positions=0, daily_realized_pnl=-10, day_start_equity=1000)[0]
    ok, why = rm.can_open_new(open_positions=0, daily_realized_pnl=-31, day_start_equity=1000)
    assert not ok and "kill switch" in why
    ok, why = rm.can_open_new(open_positions=RISK.max_open_positions, daily_realized_pnl=0, day_start_equity=1000)
    assert not ok and "máximo" in why
