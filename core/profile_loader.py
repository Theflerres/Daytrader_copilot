"""
Carrega perfis de layout (JSON) — regiões nomeadas, thresholds, OCR e composite.
Compatível com setup multi-monitor (coordenadas absolutas na área virtual do Windows).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class OcrPipelineSpec:
    """Pipeline OCR por região (upscale, binarização adaptativa, tentativas, whitelist)."""

    kind: str = "generic"  # generic | price_time | numeric_only | time_only | book_tape
    upscale: float = 1.0
    adaptive_threshold: bool = False
    gaussian_blur: int = 0  # kernel ímpar ou 0 = desligado
    attempts: int = 2
    min_confidence: float = 0.2
    whitelist: str | None = None  # "digits_time" | "digits_dot_comma" | "digits_only" | None


@dataclass
class TradingProfile:
    """Perfil operacional completo (um arquivo JSON por layout)."""

    name: str
    asset: str
    regions: dict[str, dict[str, int]]  # nome -> {left, top, width, height}
    operating_hours: list[list[int]] = field(default_factory=list)  # [[h0,m0,h1,m1], ...] vazio = sempre
    thresholds: dict[str, float] = field(default_factory=dict)
    ocr_langs: list[str] = field(default_factory=lambda: ["pt", "en"])
    ocr_pipelines: dict[str, OcrPipelineSpec] = field(default_factory=dict)
    composite_layout: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    def pipeline_for(self, region_key: str) -> OcrPipelineSpec:
        raw = self.ocr_pipelines.get(region_key) or self.ocr_pipelines.get("default") or {}
        if isinstance(raw, OcrPipelineSpec):
            return raw
        return OcrPipelineSpec(
            kind=str(raw.get("kind", "generic")),
            upscale=float(raw.get("upscale", 1.0)),
            adaptive_threshold=bool(raw.get("adaptive_threshold", False)),
            gaussian_blur=int(raw.get("gaussian_blur", 0)),
            attempts=int(raw.get("attempts", 2)),
            min_confidence=float(raw.get("min_confidence", 0.2)),
            whitelist=raw.get("whitelist"),
        )


def _parse_pipeline_map(data: dict[str, Any]) -> dict[str, OcrPipelineSpec]:
    out: dict[str, OcrPipelineSpec] = {}
    ocr_section = data.get("ocr") or {}
    pipes = ocr_section.get("pipelines") or {}
    for k, v in pipes.items():
        if isinstance(v, dict):
            out[k] = OcrPipelineSpec(
                kind=str(v.get("kind", "generic")),
                upscale=float(v.get("upscale", 1.0)),
                adaptive_threshold=bool(v.get("adaptive_threshold", False)),
                gaussian_blur=int(v.get("gaussian_blur", 0)),
                attempts=int(v.get("attempts", 2)),
                min_confidence=float(v.get("min_confidence", 0.2)),
                whitelist=v.get("whitelist"),
            )
    return out


def load_trading_profile(path: str | Path) -> TradingProfile:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Perfil não encontrado: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    regions = data.get("regions") or data.get("CAPTURE_REGIONS") or {}
    if not isinstance(regions, dict):
        raise ValueError("JSON do perfil precisa de 'regions' (dict nome -> retângulo).")

    oh = data.get("operating_hours") or []
    thresholds = data.get("thresholds") or {}
    ocr_section = data.get("ocr") or {}
    langs = ocr_section.get("default_langs") or data.get("ocr_langs") or ["pt", "en"]

    profile = TradingProfile(
        name=str(data.get("name", p.stem)),
        asset=str(data.get("asset", "WINFUT")),
        regions={k: {kk: int(vv) for kk, vv in v.items()} for k, v in regions.items() if isinstance(v, dict)},
        operating_hours=[list(map(int, w)) for w in oh if len(w) == 4],
        thresholds={k: float(v) for k, v in thresholds.items()},
        ocr_langs=list(langs),
        ocr_pipelines=_parse_pipeline_map(data),
        composite_layout=data.get("composite_layout") or {},
        meta={k: v for k, v in data.items() if k not in ("name", "asset", "regions", "CAPTURE_REGIONS", "operating_hours", "thresholds", "ocr", "composite_layout")},
    )
    _ensure_profile_defaults(profile)
    logger.info("Perfil carregado: %s (%d regiões)", profile.name, len(profile.regions))
    return profile


def save_trading_profile(path: str | Path, profile: TradingProfile) -> None:
    """Persiste perfil em JSON (usado pelo calibrate)."""
    _ensure_profile_defaults(profile)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    ocr_block: dict[str, Any] = {"default_langs": profile.ocr_langs, "pipelines": {}}
    for k, spec in profile.ocr_pipelines.items():
        ocr_block["pipelines"][k] = {
            "kind": spec.kind,
            "upscale": spec.upscale,
            "adaptive_threshold": spec.adaptive_threshold,
            "gaussian_blur": spec.gaussian_blur,
            "attempts": spec.attempts,
            "min_confidence": spec.min_confidence,
            "whitelist": spec.whitelist,
        }
    payload = {
        "name": profile.name,
        "asset": profile.asset,
        "regions": profile.regions,
        "operating_hours": profile.operating_hours,
        "thresholds": profile.thresholds,
        "ocr": ocr_block,
        "composite_layout": profile.composite_layout,
        **profile.meta,
    }
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Perfil salvo em %s", p)


def profile_from_legacy_single_region(region: dict[str, int], asset: str = "WINFUT") -> TradingProfile:
    """Compatibilidade com MVP: uma única região vira 'main_chart'."""
    return TradingProfile(
        name="legacy_single",
        asset=asset,
        regions={"main_chart": dict(region)},
        ocr_pipelines={"main_chart": OcrPipelineSpec(kind="price_time", upscale=1.5, attempts=2)},
    )


def _default_ocr_pipelines_for_region(region_key: str) -> OcrPipelineSpec:
    if region_key == "main_chart":
        return OcrPipelineSpec(kind="price_time", upscale=1.5, attempts=2)
    if region_key == "volume":
        return OcrPipelineSpec(kind="numeric_only", upscale=2.0, adaptive_threshold=True, attempts=3, whitelist="digits_dot_comma")
    if region_key in ("tape", "book"):
        return OcrPipelineSpec(kind="book_tape", upscale=1.8, attempts=2, min_confidence=0.15)
    if region_key == "clock":
        return OcrPipelineSpec(kind="time_only", upscale=2.5, adaptive_threshold=True, attempts=3, whitelist="digits_time")
    return OcrPipelineSpec(kind="generic", upscale=1.25, attempts=2)


def _ensure_profile_defaults(profile: TradingProfile) -> None:
    """Preenche pipelines OCR e layout composite quando ausentes no JSON."""
    for rk in profile.regions:
        if rk not in profile.ocr_pipelines:
            profile.ocr_pipelines[rk] = _default_ocr_pipelines_for_region(rk)

    if not profile.composite_layout:
        keys = [k for k in ("main_chart", "volume", "tape", "book", "clock", "position_area") if k in profile.regions]
        if len(keys) >= 4:
            profile.composite_layout = {
                "rows": [keys[:2], keys[2:4]],
                "cell_max_width": 640,
                "padding": 4,
                "labels": True,
            }
        elif len(keys) >= 2:
            profile.composite_layout = {"rows": [keys], "cell_max_width": 720, "padding": 4, "labels": True}
        elif keys:
            profile.composite_layout = {"rows": [[keys[0]]], "cell_max_width": 960, "padding": 4, "labels": True}
