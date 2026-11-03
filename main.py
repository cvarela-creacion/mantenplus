"""Punto de entrada del bot.

Uso:
    python main.py --check     # diagnóstico de conexión (entorno, mercados, saldo)
    python main.py --once      # ejecuta un solo ciclo y termina
    python main.py             # bucle continuo (Ctrl+C para detener)
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from logging.handlers import RotatingFileHandler

import ccxt

from tradingbot.ai_committee import InvestmentCommittee
from tradingbot.config import ConfigError, Settings
from tradingbot.engine import TradingEngine
from tradingbot.exchange import ExchangeClient
from tradingbot.state import StateStore


def setup_logging(settings: Settings) -> None:
    log_dir = settings.env_state_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    file_handler = RotatingFileHandler(log_dir / "bot.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.handlers[:] = [console, file_handler]
    # Las librerías HTTP son muy verbosas en DEBUG.
    for noisy in ("ccxt", "urllib3", "httpx", "httpx2", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def banner(settings: Settings) -> None:
    log = logging.getLogger("main")
    if settings.exchange.sandbox_mode:
        log.info("=== MODO TESTNET (dinero virtual) ===")
    elif settings.trading.dry_run:
        log.info("=== PRODUCCIÓN en DRY_RUN: datos reales, sin enviar órdenes ===")
    else:
        log.warning("!!! MODO PRODUCCIÓN: SE OPERA CON DINERO REAL !!!")
    log.info(settings.describe())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bot de trading híbrido (Python + comité IA)")
    parser.add_argument("--env-file", default=".env", help="Archivo de configuración (por defecto .env)")
    parser.add_argument("--check", action="store_true", help="Solo verificar conexión y saldo")
    parser.add_argument("--once", action="store_true", help="Ejecutar un único ciclo")
    args = parser.parse_args(argv)

    try:
        settings = Settings.from_env(args.env_file)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2

    setup_logging(settings)
    banner(settings)
    exchange = ExchangeClient(settings.exchange)

    log = logging.getLogger("main")
    try:
        if args.check:
            for key, value in exchange.check_connectivity(settings.trading.quote_currency).items():
                print(f"{key:>16}: {value}")
            return 0
        settings.require_trading_credentials()
        exchange.load_markets()
    except ConfigError as exc:
        log.error(str(exc))
        return 2
    except ccxt.AuthenticationError as exc:
        log.error("Llaves API rechazadas por %s (¿son del entorno correcto?): %s", exchange.environment, exc)
        return 3
    except ccxt.BaseError as exc:
        log.error("No se pudo conectar con el exchange (%s): %s", exchange.environment, exc)
        return 3
    engine = TradingEngine(
        settings,
        exchange,
        InvestmentCommittee(settings.ai),
        StateStore(settings.env_state_dir),
    )

    if args.once:
        engine.run_cycle()
        return 0

    stop = threading.Event()

    def _graceful(signum, _frame):  # noqa: ANN001
        logging.getLogger("main").info("Señal %s recibida: deteniendo tras el ciclo actual...", signum)
        stop.set()

    signal.signal(signal.SIGINT, _graceful)
    signal.signal(signal.SIGTERM, _graceful)
    engine.run_forever(stop)
    return 0


if __name__ == "__main__":
    sys.exit(main())
