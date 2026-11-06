"""Persistencia del estado del bot (posiciones, contabilidad de IA, PnL diario).

El estado se guarda en ``state/<entorno>/state.json`` con escritura atómica, de
modo que un reinicio no "olvida" posiciones abiertas ni el gasto de IA del día.
Cada operación cerrada se agrega a ``trades.jsonl`` para análisis posterior.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class StateStore:
    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / "state.json"
        self.journal_path = self.dir / "trades.jsonl"
        self.data: dict[str, Any] = {
            "positions": {},
            "ai_ledger": {},
            "daily": {},
            "last_candle": {},
        }
        self.load()

    # ------------------------------------------------------------------ #
    def load(self) -> None:
        if self.state_path.exists():
            with self.state_path.open(encoding="utf-8") as fh:
                loaded = json.load(fh)
            self.data.update(loaded)

    def save(self) -> None:
        fd, tmp = tempfile.mkstemp(dir=self.dir, prefix=".state-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2, ensure_ascii=False, default=str)
            os.replace(tmp, self.state_path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def append_journal(self, record: dict[str, Any]) -> None:
        with self.journal_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    # -- posiciones ------------------------------------------------------- #
    @property
    def positions(self) -> dict[str, dict[str, Any]]:
        return self.data["positions"]

    def set_position(self, symbol: str, position: dict[str, Any]) -> None:
        self.positions[symbol] = position
        self.save()

    def remove_position(self, symbol: str) -> dict[str, Any] | None:
        pos = self.positions.pop(symbol, None)
        self.save()
        return pos

    # -- PnL diario ------------------------------------------------------- #
    def daily(self, day: str) -> dict[str, float]:
        return self.data["daily"].setdefault(day, {"realized_pnl": 0.0, "start_equity": 0.0})

    def add_realized_pnl(self, day: str, pnl: float) -> None:
        self.daily(day)["realized_pnl"] += pnl
        self.save()
