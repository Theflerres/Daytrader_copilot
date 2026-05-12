"""
Sistema de confiança operacional (MVP): traduz qualidade de contexto em rótulos
ALTA / MEDIA / BAIXA / INVALIDA, alinhado à filosofia do copiloto.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_ORDER = {"INVALIDA": 0, "BAIXA": 1, "MEDIA": 2, "ALTA": 3}


@dataclass
class ConfidenceDimensions:
    """Três dimensões exigidas pelo prompt: probabilidade estimada, confiança e risco."""

    probability_continuation: float
    confidence_label: str
    contextual_risk: str


def _min_suggest_rank(min_label: str) -> int:
    return _ORDER.get(min_label.strip().upper(), 2)


def score_operational_confidence(
    risk: Any,
    preproc: dict[str, Any],
    ocr: dict[str, Any],
    trend: dict[str, Any],
    min_confidence_to_suggest: str = "MEDIA",
    market_regime: str | None = None,
) -> ConfidenceDimensions:
    """
    Heurística pré-LLM: não é 'sinal de trade', é qualidade de contexto.
    - risco ALTO do checklist tende a derrubar confiança.
    - OCR fraco ou tendência incoerente reduz confiança.
    """
    risk_level = getattr(risk, "level", "MEDIO")
    flags = set(getattr(risk, "flags", []) or [])

    conf = 2  # base MEDIA em escala 0-3
    if risk_level == "ALTO":
        conf -= 2
    elif risk_level == "MEDIO":
        conf -= 1

    if "ocr_insuficiente" in flags:
        conf -= 1
    if "mercado_inconsistente" in flags:
        conf -= 1
    if "volatilidade_anormal" in flags:
        conf -= 1

    if market_regime in ("mercado_erratico", "alta_volatilidade"):
        conf -= 1
    if market_regime == "lateralizacao":
        conf -= 1  # contexto mais ambíguo operacionalmente

    r2 = float(trend.get("r_squared", 0.0))
    if r2 > 0.35:
        conf += 1
    elif r2 < 0.05:
        conf -= 1

    edge = float(preproc.get("edge_density", 0.0))
    if edge > 0.35:
        conf -= 1

    if len(ocr.get("price_candidates") or []) >= 1 and (ocr.get("times") or []):
        conf += 1

    ogs = ocr.get("ocr_global_score")
    if isinstance(ogs, (int, float)) and ogs > 0.45:
        conf += 1
    elif isinstance(ogs, (int, float)) and ogs < 0.22:
        conf -= 1

    conf = max(0, min(3, conf))

    label_map = {0: "INVALIDA", 1: "BAIXA", 2: "MEDIA", 3: "ALTA"}
    confidence_label = label_map[conf]

    # Risco contextual textual alinhado ao checklist
    contextual_risk = risk_level if risk_level in ("BAIXO", "MEDIO", "ALTO") else "MEDIO"
    if confidence_label == "INVALIDA":
        contextual_risk = "ALTO"

    # Probabilidade numérica leve (não é previsão de candle — apenas resumo heurístico)
    base_p = 0.5 + 0.08 * (r2 - 0.2) + (0.03 if confidence_label == "ALTA" else 0.0)
    if "mercado_inconsistente" in flags:
        base_p -= 0.12
    prob = max(0.05, min(0.95, base_p))

    # Se abaixo do mínimo configurado para sugestão, reforço explícito de cautela no rótulo (parser LLM pode sobrepor depois).
    if _ORDER.get(confidence_label, 2) < _min_suggest_rank(min_confidence_to_suggest):
        logger.info("Confiança %s abaixo do mínimo %s para sugestão forte.", confidence_label, min_confidence_to_suggest)

    return ConfidenceDimensions(probability_continuation=round(prob * 100) / 100, confidence_label=confidence_label, contextual_risk=contextual_risk)
