"""
Pré-processamento OpenCV: escala de cinza, bordas e métricas para volatilidade visual.
Não infere preço real — apenas apoia risco e confiança contextual.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PreprocessResult:
    edge_density: float
    brightness_mean: float
    contrast_std: float
    gray_b64: str  # JPEG em base64 para debug opcional (não enviado ao LLM por padrão)
    metrics: dict[str, Any]


def _np_from_png(png_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Imagem PNG inválida ou corrompida.")
    return bgr


def preprocess_chart(png_bytes: bytes) -> PreprocessResult:
    """
    Converte para cinza, aplica Canny e calcula densidade de bordas (proxy de 'ruído' visual).
    """
    bgr = _np_from_png(png_bytes)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.mean(edges > 0))
    brightness_mean = float(np.mean(gray))
    contrast_std = float(np.std(gray))

    # thumbnail em base64 para eventual log (pequeno)
    small = cv2.resize(gray, (max(1, gray.shape[1] // 4), max(1, gray.shape[0] // 4)))
    ok, enc = cv2.imencode(".jpg", small, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
    gray_b64 = base64.b64encode(enc.tobytes()).decode("ascii") if ok else ""

    metrics = {
        "shape": list(bgr.shape[:2]),
        "edge_density": edge_density,
        "brightness_mean": brightness_mean,
        "contrast_std": contrast_std,
    }
    return PreprocessResult(
        edge_density=edge_density,
        brightness_mean=brightness_mean,
        contrast_std=contrast_std,
        gray_b64=gray_b64,
        metrics=metrics,
    )


def export_edges_preview_png(png_bytes: bytes) -> bytes:
    """PNG em escala de cinza (bordas Canny) para dataset / snapshot processado."""
    bgr = _np_from_png(png_bytes)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    ok, enc = cv2.imencode(".png", edges)
    if not ok:
        raise ValueError("Falha ao codificar preview de bordas.")
    return enc.tobytes()
