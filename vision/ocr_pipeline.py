"""
OCR robusto por região: pré-processamento, múltiplas tentativas, whitelist e score agregado.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from core.profile_loader import OcrPipelineSpec
from vision.ocr_reader import OcrMetrics, extract_structured_from_texts, read_screen_metrics

logger = logging.getLogger(__name__)


def _bgr_from_png(png: bytes) -> np.ndarray | None:
    arr = np.frombuffer(png, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _png_from_bgr(bgr: np.ndarray) -> bytes:
    ok, enc = cv2.imencode(".png", bgr)
    if not ok:
        raise ValueError("Falha ao codificar PNG.")
    return enc.tobytes()


def preprocess_for_ocr(bgr: np.ndarray, spec: OcrPipelineSpec) -> np.ndarray:
    """Upscale, blur opcional, threshold adaptativo opcional."""
    out = bgr.copy()
    if spec.upscale and spec.upscale > 1.01:
        w, h = out.shape[1], out.shape[0]
        nw, nh = int(w * spec.upscale), int(h * spec.upscale)
        out = cv2.resize(out, (nw, nh), interpolation=cv2.INTER_CUBIC)

    if spec.gaussian_blur and spec.gaussian_blur >= 3 and spec.gaussian_blur % 2 == 1:
        out = cv2.GaussianBlur(out, (spec.gaussian_blur, spec.gaussian_blur), 0)

    if spec.adaptive_threshold:
        gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
        at = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 11)
        out = cv2.cvtColor(at, cv2.COLOR_GRAY2BGR)

    return out


_WHITELIST_RES = {
    "digits_time": re.compile(r"^[\d\s\:\.\,]+$"),
    "digits_dot_comma": re.compile(r"^[\d\.\,\s]+$"),
    "digits_only": re.compile(r"^[\d\s]+$"),
}


def _filter_whitelist(texts: list[str], wl: str | None) -> list[str]:
    if not wl or wl not in _WHITELIST_RES:
        return texts
    rx = _WHITELIST_RES[wl]
    return [t for t in texts if rx.match(t.strip())]


@dataclass
class RegionOcrResult:
    region_key: str
    texts: list[str]
    price_candidates: list[str]
    volume_candidates: list[str]
    times: list[str]
    merged_text: str
    mean_confidence: float
    attempts_used: int
    pipeline_kind: str
    raw_debug: list[Any] = field(default_factory=list)


def run_region_ocr(region_key: str, png_bytes: bytes, spec: OcrPipelineSpec, langs: list[str]) -> RegionOcrResult:
    """
    Executa até `attempts` passes: original + pré-processamentos.
    Escolhe o pass com maior confiança média nas linhas aceitas.
    """
    bgr0 = _bgr_from_png(png_bytes)
    if bgr0 is None:
        return RegionOcrResult(region_key, [], [], [], [], "", 0.0, 0, spec.kind)

    variants: list[np.ndarray] = [bgr0]
    if spec.attempts >= 2:
        variants.append(preprocess_for_ocr(bgr0, spec))
    if spec.attempts >= 3:
        alt = OcrPipelineSpec(
            kind=spec.kind,
            upscale=max(spec.upscale, 1.2),
            adaptive_threshold=not spec.adaptive_threshold,
            gaussian_blur=spec.gaussian_blur or 3,
            attempts=1,
            min_confidence=spec.min_confidence,
            whitelist=spec.whitelist,
        )
        variants.append(preprocess_for_ocr(bgr0, alt))

    best: OcrMetrics | None = None
    best_score = -1.0
    used = 0

    for attempt_idx, bgr in enumerate(variants[: max(1, spec.attempts)]):
        used = attempt_idx + 1
        try:
            png = _png_from_bgr(bgr)
            m = read_screen_metrics(png, langs)
        except Exception as e:
            logger.debug("OCR %s tentativa %s: %s", region_key, attempt_idx, e)
            continue

        confs = [float(c) for _b, _t, c in m.raw_lines if c is not None and float(c) >= spec.min_confidence]
        score = float(sum(confs) / len(confs)) if confs else 0.0
        if score >= best_score:
            best_score = score
            best = m

    if best is None:
        return RegionOcrResult(region_key, [], [], [], [], "", 0.0, used, spec.kind)

    if spec.whitelist:
        texts_f = _filter_whitelist(best.texts, spec.whitelist)
        prices, vols, times, merged = extract_structured_from_texts(texts_f)
        texts_out = texts_f
    else:
        texts_out = best.texts
        prices, vols, times, merged = best.price_candidates, best.volume_candidates, best.times, best.merged_text

    confs2 = [float(c) for _b, _t, c in best.raw_lines if c is not None and float(c) >= spec.min_confidence]
    mean_conf = float(sum(confs2) / len(confs2)) if confs2 else best_score

    return RegionOcrResult(
        region_key=region_key,
        texts=texts_out,
        price_candidates=prices,
        volume_candidates=vols,
        times=times,
        merged_text=merged,
        mean_confidence=mean_conf,
        attempts_used=used,
        pipeline_kind=spec.kind,
    )


def aggregate_ocr_bundle(by_region: dict[str, RegionOcrResult]) -> dict[str, Any]:
    """Estrutura única para risco / LLM: campos flat + by_region."""
    prices: list[str] = []
    times: list[str] = []
    vols: list[str] = []
    texts: list[str] = []
    scores: dict[str, float] = {}

    for k, r in by_region.items():
        scores[k] = r.mean_confidence
        texts.extend(r.texts[:20])
        prices.extend(r.price_candidates)
        vols.extend(r.volume_candidates)
        times.extend(r.times)

    merged_text = " || ".join(f"{k}:{r.merged_text[:400]}" for k, r in by_region.items() if r.merged_text)

    return {
        "by_region": {
            k: {
                "texts": r.texts[:30],
                "mean_confidence": round(r.mean_confidence, 4),
                "attempts": r.attempts_used,
                "kind": r.pipeline_kind,
            }
            for k, r in by_region.items()
        },
        "price_candidates": list(dict.fromkeys(prices))[:12],
        "volume_candidates": list(dict.fromkeys(vols))[:12],
        "times": list(dict.fromkeys(times))[:12],
        "texts": texts[:60],
        "merged_text": merged_text[:4000],
        "ocr_scores": scores,
        "ocr_global_score": float(sum(scores.values()) / len(scores)) if scores else 0.0,
    }
