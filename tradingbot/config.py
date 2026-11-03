"""Gestión centralizada de configuración.

Toda la configuración se lee de variables de entorno (o de un archivo ``.env``).
El interruptor principal es ``SANDBOX_MODE``:

* ``SANDBOX_MODE=true``  -> Binance Spot Testnet (dinero virtual).
* ``SANDBOX_MODE=false`` -> Binance producción (dinero real).

La lógica de negocio nunca consulta en qué entorno está; solo el módulo
``exchange`` usa este valor para construir el cliente ``ccxt``. Así se cambia de
entorno sin tocar el código.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

LIVE_CONFIRMATION_PHRASE = "YES_I_UNDERSTAND_REAL_MONEY"

# Precios por millón de tokens (USD) de los modelos que pueden atender una
# consulta: el modelo configurado y los posibles modelos de respaldo
# (fallback) del servidor. Se usan para calcular el costo real de cada consulta.
DEFAULT_MODEL_PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


class ConfigError(ValueError):
    """Configuración inválida o insegura."""


# --------------------------------------------------------------------------- #
# Lectura tipada de variables de entorno
# --------------------------------------------------------------------------- #
def _str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "y", "on", "si", "sí"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigError(f"{name}={raw!r} no es un booleano válido")


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name}={raw!r} no es un número válido") from exc


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name}={raw!r} no es un entero válido") from exc


def _list(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(item.strip().upper() for item in raw.split(",") if item.strip())


# --------------------------------------------------------------------------- #
# Bloques de configuración
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ExchangeSettings:
    sandbox_mode: bool = True
    api_key: str = field(default="", repr=False)
    api_secret: str = field(default="", repr=False)
    exchange_id: str = "binance"
    timeout_ms: int = 15_000

    @property
    def environment(self) -> str:
        return "TESTNET" if self.sandbox_mode else "PRODUCTION"

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_key and self.api_secret)


@dataclass(frozen=True)
class TradingSettings:
    symbols: tuple[str, ...] = ("BTC/USDT", "ETH/USDT")
    timeframe: str = "15m"
    ohlcv_limit: int = 300
    poll_interval_seconds: int = 30
    quote_currency: str = "USDT"
    # DRY_RUN: calcula señales, consulta a la IA y simula posiciones, pero no
    # envía órdenes al exchange (ni siquiera al testnet).
    dry_run: bool = False
    # Si el precio se aleja más que esto del precio de la señal antes de
    # ejecutar, se recalcula el plan (y se aborta si deja de ser rentable).
    max_entry_drift_pct: float = 0.003
    # Capital virtual inicial para DRY_RUN (simulación con datos reales).
    paper_equity: float = 1_000.0


@dataclass(frozen=True)
class StrategySettings:
    ema_fast: int = 21
    ema_mid: int = 50
    ema_slow: int = 200
    rsi_period: int = 14
    rsi_min: float = 45.0
    rsi_max: float = 68.0
    adx_min: float = 20.0
    volume_ratio_min: float = 1.3
    min_atr_pct: float = 0.0025
    max_atr_pct: float = 0.05
    # Puntaje mínimo (0..1) de confluencia local para considerar la señal
    # "de alta probabilidad" y, solo entonces, pagar una consulta a la IA.
    min_signal_score: float = 0.75


@dataclass(frozen=True)
class RiskSettings:
    risk_per_trade_pct: float = 0.01  # 1 % del capital arriesgado por operación
    max_position_pct: float = 0.25  # nocional máximo por posición
    max_open_positions: int = 2
    max_daily_loss_pct: float = 0.03  # "kill switch" diario
    min_reward_risk: float = 1.8
    atr_sl_multiplier: float = 1.5
    atr_tp_multiplier: float = 3.0
    min_sl_pct: float = 0.004  # SL demasiado ajustado = ruido
    max_sl_pct: float = 0.04  # SL demasiado lejano = riesgo excesivo
    # STOP_LOSS (stop de mercado: garantiza la salida) o STOP_LOSS_LIMIT.
    stop_loss_order_type: str = "STOP_LOSS"
    stop_limit_buffer_pct: float = 0.002


@dataclass(frozen=True)
class CostSettings:
    # Comisiones por defecto de Binance Spot (nivel VIP 0). En producción se
    # intenta leer la comisión real de la cuenta; en testnet se usan estas.
    maker_fee: float = 0.001
    taker_fee: float = 0.001
    slippage_pct: float = 0.0005  # por cada ejecución a mercado
    # Beneficio bruto en TP / costos totales. 3.0 = los costos no pueden
    # comerse más de un tercio de la ganancia ("holgadamente").
    min_profit_to_cost_ratio: float = 3.0
    # Probabilidad de equilibrio máxima aceptable antes de consultar a la IA.
    max_breakeven_probability: float = 0.45
    # Ventaja mínima de la probabilidad estimada por la IA sobre la de equilibrio.
    min_probability_edge: float = 0.05
    # Valor esperado neto mínimo, expresado como múltiplo de los costos totales.
    min_ev_to_cost_ratio: float = 1.0


@dataclass(frozen=True)
class AISettings:
    enabled: bool = True
    api_key: str = field(default="", repr=False)
    model: str = "claude-opus-5-5"
    effort: str = "medium"  # low | medium | high | xhigh | max
    max_tokens: int = 16_000
    timeout_seconds: float = 120.0
    use_server_fallbacks: bool = True
    # Estimación previa (antes de llamar) del consumo de una consulta.
    estimated_input_tokens: int = 2_500
    estimated_output_tokens: int = 3_000
    daily_budget_usd: float = 2.00
    symbol_cooldown_minutes: int = 60
    exit_review_cooldown_minutes: int = 120
    # Tasa de aprobación inicial supuesta para amortizar el costo de las
    # consultas rechazadas sobre las operaciones que sí se ejecutan.
    prior_approval_rate: float = 0.35
    model_prices_per_mtok: dict[str, tuple[float, float]] = field(
        default_factory=lambda: dict(DEFAULT_MODEL_PRICES_PER_MTOK)
    )

    def price_for(self, model: str | None) -> tuple[float, float]:
        """Precio (entrada, salida) por MTok; si el modelo es desconocido, el
        más caro de la tabla (estimación conservadora)."""
        if model and model in self.model_prices_per_mtok:
            return self.model_prices_per_mtok[model]
        return max(self.model_prices_per_mtok.values(), key=lambda p: p[1])

    def estimated_call_cost_usd(self) -> float:
        price_in, price_out = self.price_for(self.model)
        return (
            self.estimated_input_tokens * price_in
            + self.estimated_output_tokens * price_out
        ) / 1_000_000


@dataclass(frozen=True)
class Settings:
    exchange: ExchangeSettings
    trading: TradingSettings
    strategy: StrategySettings
    risk: RiskSettings
    costs: CostSettings
    ai: AISettings
    state_dir: Path = Path("state")
    log_level: str = "INFO"
    live_trading_confirmation: str = field(default="", repr=False)

    # ----------------------------------------------------------------- #
    @classmethod
    def from_env(cls, env_file: str | os.PathLike[str] | None = ".env") -> "Settings":
        if env_file:
            load_dotenv(env_file, override=False)

        sandbox = _bool("SANDBOX_MODE", True)
        # Credenciales separadas por entorno: imposible usar por error las
        # llaves reales en pruebas o viceversa.
        if sandbox:
            key, secret = _str("BINANCE_TESTNET_API_KEY"), _str("BINANCE_TESTNET_API_SECRET")
        else:
            key, secret = _str("BINANCE_API_KEY"), _str("BINANCE_API_SECRET")

        exchange = ExchangeSettings(sandbox_mode=sandbox, api_key=key, api_secret=secret)
        trading = TradingSettings(
            symbols=_list("SYMBOLS", "BTC/USDT,ETH/USDT"),
            timeframe=_str("TIMEFRAME", "15m"),
            ohlcv_limit=_int("OHLCV_LIMIT", 300),
            poll_interval_seconds=_int("POLL_INTERVAL_SECONDS", 30),
            quote_currency=_str("QUOTE_CURRENCY", "USDT").upper(),
            dry_run=_bool("DRY_RUN", False),
            max_entry_drift_pct=_float("MAX_ENTRY_DRIFT_PCT", 0.003),
            paper_equity=_float("PAPER_EQUITY", 1_000.0),
        )
        strategy = StrategySettings(
            min_signal_score=_float("MIN_SIGNAL_SCORE", 0.75),
            volume_ratio_min=_float("VOLUME_RATIO_MIN", 1.3),
            adx_min=_float("ADX_MIN", 20.0),
        )
        risk = RiskSettings(
            risk_per_trade_pct=_float("RISK_PER_TRADE_PCT", 0.01),
            max_position_pct=_float("MAX_POSITION_PCT", 0.25),
            max_open_positions=_int("MAX_OPEN_POSITIONS", 2),
            max_daily_loss_pct=_float("MAX_DAILY_LOSS_PCT", 0.03),
            min_reward_risk=_float("MIN_REWARD_RISK", 1.8),
            atr_sl_multiplier=_float("ATR_SL_MULTIPLIER", 1.5),
            atr_tp_multiplier=_float("ATR_TP_MULTIPLIER", 3.0),
            min_sl_pct=_float("MIN_SL_PCT", 0.004),
            max_sl_pct=_float("MAX_SL_PCT", 0.04),
            stop_loss_order_type=_str("STOP_LOSS_ORDER_TYPE", "STOP_LOSS").upper(),
        )
        costs = CostSettings(
            maker_fee=_float("MAKER_FEE", 0.001),
            taker_fee=_float("TAKER_FEE", 0.001),
            slippage_pct=_float("SLIPPAGE_PCT", 0.0005),
            min_profit_to_cost_ratio=_float("MIN_PROFIT_TO_COST_RATIO", 3.0),
            max_breakeven_probability=_float("MAX_BREAKEVEN_PROBABILITY", 0.45),
            min_probability_edge=_float("MIN_PROBABILITY_EDGE", 0.05),
            min_ev_to_cost_ratio=_float("MIN_EV_TO_COST_RATIO", 1.0),
        )
        ai = AISettings(
            enabled=_bool("AI_ENABLED", True),
            api_key=_str("ANTHROPIC_API_KEY"),
            model=_str("AI_MODEL", "claude-opus-5-5"),
            effort=_str("AI_EFFORT", "medium").lower(),
            max_tokens=_int("AI_MAX_TOKENS", 16_000),
            timeout_seconds=_float("AI_TIMEOUT_SECONDS", 120.0),
            use_server_fallbacks=_bool("AI_USE_SERVER_FALLBACKS", True),
            estimated_input_tokens=_int("AI_EST_INPUT_TOKENS", 2_500),
            estimated_output_tokens=_int("AI_EST_OUTPUT_TOKENS", 3_000),
            daily_budget_usd=_float("AI_DAILY_BUDGET_USD", 2.00),
            symbol_cooldown_minutes=_int("AI_SYMBOL_COOLDOWN_MINUTES", 60),
            exit_review_cooldown_minutes=_int("AI_EXIT_REVIEW_COOLDOWN_MINUTES", 120),
            prior_approval_rate=_float("AI_PRIOR_APPROVAL_RATE", 0.35),
        )
        settings = cls(
            exchange=exchange,
            trading=trading,
            strategy=strategy,
            risk=risk,
            costs=costs,
            ai=ai,
            state_dir=Path(_str("STATE_DIR", "state")),
            log_level=_str("LOG_LEVEL", "INFO").upper(),
            live_trading_confirmation=_str("CONFIRM_LIVE_TRADING"),
        )
        settings.validate()
        return settings

    # ----------------------------------------------------------------- #
    @property
    def env_state_dir(self) -> Path:
        """Estado separado por entorno: testnet y producción nunca se mezclan."""
        return self.state_dir / self.exchange.environment.lower()

    def validate(self) -> None:
        errors: list[str] = []
        r, c, a, t = self.risk, self.costs, self.ai, self.trading

        if not t.symbols:
            errors.append("SYMBOLS no puede estar vacío")
        for symbol in t.symbols:
            if not symbol.endswith(f"/{t.quote_currency}"):
                errors.append(f"{symbol} no cotiza en {t.quote_currency}")
        if not 0 < r.risk_per_trade_pct <= 0.05:
            errors.append("RISK_PER_TRADE_PCT debe estar en (0, 0.05]")
        if not 0 < r.max_position_pct <= 1:
            errors.append("MAX_POSITION_PCT debe estar en (0, 1]")
        if not 0 < r.max_daily_loss_pct <= 0.2:
            errors.append("MAX_DAILY_LOSS_PCT debe estar en (0, 0.2]")
        if r.max_open_positions < 1:
            errors.append("MAX_OPEN_POSITIONS debe ser >= 1")
        if r.min_reward_risk < 1.0:
            errors.append("MIN_REWARD_RISK debe ser >= 1.0")
        if not 0 < r.min_sl_pct < r.max_sl_pct < 0.5:
            errors.append("Se requiere 0 < MIN_SL_PCT < MAX_SL_PCT < 0.5")
        if r.stop_loss_order_type not in {"STOP_LOSS", "STOP_LOSS_LIMIT"}:
            errors.append("STOP_LOSS_ORDER_TYPE debe ser STOP_LOSS o STOP_LOSS_LIMIT")
        if c.min_profit_to_cost_ratio < 1.5:
            errors.append("MIN_PROFIT_TO_COST_RATIO < 1.5 no es 'holgado'")
        if not 0 <= c.maker_fee < 0.01 or not 0 <= c.taker_fee < 0.01:
            errors.append("Comisiones fuera de rango razonable")
        if a.effort not in {"low", "medium", "high", "xhigh", "max"}:
            errors.append("AI_EFFORT debe ser low|medium|high|xhigh|max")
        if a.enabled and a.daily_budget_usd <= 0:
            errors.append("AI_DAILY_BUDGET_USD debe ser > 0")

        # Salvaguarda de dinero real: exige confirmación explícita.
        if (
            not self.exchange.sandbox_mode
            and not t.dry_run
            and self.live_trading_confirmation != LIVE_CONFIRMATION_PHRASE
        ):
            errors.append(
                "SANDBOX_MODE=false opera con DINERO REAL. Define "
                f"CONFIRM_LIVE_TRADING={LIVE_CONFIRMATION_PHRASE} para continuar."
            )

        if errors:
            raise ConfigError("Configuración inválida:\n  - " + "\n  - ".join(errors))

    def require_trading_credentials(self) -> None:
        """Para enviar órdenes (no DRY_RUN) se necesitan llaves del entorno activo."""
        if not self.trading.dry_run and not self.exchange.has_credentials:
            prefix = "BINANCE_TESTNET_" if self.exchange.sandbox_mode else "BINANCE_"
            raise ConfigError(
                f"Faltan {prefix}API_KEY / {prefix}API_SECRET para operar en "
                f"{self.exchange.environment} (o activa DRY_RUN=true)."
            )

    def describe(self) -> str:
        """Resumen legible sin secretos."""
        return (
            f"Entorno={self.exchange.environment} dry_run={self.trading.dry_run} "
            f"símbolos={','.join(self.trading.symbols)} tf={self.trading.timeframe} "
            f"IA={'on' if self.ai.enabled else 'off'}({self.ai.model}, effort={self.ai.effort}) "
            f"riesgo/op={self.risk.risk_per_trade_pct:.2%} "
            f"R:R min={self.risk.min_reward_risk} "
            f"beneficio/costo min={self.costs.min_profit_to_cost_ratio}x"
        )
