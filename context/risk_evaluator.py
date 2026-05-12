"""
Checklist de risco antes de enviar ao LLM: horários sensíveis, volatilidade visual,
consistência mínima do OCR e tendência vs densidade de bordas.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RiskEvaluation:
    """Agregação de alertas para o dashboard e para o sistema de confiança."""

    level: str  # BAIXO, MEDIO, ALTO
    flags: list[str] = field(default_factory=list)
    checklist_lines: list[str] = field(default_factory=list)


def _in_any_window(dt: datetime, windows: list[tuple[int, int, int, int]]) -> bool:
    tmin = dt.hour * 60 + dt.minute
    for h0, m0, h1, m1 in windows:
        start = h0 * 60 + m0
        end = h1 * 60 + m1
        if start <= tmin <= end:
            return True
    return False


def evaluate_contextual_risk(
    now: datetime,
    high_risk_hours: list[tuple[int, int, int, int]],
    preproc: dict[str, Any],
    ocr: dict[str, Any],
    trend: dict[str, Any],
    edge_density_high: float = 0.22,
    edge_density_extreme: float = 0.38,
    market_regime: str | None = None,
    ocr_global_score: float | None = None,
    allowed_operating_hours: list[tuple[int, int, int, int]] | None = None,
) -> RiskEvaluation:
    """
    Produz nível de risco contextual e mensagens explícitas (filtragem antes de gerar).
    """
    flags: list[str] = []
    lines: list[str] = []

    if allowed_operating_hours is not None and len(allowed_operating_hours) > 0:
        if not _in_any_window(now, allowed_operating_hours):
            flags.append("fora_janela_operacional")
            lines.append("Fora da janela operacional definida no perfil — contexto não prioritário.")

    if _in_any_window(now, high_risk_hours):
        flags.append("horario_desfavoravel")
        lines.append("Janela de alto risco (abertura/fechamento ou leilão típico).")

    edge = float(preproc.get("edge_density", 0.0))
    if edge >= edge_density_extreme:
        flags.append("volatilidade_anormal")
        lines.append("Volatilidade visual muito elevada (densidade de bordas extrema).")
    elif edge >= edge_density_high:
        flags.append("volatilidade_anormal")
        lines.append("Volatilidade visual acima do usual — possível chop ou spike.")

    has_time_ocr = bool(ocr.get("times"))
    has_price = bool(ocr.get("price_candidates"))
    if not has_time_ocr and not has_price:
        flags.append("ocr_insuficiente")
        lines.append("OCR não extraiu preço/horário com confiança — contexto textual frágil.")
    elif not has_price:
        flags.append("ocr_insuficiente")
        lines.append("Preço não detectado no OCR — validar manualmente antes de operar.")

    if ocr_global_score is not None and ocr_global_score < 0.28 and len(ocr.get("price_candidates") or []) == 0:
        flags.append("ocr_baixa_confianca")
        lines.append("Score global de OCR baixo e sem preço detectado — dados frágeis.")

    if market_regime in ("mercado_erratico", "alta_volatilidade"):
        flags.append("regime_desfavoravel")
        lines.append(f"Regime detectado: {market_regime.replace('_', ' ')} — exigir mais confirmação.")

    r2 = float(trend.get("r_squared", 0.0))
    if r2 < 0.08 and edge > 0.18:
        flags.append("mercado_inconsistente")
        lines.append("Tendência visual fraca com estrutura ruidosa — possível lateralização/caótico.")

    # Pontuação simples → nível
    score = len(flags)
    if score >= 3 or "horario_desfavoravel" in flags and "ocr_insuficiente" in flags:
        level = "ALTO"
    elif score >= 1:
        level = "MEDIO"
    else:
        level = "BAIXO"

    logger.debug("RiskEvaluation level=%s flags=%s", level, flags)
    return RiskEvaluation(level=level, flags=flags, checklist_lines=lines)
