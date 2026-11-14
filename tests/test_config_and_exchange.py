import pandas as pd
import pytest

from tradingbot.config import LIVE_CONFIRMATION_PHRASE, ConfigError, ExchangeSettings, Settings
from tradingbot.exchange import ExchangeClient

ENV_KEYS = ["SANDBOX_MODE", "DRY_RUN", "CONFIRM_LIVE_TRADING", "BINANCE_API_KEY", "BINANCE_API_SECRET",
            "BINANCE_TESTNET_API_KEY", "BINANCE_TESTNET_API_SECRET", "SYMBOLS", "AI_EFFORT"]


@pytest.fixture
def env(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("BINANCE_TESTNET_API_KEY", "test-key")
    monkeypatch.setenv("BINANCE_TESTNET_API_SECRET", "test-secret")
    monkeypatch.setenv("BINANCE_API_KEY", "live-key")
    monkeypatch.setenv("BINANCE_API_SECRET", "live-secret")
    return monkeypatch


def test_sandbox_uses_testnet_keys_and_urls(env):
    env.setenv("SANDBOX_MODE", "true")
    s = Settings.from_env(env_file=None)
    assert s.exchange.environment == "TESTNET" and s.exchange.api_key == "test-key"
    client = ExchangeClient(s.exchange)
    assert "testnet.binance.vision" in client.ex.urls["api"]["public"]
    assert s.env_state_dir.name == "testnet"


def test_production_requires_explicit_confirmation(env):
    env.setenv("SANDBOX_MODE", "false")
    with pytest.raises(ConfigError, match="DINERO REAL"):
        Settings.from_env(env_file=None)
    env.setenv("CONFIRM_LIVE_TRADING", LIVE_CONFIRMATION_PHRASE)
    s = Settings.from_env(env_file=None)
    assert s.exchange.environment == "PRODUCTION" and s.exchange.api_key == "live-key"
    assert "api.binance.com" in ExchangeClient(s.exchange).ex.urls["api"]["public"]


def test_production_dry_run_needs_no_confirmation(env):
    env.setenv("SANDBOX_MODE", "false")
    env.setenv("DRY_RUN", "true")
    assert Settings.from_env(env_file=None).trading.dry_run


def test_secrets_not_in_repr(env):
    s = Settings.from_env(env_file=None)
    assert "test-secret" not in repr(s) and "test-secret" not in s.describe()


@pytest.mark.parametrize("key,value", [("SANDBOX_MODE", "quizás"), ("AI_EFFORT", "turbo"),
                                       ("SYMBOLS", "BTC/EUR")])
def test_invalid_values_rejected(env, key, value):
    env.setenv(key, value)
    with pytest.raises(ConfigError):
        Settings.from_env(env_file=None)


# ------------------------------------------------------------ exchange -- #
class FakeCcxt:
    urls = {"api": {"public": "https://testnet.binance.vision/api/v3"}}

    def __init__(self, now_ms):
        self.now_ms = now_ms
        self.oco_params = None
        self.order_info = {}

    def milliseconds(self):
        return self.now_ms

    def fetch_ohlcv(self, symbol, timeframe, limit):
        base = 1_700_000_000_000
        return [[base + i * 900_000, 1, 2, 0.5, 1.5, 10] for i in range(5)]

    def load_markets(self, reload=False):
        return {"BTC/USDT": {}}

    def market(self, symbol):
        return {"id": "BTCUSDT", "info": {"orderTypes": ["LIMIT", "LIMIT_MAKER", "MARKET", "STOP_LOSS_LIMIT"]},
                "limits": {"amount": {"min": 0.00001}, "cost": {"min": 5.0}}}

    def amount_to_precision(self, symbol, amount):
        return f"{amount:.5f}"

    def price_to_precision(self, symbol, price):
        return f"{price:.2f}"

    def private_post_orderlist_oco(self, params):
        self.oco_params = params
        return {"orderListId": 7}

    def private_get_orderlist(self, params):
        return {"listOrderStatus": "ALL_DONE", "orders": [{"orderId": 1}, {"orderId": 2}]}

    def fetch_order(self, order_id, symbol):
        return self.order_info[order_id]


def test_ohlcv_drops_candle_in_formation():
    base = 1_700_000_000_000
    ex = ExchangeClient(ExchangeSettings(), ccxt_exchange=FakeCcxt(now_ms=base + 4 * 900_000 + 60_000))
    df = ex.fetch_ohlcv_df("BTC/USDT", "15m", limit=10)
    assert len(df) == 4  # la 5.ª vela aún no cerró
    assert isinstance(df.index, pd.DatetimeIndex) and str(df.index.tz) == "UTC"


def test_oco_falls_back_to_stop_limit_when_stop_market_unsupported():
    fake = FakeCcxt(now_ms=0)
    ex = ExchangeClient(ExchangeSettings(), ccxt_exchange=fake)
    ex.place_oco_sell("BTC/USDT", 0.01234, take_profit=104.0, stop_loss=98.0, stop_type="STOP_LOSS")
    p = fake.oco_params
    assert p["symbol"] == "BTCUSDT" and p["side"] == "SELL"
    assert p["aboveType"] == "LIMIT_MAKER" and p["abovePrice"] == "104.00"
    assert p["belowType"] == "STOP_LOSS_LIMIT" and p["belowStopPrice"] == "98.00"
    assert float(p["belowPrice"]) < 98.0 and p["belowTimeInForce"] == "GTC"


def test_oco_fill_identifies_take_profit_leg():
    fake = FakeCcxt(now_ms=0)
    fake.order_info = {
        "1": {"status": "canceled", "filled": 0, "info": {"type": "STOP_LOSS"}},
        "2": {"status": "closed", "filled": 0.5, "average": 104.0, "info": {"type": "LIMIT_MAKER"},
              "fee": {"cost": 0.052, "currency": "USDT"}},
    }
    fill = ExchangeClient(ExchangeSettings(), ccxt_exchange=fake).oco_fill("BTC/USDT", 7)
    assert fill["leg"] == "take_profit" and fill["price"] == 104.0 and fill["fee_currency"] == "USDT"


def test_testnet_uses_configured_fees_without_network():
    ex = ExchangeClient(ExchangeSettings(sandbox_mode=True, api_key="k", api_secret="s"), ccxt_exchange=FakeCcxt(0))
    assert ex.get_fee_rates("BTC/USDT", 0.001, 0.001) == (0.001, 0.001)
