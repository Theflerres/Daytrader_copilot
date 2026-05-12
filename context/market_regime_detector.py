"""
Classificação heurística de regime de mercado a partir de métricas visuais locais.
Influencia confiança, thresholds de risco e texto do prompt (não é previsão de preço).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MarketRegime:
    """Rótulo estável para logging e métricas."""

    label: str
    description_pt: str
    edge_density: float
    r_squared: float
    trend_direction: str


def detect_market_regime(preprocess_metrics: dict[str, Any], trend: dict[str, Any], patterns: dict[str, Any] | None = None) -> MarketRegime:
    """
    Regimes: tendencia_forte | lateralizacao | alta_volatilidade | baixa_volatilidade |
             mercado_erratico | mercado_direcional
    """
    edge = float(preprocess_metrics.get("edge_density", 0.0))
    r2 = float(trend.get("r_squared", 0.0))
    direction = str(trend.get("direction", "lateral"))

    patterns = patterns or {}
    horiz = int(patterns.get("horizontal_lines") or patterns.get("horizontal_like") or 0)

    # Alta / baixa volatilidade via densidade de bordas (proxy visual)
    if edge >= 0.38:
        vol_tag = "alta"
    elif edge < 0.10:
        vol_tag = "baixa"
    else:
        vol_tag = "media"

    # Erraticidade: ruído alto sem estrutura de tendência
    erratic = edge > 0.28 and r2 < 0.06

    # Direcionalidade vs lateral
    strong_trend = r2 > 0.22 and direction in ("alta", "baixa")
    lateral = r2 < 0.10 or direction == "lateral" or horiz > 10

    if erratic:
        label = "mercado_erratico"
        desc = "Estrutura visual ruidosa e pouca coerência direcional — priorizar não operar."
    elif strong_trend and vol_tag != "alta":
        label = "tendencia_forte"
        desc = "Tendência visual mais coerente; ainda assim validar fluxo/volume no gráfico."
    elif strong_trend and vol_tag == "alta":
        label = "mercado_direcional"
        desc = "Direção aparente sob alta volatilidade visual — gestão de risco reforçada."
    elif lateral and vol_tag == "baixa":
        label = "lateralizacao"
        desc = "Possível compressão / lateral; rompimentos podem ser armadilhas sem confirmação."
    elif vol_tag == "alta":
        label = "alta_volatilidade"
        desc = "Amplitude visual elevada — reduzir agressividade e exigir confirmações."
    elif vol_tag == "baixa":
        label = "baixa_volatilidade"
        desc = "Movimento visual contido — atenção a falsos rompimentos e liquidez."
    else:
        label = "mercado_direcional"
        desc = "Contexto misto; tratar como direcional moderado com filtros padrão."

    return MarketRegime(
        label=label,
        description_pt=desc,
        edge_density=edge,
        r_squared=r2,
        trend_direction=direction,
    )


def regime_to_prompt_dict(regime: MarketRegime) -> dict[str, Any]:
    return {
        "label": regime.label,
        "description": regime.description_pt,
        "edge_density": regime.edge_density,
        "r_squared": regime.r_squared,
        "trend_direction": regime.trend_direction,
    }
