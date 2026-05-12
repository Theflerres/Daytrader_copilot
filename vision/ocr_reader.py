"""
Extração de métricas textuais visíveis no gráfico com EasyOCR (preço, volume, horário).
Resultado é probabilístico; inconsistências aumentam risco contextual.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from threading import Lock
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_reader_lock = Lock()
_reader = None


def _get_reader(langs: list[str]):
    global _reader
    with _reader_lock:
        if _reader is None:
            import easyocr

            _reader = easyocr.Reader(langs, gpu=False, verbose=False)
        return _reader


@dataclass
class OcrMetrics:
    texts: list[str]
    raw_lines: list[tuple[Any, str, Any]]
    price_candidates: list[str]
    volume_candidates: list[str]
    times: list[str]
    merged_text: str


def read_screen_metrics(png_bytes: bytes, langs: list[str]) -> OcrMetrics:
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        return OcrMetrics([], [], [], [], [], [], "")

    reader = _get_reader(langs)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    raw = reader.readtext(rgb)

    texts: list[str] = []
    for _box, txt, conf in raw:
        if txt and float(conf) > 0.25:
            texts.append(txt.strip())

    merged = " | ".join(texts)

    price_cand: list[str] = []
    vol_cand: list[str] = []
    times: list[str] = []

    price_re = re.compile(r"\b\d{1,3}(?:[\.,]\d{3})+(?:[\.,]\d+)?|\b\d{4,9}(?:[\.,]\d+)?\b")
    vol_re = re.compile(r"\b[Vv]?\s*[:]?\s*(\d[\d\.]*|\d[\d\,]*)\b")
    time_re = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")

    for t in texts:
        for m in price_re.findall(t.replace(" ", "")):
            norm = m.replace(".", "").replace(",", ".") if "," in m and "." in m else m.replace(",", ".")
            if len(norm.replace(".", "")) >= 5:
                price_cand.append(m)
        for m in time_re.findall(t):
            times.append(m)
        if re.search(vol_re, t):
            vol_cand.append(t)

    return OcrMetrics(
        texts=texts,
        raw_lines=raw,
        price_candidates=list(dict.fromkeys(price_cand))[:8],
        volume_candidates=vol_cand[:8],
        times=list(dict.fromkeys(times))[:8],
        merged_text=merged,
    )


def extract_structured_from_texts(texts: list[str]) -> tuple[list[str], list[str], list[str], str]:
    """Extrai preço, volume e horários a partir de linhas OCR já filtradas."""
    price_cand: list[str] = []
    vol_cand: list[str] = []
    times: list[str] = []

    price_re = re.compile(r"\b\d{1,3}(?:[\.,]\d{3})+(?:[\.,]\d+)?|\b\d{4,9}(?:[\.,]\d+)?\b")
    vol_re = re.compile(r"\b[Vv]?\s*[:]?\s*(\d[\d\.]*|\d[\d\,]*)\b")
    time_re = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")

    for t in texts:
        for m in price_re.findall(t.replace(" ", "")):
            norm = m.replace(".", "").replace(",", ".") if "," in m and "." in m else m.replace(",", ".")
            if len(norm.replace(".", "")) >= 5:
                price_cand.append(m)
        for m in time_re.findall(t):
            times.append(m)
        if re.search(vol_re, t):
            vol_cand.append(t)

    merged = " | ".join(texts)
    return (
        list(dict.fromkeys(price_cand))[:8],
        vol_cand[:8],
        list(dict.fromkeys(times))[:8],
        merged,
    )


def ocr_to_dict(o: OcrMetrics) -> dict[str, Any]:
    return {
        "texts": o.texts[:40],
        "price_candidates": o.price_candidates,
        "volume_candidates": o.volume_candidates,
        "times": o.times,
        "merged_text": o.merged_text[:2000],
    }
