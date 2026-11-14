"""Comité de inversiones con IA (Claude).

La IA NO monitorea el mercado: solo se le consulta cuando el motor local ya
encontró una señal de alta probabilidad que, además, superó la compuerta de
rentabilidad previa. Actúa como validador estratégico final:

* ``review_entry``: aprueba/rechaza una entrada, estima la probabilidad de
  alcanzar el TP antes que el SL y puede ajustar SL/TP (que luego se vuelven a
  validar localmente con las reglas de riesgo y costos).
* ``review_exit``: ante una alerta de deterioro de una posición abierta,
  decide mantener (HOLD) o cerrar anticipadamente (CLOSE).

Principio de seguridad "fail-closed": cualquier error, rechazo del modelo,
respuesta truncada o JSON inválido equivale a NO operar.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from typing import Any, Literal

import anthropic
import pandas as pd
from pydantic import BaseModel, Field, ValidationError

from .config import AISettings
from .costs import CostBreakdown
from .risk import TradePlan
from .signals import Signal

log = logging.getLogger(__name__)

FALLBACK_BETA = "server-side-fallback-2026-07-01"


# --------------------------------------------------------------------------- #
# Esquemas de salida estructurada
# --------------------------------------------------------------------------- #
class EntryVerdict(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    win_probability: float = Field(ge=0.0, le=1.0)
    stop_loss: float = Field(gt=0)
    take_profit: float = Field(gt=0)
    confidence: Literal["low", "medium", "high"]
    risk_flags: list[str]
    rationale: str


class ExitVerdict(BaseModel):
    decision: Literal["HOLD", "CLOSE"]
    risk_flags: list[str]
    rationale: str


ENTRY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["APPROVE", "REJECT"]},
        "win_probability": {
            "type": "number",
            "description": "Probabilidad (0 a 1) de tocar el take_profit antes que el stop_loss.",
        },
        "stop_loss": {"type": "number"},
        "take_profit": {"type": "number"},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "risk_flags": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": [
        "decision", "win_probability", "stop_loss", "take_profit",
        "confidence", "risk_flags", "rationale",
    ],
    "additionalProperties": False,
}

EXIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["HOLD", "CLOSE"]},
        "risk_flags": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["decision", "risk_flags", "rationale"],
    "additionalProperties": False,
}

ENTRY_SYSTEM_PROMPT = """\
Eres el comité de inversiones de un sistema de trading algorítmico que opera en \
Binance Spot (solo posiciones largas). Un motor cuantitativo local vigila el \
mercado y solo te consulta cuando detecta una señal de alta probabilidad que ya \
superó un primer filtro de costos. Tu papel es la validación final: escéptica, \
independiente y orientada a proteger el capital.

Cómo decidir:
- Aprueba solo si la configuración es claramente favorable después de costos. \
Ante datos contradictorios o un contexto desfavorable (tendencia agotada, \
resistencia cercana, mechas de rechazo, volumen anómalo, volatilidad extrema), \
rechaza: rechazar no cuesta nada y una mala operación sí.
- win_probability es tu estimación calibrada de que el precio toque el \
take_profit antes que el stop_loss. El sistema la compara localmente con la \
probabilidad de equilibrio derivada de las comisiones; una estimación inflada \
se traduce en pérdidas reales.
- stop_loss y take_profit: devuelve los niveles propuestos o ajústalos si la \
estructura del precio lo justifica (por ejemplo, SL bajo un soporte claro). \
Deben respetar el bloque "constraints"; si no lo hacen, la operación se descarta.
- rationale: como máximo 3 frases en español con los factores decisivos.
- risk_flags: riesgos concretos y breves (lista vacía si no hay)."""

EXIT_SYSTEM_PROMPT = """\
Eres el comité de inversiones de un sistema de trading algorítmico en Binance \
Spot. Revisas una posición larga abierta que ya está protegida en el exchange \
por una orden OCO con stop_loss y take_profit. El motor local detectó una \
alerta de deterioro y pide tu criterio.

