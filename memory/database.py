"""Conexão SQLite + factory de sessão."""
from __future__ import annotations

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import (  # noqa: F401 - metadados
    Analysis,
    Base,
    MarketReaction,
    MetricEvent,
    OperatorFeedback,
    OperatorLog,
    PatternRecord,
)

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


def get_engine(db_path: str):
    """Cria ou reutiliza engine SQLite."""
    global _engine, _SessionLocal
    if _engine is None:
        url = f"sqlite:///{db_path}"
        _engine = create_engine(url, echo=False, future=True)
        Base.metadata.create_all(_engine)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)
        logger.info("Banco inicializado em %s", db_path)
    return _engine


@contextmanager
def session_scope(db_path: str):
    """Context manager de sessão com commit/rollback seguros."""
    get_engine(db_path)
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
