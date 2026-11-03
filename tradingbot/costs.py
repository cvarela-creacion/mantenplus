"""Filtro estricto de rentabilidad neta.

Ninguna operación pasa si el beneficio esperado no supera holgadamente la suma
de: comisión de entrada + comisión de salida + deslizamiento + costo de la IA.

Dos compuertas:

1. **Antes de la IA** (gratis): con el costo de IA *amortizado* estimado. Si la
   operación no puede ser rentable ni en el mejor caso, no se gasta ni un
   centavo en consultar a la IA.
2. **Después de la IA**: con el costo real de la consulta, los niveles SL/TP
   finales y la probabilidad de éxito estimada por el comité; exige valor
   esperado neto positivo con margen.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .config import CostSettings


@dataclass(frozen=True)
class CostBreakdown:
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    notional: float
    entry_fee: float
    entry_slippage: float
    tp_exit_fee: float
    sl_exit_fee: float
    sl_slippage: float
    ai_cost: float
    gross_profit_tp: float
    gross_loss_sl: float
    costs_tp_path: float
    costs_sl_path: float
    net_profit_tp: float
    net_loss_sl: float
    profit_to_cost_ratio: float
    breakeven_probability: float

    def expected_value(self, win_probability: float) -> float:
        """VE neto (USD) si TP se alcanza con prob. p y SL con prob. 1-p."""
        p = min(max(win_probability, 0.0), 1.0)
        return p * self.net_profit_tp - (1.0 - p) * self.net_loss_sl

    def as_dict(self, ndigits: int = 6) -> dict[str, float]:
        return {k: round(v, ndigits) for k, v in asdict(self).items()}


class CostModel:
    """Calcula costos y resultados netos de una operación larga en spot.

    Supuestos de ejecución (coinciden con ``exchange.py``):
      * entrada: orden de mercado -> comisión *taker* + deslizamiento.
      * TP: pata LIMIT_MAKER del OCO -> comisión *maker*, sin deslizamiento.
      * SL: pata STOP_LOSS del OCO -> comisión *taker* + deslizamiento.
    """

    def __init__(self, settings: CostSettings):
        self.s = settings

    def evaluate(
        self,
        *,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        quantity: float,
        maker_fee: float,
        taker_fee: float,
        ai_cost: float,
    ) -> CostBreakdown:
        notional = quantity * entry_price
        entry_fee = notional * taker_fee
        entry_slip = notional * self.s.slippage_pct
        tp_fee = quantity * take_profit * maker_fee
        sl_fee = quantity * stop_loss * taker_fee
        sl_slip = quantity * stop_loss * self.s.slippage_pct

        gross_profit = quantity * (take_profit - entry_price)
        gross_loss = quantity * (entry_price - stop_loss)
        costs_tp = entry_fee + entry_slip + tp_fee + ai_cost
        costs_sl = entry_fee + entry_slip + sl_fee + sl_slip + ai_cost
        net_profit = gross_profit - costs_tp
        net_loss = gross_loss + costs_sl

        ratio = gross_profit / costs_tp if costs_tp > 0 else float("inf")
        breakeven = net_loss / (net_profit + net_loss) if net_profit > 0 else 1.0
        return CostBreakdown(
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            notional=notional,
            entry_fee=entry_fee,
            entry_slippage=entry_slip,
            tp_exit_fee=tp_fee,
            sl_exit_fee=sl_fee,
            sl_slippage=sl_slip,
            ai_cost=ai_cost,
            gross_profit_tp=gross_profit,
            gross_loss_sl=gross_loss,
            costs_tp_path=costs_tp,
            costs_sl_path=costs_sl,
            net_profit_tp=net_profit,
            net_loss_sl=net_loss,
            profit_to_cost_ratio=ratio,
            breakeven_probability=breakeven,
        )


@dataclass(frozen=True)
class FilterResult:
    ok: bool
    reasons: tuple[str, ...] = ()


class ProfitabilityFilter:
    def __init__(self, settings: CostSettings):
        self.s = settings

    def pre_ai(self, b: CostBreakdown) -> FilterResult:
        reasons: list[str] = []
        if b.net_profit_tp <= 0:
            reasons.append(f"beneficio neto en TP no positivo ({b.net_profit_tp:.4f})")
        if b.profit_to_cost_ratio < self.s.min_profit_to_cost_ratio:
            reasons.append(
                f"beneficio/costo {b.profit_to_cost_ratio:.2f}x < "
                f"{self.s.min_profit_to_cost_ratio:.2f}x"
            )
        if b.breakeven_probability > self.s.max_breakeven_probability:
            reasons.append(
                f"prob. de equilibrio {b.breakeven_probability:.1%} > "
                f"{self.s.max_breakeven_probability:.1%}"
            )
        return FilterResult(not reasons, tuple(reasons))

    def post_ai(self, b: CostBreakdown, win_probability: float) -> FilterResult:
        reasons = list(self.pre_ai(b).reasons)
        required_p = b.breakeven_probability + self.s.min_probability_edge
        if win_probability < required_p:
            reasons.append(
                f"prob. IA {win_probability:.1%} < equilibrio+margen {required_p:.1%}"
            )
        ev = b.expected_value(win_probability)
        min_ev = self.s.min_ev_to_cost_ratio * b.costs_tp_path
        if ev < min_ev:
            reasons.append(f"VE neto {ev:.4f} < mínimo {min_ev:.4f}")
        return FilterResult(not reasons, tuple(reasons))


@dataclass
class AICostTracker:
    """Contabilidad del gasto en IA: presupuesto diario, enfriamiento por
    símbolo y amortización del costo de las consultas rechazadas.

    El costo de IA imputado a una operación candidata es
    ``costo_por_consulta / tasa_de_aprobación``: cada operación ejecutada debe
    "pagar" también las consultas que terminaron en rechazo.
    """

    daily_budget_usd: float
    prior_approval_rate: float = 0.35
    prior_weight: float = 5.0
    min_approval_rate: float = 0.10
    day: str = ""
    spend_today: float = 0.0
    spend_total: float = 0.0
    calls_total: int = 0
    approvals_total: int = 0
    last_consult_at: dict[str, float] = field(default_factory=dict)

    # -- presupuesto -------------------------------------------------------- #
    def roll_day(self, today: str) -> None:
        if today != self.day:
            self.day = today
            self.spend_today = 0.0

    def can_spend(self, amount: float) -> bool:
        return self.spend_today + amount <= self.daily_budget_usd

    # -- enfriamiento ------------------------------------------------------- #
    def in_cooldown(self, key: str, now: float, cooldown_minutes: float) -> bool:
        last = self.last_consult_at.get(key)
        return last is not None and (now - last) < cooldown_minutes * 60

    def mark_consulted(self, key: str, now: float) -> None:
        self.last_consult_at[key] = now

    # -- amortización ------------------------------------------------------- #
    def approval_rate(self) -> float:
        rate = (self.approvals_total + self.prior_approval_rate * self.prior_weight) / (
            self.calls_total + self.prior_weight
        )
        return max(rate, self.min_approval_rate)

    def amortized_cost(self, call_cost: float) -> float:
        return call_cost / self.approval_rate()

    def record(self, cost_usd: float, approved: bool, *, entry_review: bool = True) -> None:
        """Registra el gasto. Solo las revisiones de ENTRADA cuentan para la tasa
        de aprobación (las de salida se cargan a la posición que las originó)."""
        self.spend_today += cost_usd
        self.spend_total += cost_usd
        if entry_review:
            self.calls_total += 1
            if approved:
                self.approvals_total += 1

    # -- persistencia ------------------------------------------------------- #
    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "spend_today": self.spend_today,
            "spend_total": self.spend_total,
            "calls_total": self.calls_total,
            "approvals_total": self.approvals_total,
            "last_consult_at": dict(self.last_consult_at),
        }

    def load(self, data: dict | None) -> None:
        if not data:
            return
        self.day = data.get("day", "")
        self.spend_today = float(data.get("spend_today", 0.0))
        self.spend_total = float(data.get("spend_total", 0.0))
        self.calls_total = int(data.get("calls_total", 0))
        self.approvals_total = int(data.get("approvals_total", 0))
        self.last_consult_at = {k: float(v) for k, v in data.get("last_consult_at", {}).items()}