- HOLD: mantener la posición; el SL y el TP existentes siguen protegiéndola.
- CLOSE: cerrar ahora a mercado, pagando comisión taker y deslizamiento. Elige \
CLOSE solo si consideras claramente más probable tocar el stop_loss que el \
take_profit, teniendo en cuenta el resultado no realizado y los costos de salida.
- rationale: como máximo 3 frases en español. risk_flags: lista breve."""


# --------------------------------------------------------------------------- #
@dataclass
class CommitteeResult:
    verdict: EntryVerdict | ExitVerdict | None
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str | None = None
    request_id: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.verdict is not None and self.error is None

    @property
    def approved(self) -> bool:
        return self.ok and getattr(self.verdict, "decision", None) == "APPROVE"


def _sig(x: float, digits: int = 6) -> float:
    return float(f"{x:.{digits}g}") if math.isfinite(x) else x


def build_market_context(df: pd.DataFrame, candles: int = 24) -> dict[str, Any]:
    """Contexto compacto del mercado (pocos tokens = consulta barata)."""
    recent = df.tail(candles)
    window = df.tail(100)
    close = float(df["close"].iloc[-1])
    return {
        "last_close": _sig(close),
        "change_pct_window": round((close / float(recent["close"].iloc[0]) - 1) * 100, 3),
        "range_100": {"high": _sig(float(window["high"].max())), "low": _sig(float(window["low"].min()))},
        "dist_to_high_100_pct": round((float(window["high"].max()) / close - 1) * 100, 3),
        "candles_ohlcv": [
            [ts.strftime("%m-%d %H:%M"), _sig(r.open), _sig(r.high), _sig(r.low), _sig(r.close), _sig(r.volume, 4)]
            for ts, r in recent.iterrows()
        ],
    }


class InvestmentCommittee:
    def __init__(self, settings: AISettings, client: Any | None = None):
        self.s = settings
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            kwargs: dict[str, Any] = {"timeout": self.s.timeout_seconds, "max_retries": 2}
            if self.s.api_key:
                kwargs["api_key"] = self.s.api_key
            self._client = anthropic.Anthropic(**kwargs)
        return self._client

    def estimated_call_cost(self) -> float:
        return self.s.estimated_call_cost_usd()

    # ------------------------------------------------------------------ #
    def review_entry(
        self,
        *,
        signal: Signal,
        plan: TradePlan,
        costs: CostBreakdown,
        market_context: dict[str, Any],
        constraints: dict[str, float],
        environment: str,
    ) -> CommitteeResult:
        payload = {
            "task": "validar_entrada_larga",
            "environment": environment,
            "symbol": signal.symbol,
            "candle_close_utc": signal.candle_time.isoformat(),
            "local_signal": {
                "score": signal.score,
                "reasons": list(signal.reasons),
                "indicators": signal.features,
            },
            "proposed_trade": {
                "entry_price": _sig(plan.entry_price),
                "stop_loss": _sig(plan.stop_loss),
                "take_profit": _sig(plan.take_profit),
                "reward_risk": round(plan.reward_risk, 3),
                "quantity": plan.quantity,
                "notional_usd": round(plan.notional, 2),
                "risk_usd": round(plan.risk_amount, 4),
            },
            "costs_usd": {
                "entry_fee": round(costs.entry_fee, 6),
                "tp_exit_fee": round(costs.tp_exit_fee, 6),
                "sl_exit_fee": round(costs.sl_exit_fee, 6),
                "slippage_estimate": round(costs.entry_slippage + costs.sl_slippage, 6),
                "ai_cost": round(costs.ai_cost, 6),
                "net_profit_at_tp": round(costs.net_profit_tp, 4),
                "net_loss_at_sl": round(costs.net_loss_sl, 4),
            },
            "constraints": constraints,
            "market": market_context,
        }
        return self._consult(ENTRY_SYSTEM_PROMPT, payload, ENTRY_SCHEMA, EntryVerdict)

    def review_exit(
        self,
        *,
        position: dict[str, Any],
        last_price: float,
        alert: str,
        indicators: dict[str, float],
        market_context: dict[str, Any],
        exit_cost_usd: float,
    ) -> CommitteeResult:
        entry = float(position["entry_price"])
        payload = {
            "task": "revisar_salida",
            "symbol": position["symbol"],
            "alert": alert,
            "position": {
                "entry_price": _sig(entry),
                "stop_loss": _sig(float(position["stop_loss"])),
                "take_profit": _sig(float(position["take_profit"])),
                "quantity": position["quantity"],
                "opened_at_utc": position.get("opened_at"),
                "unrealized_pnl_pct": round((last_price / entry - 1) * 100, 3),
            },
            "last_price": _sig(last_price),
            "exit_now_cost_usd": round(exit_cost_usd, 6),
            "indicators": indicators,
            "market": market_context,
        }
        return self._consult(EXIT_SYSTEM_PROMPT, payload, EXIT_SCHEMA, ExitVerdict)

    # ------------------------------------------------------------------ #
    def _consult(
        self,
        system: str,
        payload: dict[str, Any],
        schema: dict[str, Any],
        model_cls: type[BaseModel],
    ) -> CommitteeResult:
        params: dict[str, Any] = {
            "model": self.s.model,
            "max_tokens": self.s.max_tokens,
            "system": system,
            "messages": [
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))}
            ],
            "thinking": {"type": "adaptive"},
            "output_config": {
                "effort": self.s.effort,
                "format": {"type": "json_schema", "schema": schema},
            },
        }
        try:
            if self.s.use_server_fallbacks:
                # Si el modelo declina por política, el servidor reintenta con el
                # modelo de respaldo recomendado dentro de la misma llamada.
                response = self.client.beta.messages.create(
                    betas=[FALLBACK_BETA], fallbacks="default", **params
                )
            else:
                response = self.client.messages.create(**params)
        except anthropic.RateLimitError as exc:
            return CommitteeResult(None, error=f"límite de tasa de la API: {exc.message}")
        except anthropic.BadRequestError as exc:
            return CommitteeResult(None, error=f"petición inválida: {exc.message}")
        except anthropic.APIStatusError as exc:
            return CommitteeResult(None, error=f"error API {exc.status_code}: {exc.message}")
        except anthropic.APIConnectionError as exc:
            return CommitteeResult(None, error=f"sin conexión con la API: {exc}")

        result = CommitteeResult(
            None,
            cost_usd=self._cost_usd(response),
            input_tokens=int(getattr(response.usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(response.usage, "output_tokens", 0) or 0),
            model=getattr(response, "model", None),
            request_id=getattr(response, "_request_id", None),
        )
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            result.error = f"el modelo declinó (categoría={getattr(details, 'category', None)})"
            return result
        if response.stop_reason == "max_tokens":
            result.error = "respuesta truncada (max_tokens)"
            return result

        text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), None)
        if not text:
            result.error = "respuesta sin bloque de texto"
            return result
        try:
            result.verdict = model_cls.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as exc:
            result.error = f"JSON inválido del comité: {exc}"
        return result

    # ------------------------------------------------------------------ #
    def _tokens_cost(self, model: str | None, usage: Any) -> float:
        price_in, price_out = self.s.price_for(model or self.s.model)
        fresh = int(getattr(usage, "input_tokens", 0) or 0)
        cache_write = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        output = int(getattr(usage, "output_tokens", 0) or 0)  # incluye thinking
        input_equiv = fresh + 1.25 * cache_write + 0.1 * cache_read
        return (input_equiv * price_in + output * price_out) / 1_000_000

    def _cost_usd(self, response: Any) -> float:
        usage = response.usage
        iterations = getattr(usage, "iterations", None)
        if iterations:
            # Con fallback, cada tramo se factura a la tarifa de su propio modelo.
            # Un tramo sin modelo explícito corresponde al modelo solicitado.
            return sum(
                self._tokens_cost(getattr(it, "model", None) or self.s.model, it)
                for it in iterations
            )
        return self._tokens_cost(getattr(response, "model", None), usage)
