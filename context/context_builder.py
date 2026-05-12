"""Montagem do pacote de contexto (dict + texto auxiliar) enviado ao prompt_builder."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from .confidence_scorer import ConfidenceDimensions
from .risk_evaluator import RiskEvaluation


def build_llm_context(
    *,
    asset: str,
    now: datetime,
    dimensions: ConfidenceDimensions,
    risk: RiskEvaluation,
    preprocess_metrics: dict[str, Any],
    trend: dict[str, Any],
    patterns: dict[str, Any],
    ocr: dict[str, Any],
    historical_analyses: list[dict[str, Any]],
    similar_reactions: list[dict[str, Any]],
    market_regime: dict[str, Any] | None = None,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """
    Estrutura única para o prompt: combina filosofia do copiloto (filtragem antes)
    com dados objetivos disponíveis no MVP.
    """
    dims = dict(asdict(dimensions))
    dims["probability_percent"] = round(float(dimensions.probability_continuation) * 100, 2)
    return {
        "asset": asset,
        "timestamp_local": now.isoformat(timespec="seconds"),
        "pre_analysis": dims,
        "risk_evaluation": {"level": risk.level, "flags": risk.flags, "checklist": risk.checklist_lines},
        "vision": {
            "preprocess": preprocess_metrics,
            "trend": trend,
            "patterns": patterns,
        },
        "ocr": ocr,
        "historical_analyses": historical_analyses,
        "similar_reactions": similar_reactions,
        "market_regime": market_regime or {},
        "profile_name": profile_name or "",
    }
