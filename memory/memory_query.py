"""Busca contextos históricos semelhantes para enriquecer o prompt."""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Analysis, MarketReaction, PatternRecord

logger = logging.getLogger(__name__)


def fetch_recent_analyses(session: Session, asset: str, limit: int) -> list[dict[str, Any]]:
    stmt = (
        select(Analysis)
        .where(Analysis.asset == asset)
        .order_by(Analysis.created_at.desc())
        .limit(limit)
    )
    rows = session.scalars(stmt).all()
    out: list[dict[str, Any]] = []
    for a in reversed(rows):  # ordem cronológica para o LLM
        out.append(
            {
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "probability": a.probability_continuation,
                "confidence": a.confidence_level,
                "risk": a.contextual_risk,
                "recommendation": a.recommendation,
                "summary": (a.justification or "")[:400],
            }
        )
    return out


def fetch_similar_reactions(
    session: Session,
    asset: str,
    risk_level: str | None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """
    Heurística MVP: últimas reações do mesmo ativo; se risk_level fornecido,
    prioriza entradas cujo JSON de condição mencione risco similar.
    """
    stmt = select(MarketReaction).where(MarketReaction.asset == asset).order_by(MarketReaction.timestamp.desc()).limit(20)
    rows = session.scalars(stmt).all()
    picked: list[MarketReaction] = []
    if risk_level:
        key = risk_level.upper()
        for r in rows:
            try:
                blob = (r.market_condition_before or "") + (r.notes or "")
                if key in blob.upper():
                    picked.append(r)
            except Exception:
                continue
            if len(picked) >= limit:
                break
    if len(picked) < limit:
        for r in rows:
            if r not in picked:
                picked.append(r)
            if len(picked) >= limit:
                break
    return [
        {
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "event_type": r.event_type,
            "event_description": r.event_description[:300],
            "outcome": r.outcome,
        }
        for r in picked[:limit]
    ]


def fetch_recent_patterns(session: Session, asset: str, limit: int = 5) -> list[dict[str, Any]]:
    stmt = select(PatternRecord).where(PatternRecord.asset == asset).order_by(PatternRecord.created_at.desc()).limit(limit)
    rows = session.scalars(stmt).all()
    return [
        {
            "pattern_type": p.pattern_type,
            "data": json.loads(p.detection_data) if p.detection_data else None,
        }
        for p in reversed(rows)
    ]
