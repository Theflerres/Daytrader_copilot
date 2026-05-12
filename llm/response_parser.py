"""
Parse estruturado da resposta do LLM — probabilidade, confiança, risco, recomendação.
Fallback para dimensões heurísticas se o modelo não seguir o formato.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from context.confidence_scorer import ConfidenceDimensions

logger = logging.getLogger(__name__)


@dataclass
class ParsedAnalysis:
    probability_continuation: float
    confidence_level: str
    contextual_risk: str
    recommendation: str
    justification: str


_RE_PROB = re.compile(
    r"Probabilidade\s+de\s+continua(?:ç|c)ão\s*:\s*(\d+(?:[\.,]\d+)?)\s*%",
    re.IGNORECASE,
)
_RE_CONF = re.compile(
    r"Confian(?:ç|c)a\s+da\s+an(?:á|a)lise\s*:\s*(ALTA|M[ÉE]DIA|BAIXA|INV[ÁA]LIDA|MEDIA|INVALIDA)",
    re.IGNORECASE,
)
_RE_RISK = re.compile(
    r"Risco\s+contextual\s*:\s*(BAIXO|M[ÉE]DIO|MEDIO|ALTO)",
    re.IGNORECASE,
)
_RE_REC = re.compile(r"Recomenda(?:ç|c)[ãa]o\s*:\s*([^\n\r]+)", re.IGNORECASE)


def _norm_conf(v: str) -> str:
    u = v.upper().replace("É", "E").replace("Á", "A")
    if u in ("INVALIDA", "INVÁLIDA", "INVALIDA"):
        return "INVALIDA"
    if u in ("MÉDIA", "MEDIA", "MEDIO"):  # model confundindo
        return "MEDIA"
    return u if u in ("ALTA", "MEDIA", "BAIXA", "INVALIDA") else "BAIXA"


def _norm_risk(v: str) -> str:
    u = v.upper().replace("É", "E")
    if u in ("MÉDIO", "MEDIO"):
        return "MEDIO"
    if u in ("BAIXO", "ALTO"):
        return u
    return "MEDIO"


def parse_llm_response(text: str, fallback: ConfidenceDimensions) -> ParsedAnalysis:
    justification = text.strip()

    prob_m = _RE_PROB.search(text.replace(",", "."))
    if prob_m:
        try:
            p = float(prob_m.group(1).replace(",", ".")) / 100.0
            probability = max(0.0, min(1.0, p))
        except ValueError:
            probability = fallback.probability_continuation
    else:
        # fallback porcentagem solta perto da palavra probabilidade
        loose = re.search(r"(\d{1,2}(?:[\.,]\d+)?)\s*%", text)
        probability = (
            max(0.0, min(1.0, float(loose.group(1).replace(",", ".")) / 100.0)) if loose else fallback.probability_continuation
        )

    cf = _RE_CONF.search(text)
    confidence = _norm_conf(cf.group(1)) if cf else fallback.confidence_label

    rk = _RE_RISK.search(text)
    risk = _norm_risk(rk.group(1)) if rk else fallback.contextual_risk
    risk = {"BAIXO": "BAIXO", "MEDIO": "MEDIO", "ALTO": "ALTO"}.get(risk, "MEDIO")

    rm = _RE_REC.search(text)
    recommendation = (rm.group(1).strip() if rm else "Reavaliar contexto antes de qualquer decisão.")[:500]

    return ParsedAnalysis(
        probability_continuation=probability if probability <= 1.0 else probability / 100.0,
        confidence_level=confidence,
        contextual_risk=risk,
        recommendation=recommendation,
        justification=justification,
    )
