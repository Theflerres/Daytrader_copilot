"""
Logging estruturado em JSON com rotação por canal (captura, OCR, LLM, risco, dashboard).
Mantém também o log legado texto em copilot.log se desejado.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonLineFormatter(logging.Formatter):
    """Uma linha JSON por evento (adequado para ingestão futura)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        extra = getattr(record, "structured", None)
        if isinstance(extra, dict):
            payload["data"] = extra
        return json.dumps(payload, ensure_ascii=False)


def setup_channel_logging(log_dir: str | Path, level_name: str = "INFO", max_bytes: int = 5_000_000, backup_count: int = 5) -> None:
    """
    Configura loggers filhos `copilot.<canal>` com arquivo JSON rotativo.
    Canais: capture, ocr, llm, risk, dashboard
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, level_name.upper(), logging.INFO)

    channels = ("capture", "ocr", "llm", "risk", "dashboard")
    for ch in channels:
        lg = logging.getLogger(f"copilot.{ch}")
        lg.handlers.clear()
        lg.setLevel(level)
        lg.propagate = False
        path = log_dir / f"{ch}.jsonl"
        fh = logging.handlers.RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        fh.setFormatter(JsonLineFormatter())
        lg.addHandler(fh)

    # Raiz: opcionalmente não poluir — main.py pode continuar com setup_logging legado
    logging.getLogger("copilot").setLevel(level)


def log_structured(logger_name: str, level: int, message: str, **data: Any) -> None:
    """Helper: log em logger copilot.<nome> com campo structured."""
    lg = logging.getLogger(f"copilot.{logger_name}")
    extra = {"structured": data} if data else {}
    lg.log(level, message, extra=extra)
