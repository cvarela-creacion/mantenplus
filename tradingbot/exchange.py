"""Capa de conexión con el exchange vía ``ccxt``, agnóstica al entorno.

Es el ÚNICO módulo que sabe si se opera en Testnet o en Producción: el resto
del sistema usa la misma interfaz en ambos casos.

Protección SL/TP: tras cada compra se coloca en Binance una orden **OCO**
(One-Cancels-the-Other) de venta con dos patas:
  * TP: ``LIMIT_MAKER`` por encima del precio (comisión maker).
  * SL: ``STOP_LOSS`` (stop de mercado) o ``STOP_LOSS_LIMIT`` por debajo.
Así la posición queda protegida en el propio exchange aunque el bot se caiga.
"""

from __future__ import annotations

import logging
from typing import Any

import ccxt
import pandas as pd

from .config import ExchangeSettings
from .risk import MarketLimits

log = logging.getLogger(__name__)

TIMEFRAME_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "6h": 21_600_000,
    "8h": 28_800_000, "12h": 43_200_000, "1d": 86_400_000,
}


class ExchangeClient:
    def __init__(self, settings: ExchangeSettings, ccxt_exchange: Any | None = None):
        self.settings = settings
        self.ex = ccxt_exchange if ccxt_exchange is not None else self._build(settings)
        self._markets_loaded = False

    # ------------------------------------------------------------------ #
    # Construcción
    # ------------------------------------------------------------------ #
    @staticmethod
    def _build(s: ExchangeSettings) -> Any:
        exchange_cls = getattr(ccxt, s.exchange_id)
        config: dict[str, Any] = {
            "enableRateLimit": True,
            "timeout": s.timeout_ms,
            "options": {"defaultType": "spot", "adjustForTimeDifference": True},
        }
        if s.has_credentials:
            config["apiKey"] = s.api_key
            config["secret"] = s.api_secret
        ex = exchange_cls(config)
        if s.sandbox_mode:
            # Redirige todas las URLs a https://testnet.binance.vision
            ex.set_sandbox_mode(True)
        return ex

    @property
    def environment(self) -> str:
        return self.settings.environment

    @property
    def is_sandbox(self) -> bool:
        return self.settings.sandbox_mode

    def load_markets(self, reload: bool = False) -> dict:
        markets = self.ex.load_markets(reload)
        self._markets_loaded = True
        return markets

    def _market(self, symbol: str) -> dict:
        if not self._markets_loaded:
            self.load_markets()
        return self.ex.market(symbol)

    # ------------------------------------------------------------------ #
    # Datos de mercado (públicos, sin costo)
    # ------------------------------------------------------------------ #
    def fetch_ohlcv_df(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """OHLCV con SOLO velas cerradas (se descarta la vela en formación para
        evitar señales que "repintan")."""
        rows = self.ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit + 1)
        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        if df.empty:
            return df
        tf_ms = TIMEFRAME_MS.get(timeframe)
        now_ms = self.ex.milliseconds()
        if tf_ms and df["timestamp"].iloc[-1] + tf_ms > now_ms:
            df = df.iloc[:-1]
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("timestamp").astype(float)
        return df.tail(limit)

    def fetch_last_price(self, symbol: str) -> float:
        ticker = self.ex.fetch_ticker(symbol)
        price = ticker.get("last") or ticker.get("close")
        if not price:
            raise ccxt.ExchangeError(f"Ticker sin precio para {symbol}")
        return float(price)

    def market_limits(self, symbol: str) -> MarketLimits:
        limits = self._market(symbol).get("limits", {})
        return MarketLimits(
            min_amount=(limits.get("amount") or {}).get("min"),
            min_cost=(limits.get("cost") or {}).get("min"),
        )

    def amount_to_precision(self, symbol: str, amount: float) -> float:
        return float(self.ex.amount_to_precision(symbol, amount))  # trunca

    def price_to_precision(self, symbol: str, price: float) -> float:
        return float(self.ex.price_to_precision(symbol, price))

    def get_fee_rates(self, symbol: str, default_maker: float, default_taker: float) -> tuple[float, float]:
        """Comisiones reales de la cuenta en producción; en testnet (no expone el
        endpoint) o ante error, las configuradas. Nunca usa una comisión menor
        que la configurada: ante la duda, estimación conservadora."""
        if self.is_sandbox or not self.settings.has_credentials:
            return default_maker, default_taker
        try:
            fee = self.ex.fetch_trading_fee(symbol)
            maker = float(fee.get("maker", default_maker))
            taker = float(fee.get("taker", default_taker))
            return max(maker, 0.0), max(taker, 0.0)
        except Exception as exc:  # noqa: BLE001 - degradamos a la configuración
            log.debug("No se pudo leer la comisión de %s: %s", symbol, exc)
            return default_maker, default_taker

    # ------------------------------------------------------------------ #
    # Cuenta
    # ------------------------------------------------------------------ #
    def fetch_balances(self) -> dict:
        return self.ex.fetch_balance()

    def free_balance(self, asset: str, balances: dict | None = None) -> float:
        b = balances or self.fetch_balances()
        return float((b.get(asset) or {}).get("free") or 0.0)

    def equity_in_quote(self, quote: str, symbols: tuple[str, ...], balances: dict | None = None) -> float:
        """Capital total aproximado = quote total + activos base valorados."""
        b = balances or self.fetch_balances()
        equity = float((b.get(quote) or {}).get("total") or 0.0)
        for symbol in symbols:
            base = symbol.split("/")[0]
            qty = float((b.get(base) or {}).get("total") or 0.0)
            if qty > 0:
                equity += qty * self.fetch_last_price(symbol)
        return equity

    # ------------------------------------------------------------------ #
    # Órdenes
    # ------------------------------------------------------------------ #
    def market_buy(self, symbol: str, amount: float) -> dict:
        qty = self.amount_to_precision(symbol, amount)
        log.info("[%s] COMPRA mercado %s %s", self.environment, qty, symbol)
        return self.ex.create_order(symbol, "market", "buy", qty)

    def market_sell(self, symbol: str, amount: float) -> dict:
        qty = self.amount_to_precision(symbol, amount)
        log.info("[%s] VENTA mercado %s %s", self.environment, qty, symbol)
        return self.ex.create_order(symbol, "market", "sell", qty)

    def fetch_order(self, order_id: str, symbol: str) -> dict:
        return self.ex.fetch_order(order_id, symbol)

    def place_oco_sell(
        self,
        symbol: str,
        amount: float,
        take_profit: float,
        stop_loss: float,
        stop_type: str = "STOP_LOSS",
        stop_limit_buffer_pct: float = 0.002,
    ) -> dict:
        """Coloca la protección SL/TP como OCO de venta (POST /api/v3/orderList/oco)."""
        market = self._market(symbol)
        if stop_type == "STOP_LOSS" and "STOP_LOSS" not in (market.get("info", {}).get("orderTypes") or ["STOP_LOSS"]):
            log.warning("%s no admite STOP_LOSS; se usa STOP_LOSS_LIMIT", symbol)
            stop_type = "STOP_LOSS_LIMIT"

        params: dict[str, Any] = {
            "symbol": market["id"],
            "side": "SELL",
            "quantity": self.ex.amount_to_precision(symbol, amount),
            "aboveType": "LIMIT_MAKER",
            "abovePrice": self.ex.price_to_precision(symbol, take_profit),
            "belowType": stop_type,
            "belowStopPrice": self.ex.price_to_precision(symbol, stop_loss),
            "newOrderRespType": "RESULT",
        }
        if stop_type == "STOP_LOSS_LIMIT":
            params["belowPrice"] = self.ex.price_to_precision(
                symbol, stop_loss * (1 - stop_limit_buffer_pct)
            )
            params["belowTimeInForce"] = "GTC"
        log.info(
            "[%s] OCO venta %s %s TP=%s SL=%s (%s)",
            self.environment, params["quantity"], symbol,
            params["abovePrice"], params["belowStopPrice"], stop_type,
        )
        return self.ex.private_post_orderlist_oco(params)

    def fetch_oco(self, order_list_id: str | int) -> dict:
        return self.ex.private_get_orderlist({"orderListId": order_list_id})

    def cancel_oco(self, symbol: str, order_list_id: str | int) -> dict:
        market = self._market(symbol)
        return self.ex.private_delete_orderlist({"symbol": market["id"], "orderListId": order_list_id})

    def oco_fill(self, symbol: str, order_list_id: str | int) -> dict | None:
        """Si el OCO terminó, devuelve la pata ejecutada: {'leg','price','amount','fee'}.
        ``None`` si sigue activo."""
        info = self.fetch_oco(order_list_id)
        if info.get("listOrderStatus") != "ALL_DONE":
            return None
        for leg in info.get("orders", []):
            order = self.fetch_order(str(leg["orderId"]), symbol)
            if order.get("status") == "closed" and float(order.get("filled") or 0) > 0:
                raw_type = str(order.get("info", {}).get("type", "")).upper()
                fee = order.get("fee") or {}
                return {
                    "leg": "take_profit" if raw_type == "LIMIT_MAKER" else "stop_loss",
                    "price": float(order.get("average") or order.get("price") or 0.0),
                    "amount": float(order["filled"]),
                    "fee_cost": float(fee.get("cost") or 0.0),
                    "fee_currency": fee.get("currency"),
                }
        return {"leg": "cancelled", "price": 0.0, "amount": 0.0, "fee_cost": 0.0, "fee_currency": None}

    # ------------------------------------------------------------------ #
    def check_connectivity(self, quote: str) -> dict:
        """Diagnóstico rápido: mercados, hora del servidor y saldo (si hay llaves)."""
        markets = self.load_markets()
        report: dict[str, Any] = {
            "environment": self.environment,
            "api_url": self.ex.urls.get("api", {}).get("public"),
            "markets": len(markets),
            "server_time": self.ex.iso8601(self.ex.fetch_time()),
        }
        if self.settings.has_credentials:
            report[f"free_{quote}"] = self.free_balance(quote)
        else:
            report["warning"] = "sin llaves API: solo datos públicos"
        return report
