"""
Detecção visual básica: linhas horizontais fortes (possíveis níveis) e densidade estrutural.
MVP sem YOLO — apenas OpenCV clássico.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PatternSummary:
    horizontal_lines: int
    dominant_angle_deg: float | None
    detail: dict[str, Any]


def detect_basic_patterns(png_bytes: bytes) -> PatternSummary:
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        return PatternSummary(0, None, {})

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 40, 120)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=120, minLineLength=int(gray.shape[1] * 0.12), maxLineGap=20)

    horiz = 0
    angles: list[float] = []
    if lines is not None:
        for ln in lines[:, 0, :]:
            x1, y1, x2, y2 = ln
            dx, dy = (x2 - x1), (y2 - y1)
            if dx == 0:
                continue
            ang = abs(np.degrees(np.arctan2(dy, dx)))
            angles.append(float(ang))
            if ang < 12 or ang > 168:
                horiz += 1

    dominant = float(np.median(angles)) if angles else None
    detail = {
        "line_count": int(len(lines) if lines is not None else 0),
        "horizontal_like": horiz,
    }
    return PatternSummary(horizontal_lines=horiz, dominant_angle_deg=dominant, detail=detail)


def patterns_to_dict(p: PatternSummary) -> dict[str, Any]:
    return {"horizontal_lines": p.horizontal_lines, "dominant_angle_deg": p.dominant_angle_deg, **p.detail}
