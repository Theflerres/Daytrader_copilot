"""
Análise de tendência aproximada por regressão linear na silhueta inferior dos candles.
Heurística visual (sombra/chão aproximado), não substitui leitura humana.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TrendSummary:
    slope: float
    direction: str  # alta, baixa, lateral
    r_squared: float
    points_used: int


def analyze_trend_from_silhouette(png_bytes: bytes) -> TrendSummary:
    """
    Usa a metade inferior da imagem (área típica de candles) e ajusta reta nos
    pontos mais escuros por coluna (aproximação de sombras).
    """
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        return TrendSummary(0.0, "lateral", 0.0, 0)

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    roi = gray[int(h * 0.35) :, :]
    roi = cv2.GaussianBlur(roi, (5, 5), 0)

    xs: list[float] = []
    ys: list[float] = []
    for x in range(0, roi.shape[1], max(1, roi.shape[1] // 200)):
        col = roi[:, x]
        y = int(np.argmin(col))
        xs.append(float(x))
        ys.append(float(y))

    n = len(xs)
    if n < 5:
        return TrendSummary(0.0, "lateral", 0.0, n)

    x_arr = np.array(xs)
    y_arr = np.array(ys)
    coef = np.polyfit(x_arr, y_arr, 1)
    slope = float(coef[0])
    y_pred = np.poly1d(coef)(x_arr)
    ss_res = float(np.sum((y_arr - y_pred) ** 2))
    ss_tot = float(np.sum((y_arr - np.mean(y_arr)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 1e-6 else 0.0

    norm = abs(slope) * w / max(h, 1)
    if norm < 0.15:
        direction = "lateral"
    elif slope < 0:
        direction = "alta"  # eixo y cresce para baixo na imagem: inclinação negativa => preço sobe
    else:
        direction = "baixa"

    return TrendSummary(slope=slope, direction=direction, r_squared=float(max(0.0, min(1.0, r_squared))), points_used=n)


def trend_to_dict(t: TrendSummary) -> dict[str, Any]:
    return {
        "slope": t.slope,
        "direction": t.direction,
        "r_squared": t.r_squared,
        "points_used": t.points_used,
    }
