"""Bucle lógico híbrido.

Flujo por símbolo y por vela cerrada::

    OHLCV (ccxt) -> indicadores (pandas) -> señal local (puntaje)
         |  sin señal -> fin (costo IA = 0)
         v
    reglas de riesgo (posiciones, kill switch) -> plan con SL/TP obligatorios
         v
    compuerta de rentabilidad PRE-IA (comisiones + deslizamiento + IA amortizada)
         |  no rentable -> fin (costo IA = 0)
         v
    presupuesto/enfriamiento de IA -> COMITÉ DE IA (Claude)
         |  rechaza / error -> fin (fail-closed)
         v
    revalidación local de SL/TP propuestos + compuerta POST-IA (VE neto)
         v
    compra a mercado -> OCO de protección SL/TP en el exchange
         |  falla la protección -> cierre de emergencia inmediato
         v
    seguimiento: OCO ejecutado -> PnL neto (incluye costo IA) -> diario

El motor no sabe si está en Testnet o Producción: usa ``ExchangeClient``.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

import ccxt
import pandas as pd

from .ai_committee import InvestmentCommittee, build_market_context
from .config import Settings
from .costs import AICostTracker, CostBreakdown, CostModel, ProfitabilityFilter
from .exchange import ExchangeClient
from .indicators import add_indicators, min_candles_required
from .risk import MarketLimits, RiskManager, RiskRejected, TradePlan
from .signals import FEATURE_COLUMNS, Signal, SignalEngine
from .state import StateStore, utc_now_iso

log = logging.getLogger(__name__)


class TradingEngine:
    def __init__(
        self,
        settings: Settings,
        exchange: ExchangeClient,
        committee: InvestmentCommittee,
        store: StateStore,
        *,
        signal_engine: SignalEngine | None = None,
        clock: Callable[[], float] = time.time,
    ):
        self.cfg = settings
        self.exchange = exchange
        self.committee = committee
        self.store = store
        self.clock = clock
        self.signals = signal_engine or SignalEngine(settings.strategy, settings.risk)
        self.risk = RiskManager(settings.risk)
        self.cost_model = CostModel(settings.costs)
        self.profit_filter = ProfitabilityFilter(settings.costs)
        self.tracker = AICostTracker(
            daily_budget_usd=settings.ai.daily_budget_usd,
            prior_approval_rate=settings.ai.prior_approval_rate,
        )
        self.tracker.load(store.data.get("ai_ledger"))

    # ================================================================== #
    # Bucle principal
    # ================================================================== #
    def run_forever(self, stop_event: threading.Event) -> None:
        log.info("Motor iniciado: %s", self.cfg.describe())
        if self.store.positions:
            log.info("Posiciones recuperadas del estado: %s", ", ".join(self.store.positions))
        while not stop_event.is_set():
            started = self.clock()
            self.run_cycle()
            elapsed = self.clock() - started
            stop_event.wait(max(1.0, self.cfg.trading.poll_interval_seconds - elapsed))
        self._persist()
        log.info("Motor detenido de forma ordenada.")

    def run_cycle(self) -> None:
        self._roll_day()
        for symbol in self.cfg.trading.symbols:
            try:
                self._process_symbol(symbol)
            except ccxt.NetworkError as exc:
                log.warning("[%s] Error de red (se reintenta en el próximo ciclo): %s", symbol, exc)
            except ccxt.ExchangeError as exc:
                log.error("[%s] Error del exchange: %s", symbol, exc)
            except Exception:  # noqa: BLE001 - un símbolo nunca debe tumbar el bucle
                log.exception("[%s] Error inesperado", symbol)
        self._persist()

    def _process_symbol(self, symbol: str) -> None:
        t = self.cfg.trading
        df = self.exchange.fetch_ohlcv_df(symbol, t.timeframe, t.ohlcv_limit)
        if len(df) < min_candles_required(self.cfg.strategy):
            log.debug("[%s] Velas insuficientes (%d)", symbol, len(df))
            return
        df = add_indicators(df, self.cfg.strategy)

        if symbol in self.store.positions:
            self._manage_position(symbol, df)
            return

        # Cada vela cerrada se evalúa una sola vez: evita consultas repetidas.
        candle_key = pd.Timestamp(df.index[-1]).isoformat()
        if self.store.data["last_candle"].get(symbol) == candle_key:
            return
        self.store.data["last_candle"][symbol] = candle_key
        self._seek_entry(symbol, df)

    # ================================================================== #
    # Entradas
    # ================================================================== #
    def _seek_entry(self, symbol: str, df: pd.DataFrame) -> None:
        signal = self.signals.evaluate(symbol, df)
        if signal is None:
            return  # Caso más frecuente: cero llamadas a la IA.
        log.info(
            "[%s] Señal local score=%.2f precio=%.6g SL=%.6g TP=%.6g (%s)",
            symbol, signal.score, signal.price, signal.stop_loss, signal.take_profit,
            "; ".join(signal.reasons),
        )

        daily = self.store.daily(self._today())
        ok, why = self.risk.can_open_new(
            open_positions=len(self.store.positions),
            daily_realized_pnl=daily["realized_pnl"],
            day_start_equity=daily["start_equity"],
        )
        if not ok:
            log.info("[%s] Entrada bloqueada por riesgo: %s", symbol, why)
            return

        maker, taker = self.exchange.get_fee_rates(symbol, self.cfg.costs.maker_fee, self.cfg.costs.taker_fee)
        equity, free_quote = self._account_snapshot()
        limits = self.exchange.market_limits(symbol)
        try:
            plan = self._build_plan(symbol, signal.price, signal.stop_loss, signal.take_profit,
                                    equity, free_quote, taker, limits)
        except RiskRejected as exc:
            log.info("[%s] Plan rechazado por riesgo: %s", symbol, exc)
            return

        # ---- Compuerta 1: rentabilidad PRE-IA (gratuita) -------------------
        est_call = self.committee.estimated_call_cost()
        pre_costs = self._evaluate_costs(plan, maker, taker, self.tracker.amortized_cost(est_call))
        pre = self.profit_filter.pre_ai(pre_costs)
        if not pre.ok:
            log.info("[%s] Descartada ANTES de la IA (costo IA = 0): %s", symbol, "; ".join(pre.reasons))
            return

        # ---- Presupuesto y enfriamiento de la IA ---------------------------
        if not self.cfg.ai.enabled:
            log.info("[%s] IA desactivada (AI_ENABLED=false): la señal se registra, no se opera.", symbol)
            return
        now, key = self.clock(), f"entry:{symbol}"
        if self.tracker.in_cooldown(key, now, self.cfg.ai.symbol_cooldown_minutes):
            log.info("[%s] Comité en enfriamiento para este símbolo; se omite.", symbol)
            return
        if not self.tracker.can_spend(est_call):
            log.warning("Presupuesto diario de IA agotado (%.4f USD): no se consulta.", self.tracker.spend_today)
            return

        # ---- Comité de inversiones -----------------------------------------
        self.tracker.mark_consulted(key, now)
        result = self.committee.review_entry(
            signal=signal,
            plan=plan,
            costs=pre_costs,
            market_context=build_market_context(df),
            constraints=self._constraints(plan.entry_price),
            environment=self.exchange.environment,
        )
        self.tracker.record(result.cost_usd, result.approved)
        self._persist()
        log.info(
            "[%s] Comité: %s | costo IA=%.5f USD (%s tok in / %s tok out, %s)",
            symbol, getattr(result.verdict, "decision", "SIN VEREDICTO"),
            result.cost_usd, result.input_tokens, result.output_tokens, result.model,
        )
        if not result.ok:
            log.warning("[%s] Sin veredicto válido (%s): NO se opera.", symbol, result.error)
            return
        verdict = result.verdict
        if verdict.decision != "APPROVE":
            log.info("[%s] Rechazada por el comité: %s", symbol, verdict.rationale)
            return

        # ---- Revalidación local con precio actual y niveles de la IA -------
        price_now = self.exchange.fetch_last_price(symbol)
        drift = abs(price_now / plan.entry_price - 1)
        if drift > self.cfg.trading.max_entry_drift_pct:
            log.info("[%s] El precio se movió %.2f%% desde la señal: se aborta.", symbol, drift * 100)
            return
        try:
            final_plan = self._build_plan(symbol, price_now, verdict.stop_loss, verdict.take_profit,
                                          equity, free_quote, taker, limits)
        except RiskRejected as exc:
            log.info("[%s] Niveles del comité no cumplen las reglas de riesgo: %s", symbol, exc)
            return

        # ---- Compuerta 2: rentabilidad POST-IA (costo real de la consulta) --
        final_costs = self._evaluate_costs(final_plan, maker, taker, result.cost_usd)
        post = self.profit_filter.post_ai(final_costs, verdict.win_probability)
        if not post.ok:
            log.info("[%s] Descartada DESPUÉS de la IA: %s", symbol, "; ".join(post.reasons))
            return

        log.info(
            "[%s] APROBADA: qty=%s entrada≈%.6g SL=%.6g TP=%.6g R:R=%.2f p=%.0f%% VE=%.4f USD",
            symbol, final_plan.quantity, final_plan.entry_price, final_plan.stop_loss,
            final_plan.take_profit, final_plan.reward_risk, verdict.win_probability * 100,
            final_costs.expected_value(verdict.win_probability),
        )
        self._open_position(final_plan, final_costs, signal, result.cost_usd, verdict)

    def _build_plan(
        self, symbol: str, entry: float, sl: float, tp: float,
        equity: float, free_quote: float, taker: float, limits: MarketLimits,
    ) -> TradePlan:
        return self.risk.build_plan(
            symbol=symbol, entry=entry, stop_loss=sl, take_profit=tp,
            equity=equity, free_quote=free_quote, taker_fee=taker,
            slippage_pct=self.cfg.costs.slippage_pct, limits=limits,
            amount_to_precision=lambda q: self.exchange.amount_to_precision(symbol, q),
        )

    def _evaluate_costs(self, plan: TradePlan, maker: float, taker: float, ai_cost: float) -> CostBreakdown:
        return self.cost_model.evaluate(
            entry_price=plan.entry_price, stop_loss=plan.stop_loss, take_profit=plan.take_profit,
            quantity=plan.quantity, maker_fee=maker, taker_fee=taker, ai_cost=ai_cost,
        )

    def _constraints(self, entry: float) -> dict[str, float]:
        r = self.cfg.risk
        return {
            "stop_loss_min": round(entry * (1 - r.max_sl_pct), 8),
            "stop_loss_max": round(entry * (1 - r.min_sl_pct), 8),
            "take_profit_min_reward_risk": r.min_reward_risk,
        }

    # ================================================================== #
    # Ejecución y protección
    # ================================================================== #
    def _open_position(
        self, plan: TradePlan, costs: CostBreakdown, signal: Signal, ai_cost: float, verdict: Any
    ) -> None:
        symbol = plan.symbol
        position: dict[str, Any] = {
            "symbol": symbol,
            "side": "long",
            "quantity": plan.quantity,
            "entry_price": plan.entry_price,
            "stop_loss": plan.stop_loss,
            "take_profit": plan.take_profit,
            "opened_at": utc_now_iso(),
            "environment": self.exchange.environment,
            "signal_score": signal.score,
            "ai_cost_usd": ai_cost,
            "ai_win_probability": verdict.win_probability,
            "ai_rationale": verdict.rationale,
            "entry_fee_quote": costs.entry_fee,
            "oco_list_id": None,
        }

        if self.cfg.trading.dry_run:
            position["mode"] = "paper"
            paper = self._paper()
            paper["cash"] -= plan.notional + costs.entry_fee
            self.store.set_position(symbol, position)
            log.info("[%s] DRY_RUN: posición simulada abierta.", symbol)
            return

        position["mode"] = "live"
        order = self.exchange.market_buy(symbol, plan.quantity)
        filled = float(order.get("filled") or 0.0)
        if filled <= 0:
            log.error("[%s] La compra no se ejecutó: %s", symbol, order.get("status"))
            return
        avg = float(order.get("average") or order.get("price") or plan.entry_price)
        base, quote = symbol.split("/")
        fee = order.get("fee") or {}
        fee_cost, fee_ccy = float(fee.get("cost") or 0.0), fee.get("currency")
        net_qty = filled - fee_cost if fee_ccy == base else filled
        position["entry_fee_quote"] = self._fee_in_quote(fee_cost, fee_ccy, base, quote, avg, filled * avg)
        sell_qty = self.exchange.amount_to_precision(symbol, min(net_qty, self.exchange.free_balance(base)))
        position.update(entry_price=avg, quantity=sell_qty, entry_order_id=order.get("id"))
        # Se guarda ANTES de proteger: si el proceso muere aquí, el próximo
        # ciclo detecta la posición sin OCO y la protege o la cierra.
        self.store.set_position(symbol, position)

        oco = self._protect(symbol, position)
        if oco is None:
            log.critical("[%s] ¡No se pudo colocar SL/TP! Cierre de emergencia.", symbol)
            self._emergency_close(symbol, position, "fallo al colocar la protección OCO")
            return
        position["oco_list_id"] = oco.get("orderListId")
        self.store.set_position(symbol, position)
        log.info("[%s] Posición abierta y protegida (OCO %s).", symbol, position["oco_list_id"])

    def _protect(self, symbol: str, position: dict[str, Any], attempts: int = 2) -> dict | None:
        for attempt in range(1, attempts + 1):
            try:
                return self.exchange.place_oco_sell(
                    symbol,
                    position["quantity"],
                    take_profit=position["take_profit"],
                    stop_loss=position["stop_loss"],
                    stop_type=self.cfg.risk.stop_loss_order_type,
                    stop_limit_buffer_pct=self.cfg.risk.stop_limit_buffer_pct,
                )
            except Exception as exc:  # noqa: BLE001
                log.error("[%s] Intento %d de OCO fallido: %s", symbol, attempt, exc)
        return None

    def _emergency_close(self, symbol: str, position: dict[str, Any], reason: str) -> None:
        try:
            order = self.exchange.market_sell(symbol, position["quantity"])
        except Exception as exc:  # noqa: BLE001
            position["unprotected"] = True
            self.store.set_position(symbol, position)
            log.critical("[%s] CIERRE DE EMERGENCIA FALLIDO (%s). Revisión manual urgente.", symbol, exc)
            return
        price = float(order.get("average") or order.get("price") or self.exchange.fetch_last_price(symbol))
        self._record_close(symbol, position, price, f"emergencia: {reason}", self._order_fee_quote(symbol, order, price))

    # ================================================================== #
    # Seguimiento de posiciones
    # ================================================================== #
    def _manage_position(self, symbol: str, df: pd.DataFrame) -> None:
        pos = self.store.positions[symbol]
        if pos.get("mode") == "paper":
            if self._check_paper_exit(symbol, pos, df):
                return
        else:
            if not pos.get("oco_list_id"):
                log.warning("[%s] Posición sin protección OCO: reintentando.", symbol)
                oco = self._protect(symbol, pos)
                if oco is None:
                    self._emergency_close(symbol, pos, "posición sin protección")
                    return
                pos["oco_list_id"] = oco.get("orderListId")
                pos.pop("unprotected", None)
                self.store.set_position(symbol, pos)
                return
            fill = self.exchange.oco_fill(symbol, pos["oco_list_id"])
            if fill is not None:
                if fill["leg"] == "cancelled":
                    self._handle_cancelled_oco(symbol, pos)
                else:
                    fee = self._fee_in_quote(fill["fee_cost"], fill["fee_currency"], *symbol.split("/"),
                                             fill["price"], fill["amount"] * fill["price"])
                    self._record_close(symbol, pos, fill["price"], fill["leg"], fee)
                return

        alert = self.signals.exit_alert(df)
        if alert:
            self._review_exit(symbol, pos, df, alert)

    def _handle_cancelled_oco(self, symbol: str, pos: dict[str, Any]) -> None:
        base = symbol.split("/")[0]
        if self.exchange.free_balance(base) >= pos["quantity"] * 0.99:
            log.warning("[%s] OCO cancelado externamente; se vuelve a proteger.", symbol)
            pos["oco_list_id"] = None
            self.store.set_position(symbol, pos)
        else:
            log.warning("[%s] OCO cancelado y sin saldo: se asume cierre manual.", symbol)
            self.store.remove_position(symbol)
            self.store.append_journal({**pos, "closed_at": utc_now_iso(), "exit_reason": "cierre externo"})

    def _check_paper_exit(self, symbol: str, pos: dict[str, Any], df: pd.DataFrame) -> bool:
        opened = pd.Timestamp(pos["opened_at"])
        after = df[df.index > opened]
        price = self.exchange.fetch_last_price(symbol)
        low = min([price, *after["low"].tolist()])
        high = max([price, *after["high"].tolist()])
        # Supuesto pesimista: si ambos niveles se tocaron, se asume el SL.
        if low <= pos["stop_loss"]:
            exit_price = pos["stop_loss"] * (1 - self.cfg.costs.slippage_pct)
            self._record_close(symbol, pos, exit_price, "stop_loss")
            return True
        if high >= pos["take_profit"]:
            self._record_close(symbol, pos, pos["take_profit"], "take_profit")
            return True
        return False

    def _review_exit(self, symbol: str, pos: dict[str, Any], df: pd.DataFrame, alert: str) -> None:
        ai = self.cfg.ai
        now, key = self.clock(), f"exit:{symbol}"
        if not ai.enabled or self.tracker.in_cooldown(key, now, ai.exit_review_cooldown_minutes):
            return
        est = self.committee.estimated_call_cost()
        if not self.tracker.can_spend(est):
            return
        price = self.exchange.fetch_last_price(symbol)
        exit_cost = pos["quantity"] * price * (self.cfg.costs.taker_fee + self.cfg.costs.slippage_pct)
        # Revisar la salida solo tiene sentido si lo que se arriesga perder
        # (distancia al SL) justifica holgadamente el costo de consultar.
        at_risk = pos["quantity"] * max(price - pos["stop_loss"], 0.0)
        if at_risk < self.cfg.costs.min_profit_to_cost_ratio * (est + exit_cost):
            log.debug("[%s] Alerta de salida sin consulta: riesgo restante no justifica el costo.", symbol)
            return

        log.info("[%s] Alerta de salida: %s -> consulta al comité.", symbol, alert)
        self.tracker.mark_consulted(key, now)
        last = df.iloc[-1]
        result = self.committee.review_exit(
            position=pos,
            last_price=price,
            alert=alert,
            indicators={k: round(float(last[k]), 8) for k in FEATURE_COLUMNS if k in last and pd.notna(last[k])},
            market_context=build_market_context(df),
            exit_cost_usd=exit_cost,
        )
        self.tracker.record(result.cost_usd, approved=False, entry_review=False)
        pos["ai_cost_usd"] = pos.get("ai_cost_usd", 0.0) + result.cost_usd
        self.store.set_position(symbol, pos)
        if not result.ok or result.verdict.decision != "CLOSE":
            log.info("[%s] Comité de salida: %s", symbol,
                     result.error or f"HOLD - {result.verdict.rationale}")
            return

        log.info("[%s] Comité de salida: CLOSE - %s", symbol, result.verdict.rationale)
        if pos.get("mode") == "paper":
            self._record_close(symbol, pos, price * (1 - self.cfg.costs.slippage_pct), "cierre anticipado IA")
            return
        try:
            self.exchange.cancel_oco(symbol, pos["oco_list_id"])
        except Exception as exc:  # noqa: BLE001 - p. ej. el OCO acaba de ejecutarse
            log.warning("[%s] No se pudo cancelar el OCO (%s); se revisará en el próximo ciclo.", symbol, exc)
            return
        order = self.exchange.market_sell(symbol, pos["quantity"])
        fill_price = float(order.get("average") or order.get("price") or price)
        self._record_close(symbol, pos, fill_price, "cierre anticipado IA",
                           self._order_fee_quote(symbol, order, fill_price))

    # ================================================================== #
    # Contabilidad
    # ================================================================== #
    def _record_close(
        self, symbol: str, pos: dict[str, Any], exit_price: float, reason: str,
        exit_fee_quote: float | None = None,
    ) -> None:
        qty, entry = float(pos["quantity"]), float(pos["entry_price"])
        if exit_fee_quote is None:
            rate = self.cfg.costs.maker_fee if reason == "take_profit" else self.cfg.costs.taker_fee
            exit_fee_quote = qty * exit_price * rate
        gross = qty * (exit_price - entry)
        entry_fee = float(pos.get("entry_fee_quote", qty * entry * self.cfg.costs.taker_fee))
        ai_cost = float(pos.get("ai_cost_usd", 0.0))
        net = gross - entry_fee - exit_fee_quote - ai_cost

        if pos.get("mode") == "paper":
            self._paper()["cash"] += qty * exit_price - exit_fee_quote
        self.store.add_realized_pnl(self._today(), net)
        self.store.remove_position(symbol)
        self.store.append_journal({
            **pos,
            "closed_at": utc_now_iso(),
            "exit_price": exit_price,
            "exit_reason": reason,
            "gross_pnl": gross,
            "fees": entry_fee + exit_fee_quote,
            "ai_cost_usd": ai_cost,
            "net_pnl": net,
        })
        log.info(
            "[%s] CERRADA (%s) salida=%.6g bruto=%.4f comisiones=%.4f IA=%.4f NETO=%.4f USD",
            symbol, reason, exit_price, gross, entry_fee + exit_fee_quote, ai_cost, net,
        )

    @staticmethod
    def _fee_in_quote(cost: float, ccy: str | None, base: str, quote: str, price: float, notional: float) -> float:
        if ccy == quote:
            return cost
        if ccy == base:
            return cost * price
        # Comisión en BNB u otra moneda: se estima de forma conservadora al 0.1 %.
        return notional * 0.001

    def _order_fee_quote(self, symbol: str, order: dict, price: float) -> float:
        base, quote = symbol.split("/")
        fee = order.get("fee") or {}
        filled = float(order.get("filled") or 0.0)
        return self._fee_in_quote(float(fee.get("cost") or 0.0), fee.get("currency"), base, quote,
                                  price, filled * price)

    def _paper(self) -> dict[str, float]:
        return self.store.data.setdefault("paper", {"cash": self.cfg.trading.paper_equity})

    def _account_snapshot(self) -> tuple[float, float]:
        """(capital total, saldo libre en la moneda de cotización)."""
        if self.cfg.trading.dry_run:
            cash = self._paper()["cash"]
            invested = sum(p["quantity"] * p["entry_price"] for p in self.store.positions.values()
                           if p.get("mode") == "paper")
            return cash + invested, cash
        quote = self.cfg.trading.quote_currency
        balances = self.exchange.fetch_balances()
        free = self.exchange.free_balance(quote, balances)
        equity = self.exchange.equity_in_quote(quote, self.cfg.trading.symbols, balances)
        return equity, free

    def _today(self) -> str:
        return datetime.fromtimestamp(self.clock(), tz=timezone.utc).strftime("%Y-%m-%d")

    def _roll_day(self) -> None:
        day = self._today()
        self.tracker.roll_day(day)
        daily = self.store.daily(day)
        if daily["start_equity"] <= 0:
            try:
                daily["start_equity"] = self._account_snapshot()[0]
                log.info("Nuevo día %s: capital inicial %.2f %s", day, daily["start_equity"],
                         self.cfg.trading.quote_currency)
            except Exception as exc:  # noqa: BLE001
                log.warning("No se pudo leer el capital inicial del día: %s", exc)

    def _persist(self) -> None:
        self.store.data["ai_ledger"] = self.tracker.to_dict()
        self.store.save()
