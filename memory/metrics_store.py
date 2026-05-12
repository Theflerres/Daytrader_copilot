"""Persistência e leitura de métricas agregadas do copiloto."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from memory.models import MetricEvent, OperatorFeedback

logger = logging.getLogger(__name__)


def record_metric_event(
    session: Session,
    *,
    profile_name: str,
    asset: str,
    now: datetime,
    regime: str,
    confidence_level: str,
    contextual_risk: str,
    recommendation: str,
    ocr_global_score: float | None,
    capture_ok: bool,
    llm_ok: bool,
    meta: dict[str, Any] | None = None,
) -> None:
    rec_u = recommendation.upper()
    dont = 1 if ("NÃO OPERAR" in rec_u or "NAO OPERAR" in rec_u) else 0
    ev = MetricEvent(
        profile_name=profile_name[:64],
        asset=asset[:32],
        hour_bucket=now.hour,
        regime=regime[:48],
        confidence_level=confidence_level[:16],
        contextual_risk=contextual_risk[:16],
        dont_operar=dont,
        ocr_global_score=ocr_global_score,
        capture_ok=1 if capture_ok else 0,
        llm_ok=1 if llm_ok else 0,
        meta_json=json.dumps(meta or {}, ensure_ascii=False),
    )
    session.add(ev)


def fetch_dashboard_metrics(session: Session, since_hours: int = 168) -> dict[str, Any]:
    """Agregações simples para painel técnico (últimos N horas)."""
    cutoff = datetime.utcnow() - timedelta(hours=since_hours)
    stmt = select(MetricEvent).where(MetricEvent.created_at >= cutoff)
    rows = list(session.scalars(stmt).all())
    n = len(rows)
    if n == 0:
        return {
            "samples": 0,
            "dont_operar_rate": 0.0,
            "avg_ocr_score": 0.0,
            "confidence_counts": {},
            "regime_counts": {},
            "hour_dont": {},
            "feedback_pending_note": "Sem amostras no período.",
        }

    dont_c = sum(r.dont_operar for r in rows)
    ocr_vals = [float(r.ocr_global_score) for r in rows if r.ocr_global_score is not None]
    avg_ocr = sum(ocr_vals) / len(ocr_vals) if ocr_vals else 0.0

    conf_c: dict[str, int] = {}
    reg_c: dict[str, int] = {}
    hour_dont: dict[int, tuple[int, int]] = {}  # hour -> (dont, total)

    for r in rows:
        conf_c[r.confidence_level] = conf_c.get(r.confidence_level, 0) + 1
        reg_c[r.regime] = reg_c.get(r.regime, 0) + 1
        h = int(r.hour_bucket)
        a, b = hour_dont.get(h, (0, 0))
        hour_dont[h] = (a + r.dont_operar, b + 1)

    # Feedback humano (precisão supervisionada) — contagem bruta
    fstmt = select(func.count(OperatorFeedback.id)).where(OperatorFeedback.created_at >= cutoff)
    fb_n = int(session.scalar(fstmt) or 0)

    return {
        "samples": n,
        "dont_operar_rate": round(dont_c / n, 4),
        "avg_ocr_score": round(avg_ocr, 4),
        "confidence_counts": conf_c,
        "regime_counts": reg_c,
        "hour_dont": {str(k): {"dont": v[0], "n": v[1]} for k, v in sorted(hour_dont.items())},
        "feedback_samples": fb_n,
        "feedback_pending_note": "Precisão supervisionada exige labels em operator_feedback (futuro CLI).",
    }
