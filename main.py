#!/usr/bin/env python3
"""
Orquestrador Market Copilot — Fase refinamento: perfis multi-região, composite, regime,
snapshots hierárquicos, métricas e logging por canal.
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

import config as cfg

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from capture.region_selector import load_saved_region, save_region, select_region_interactive
from capture.screen_capture import capture_region_png
from context.confidence_scorer import score_operational_confidence
from context.context_builder import build_llm_context
from context.market_regime_detector import detect_market_regime, regime_to_prompt_dict
from context.risk_evaluator import evaluate_contextual_risk
from core.logging_setup import log_structured, setup_channel_logging
from core.profile_loader import TradingProfile, load_trading_profile, profile_from_legacy_single_region
from interface.dashboard import DashboardState, build_dashboard
from llm.ollama_client import LlavaAnalyzer
from llm.prompt_builder import build_multimodal_messages
from llm.response_parser import parse_llm_response
from memory.database import session_scope
from memory.memory_query import fetch_recent_analyses, fetch_similar_reactions
from memory.metrics_store import fetch_dashboard_metrics, record_metric_event
from memory.models import Analysis, OperatorLog, PatternRecord
from vision.composite_frame import build_composite
from vision.ocr_pipeline import aggregate_ocr_bundle, run_region_ocr
from vision.pattern_detector import detect_basic_patterns, patterns_to_dict
from vision.preprocessor import export_edges_preview_png, preprocess_chart
from vision.snapshot_store import SnapshotSession
from vision.trend_analyzer import analyze_trend_from_silhouette, trend_to_dict


def setup_logging(log_file: str, level_name: str) -> None:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, level_name.upper(), logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root_log = logging.getLogger()
    root_log.handlers.clear()
    root_log.setLevel(level)
    root_log.addHandler(fh)
    root_log.addHandler(sh)


def _tuple_hours(blocks: list[list[int]]) -> list[tuple[int, int, int, int]]:
    out: list[tuple[int, int, int, int]] = []
    for w in blocks:
        if len(w) == 4:
            out.append((int(w[0]), int(w[1]), int(w[2]), int(w[3])))
    return out


def resolve_trading_profile(args: argparse.Namespace) -> TradingProfile:
    """Perfil JSON ativo ou fallback legado (uma região main_chart)."""
    if getattr(args, "profile", None):
        return load_trading_profile(args.profile)

    ap_path = Path(cfg.ACTIVE_PROFILE_PATH)
    if ap_path.is_file():
        try:
            return load_trading_profile(ap_path)
        except Exception as e:
            logging.getLogger(__name__).warning("Perfil padrão inválido (%s): %s — usando legado.", ap_path, e)

    reg: dict[str, int] | None = None
    if args.region_file and Path(args.region_file).is_file():
        reg = load_saved_region(args.region_file)
    if reg is None:
        reg = load_saved_region(cfg.REGION_SAVE_FILE)
    if reg is None and getattr(args, "interactive_region", False):
        sel = select_region_interactive()
        save_region(cfg.REGION_SAVE_FILE, sel)
        reg = sel
    if reg is None and cfg.USE_INTERACTIVE_REGION_ON_FIRST_RUN:
        try:
            logging.getLogger(__name__).info("Abrindo seletor de região (legado).")
            sel = select_region_interactive()
            save_region(cfg.REGION_SAVE_FILE, sel)
            reg = sel
        except RuntimeError:
            logging.getLogger(__name__).warning("Seleção cancelada — usando CAPTURE_REGION.")
    reg = reg or dict(cfg.CAPTURE_REGION)
    return profile_from_legacy_single_region(reg, cfg.DEFAULT_ASSET)


def heuristic_llm_fallback(dimensions, risk) -> str:
    flags = getattr(risk, "flags", [])
    chk = getattr(risk, "checklist_lines", []) or []
    texto = "[LLM offline ou erro] Resumo local:\n"
    texto += (
        f"Probabilidade de continuação: {dimensions.probability_continuation * 100:.0f}%\n"
        f"Confiança da análise: {dimensions.confidence_label}\n"
        f"Risco contextual: {_risk_normalize_label(dimensions.contextual_risk)}\n"
        f"Recomendação: Não operar — serviço de IA não respondeu; use apenas diagnóstico local.\n"
    )
    if chk:
        texto += "\n".join(chk[:6])
    if flags:
        texto += "\nBandeiras: " + ", ".join(flags)
    return texto


def _risk_normalize_label(x: str) -> str:
    return {"BAIXO": "BAIXO", "MEDIO": "MEDIO", "ALTO": "ALTO"}.get(x.upper().replace("É", "E"), x)


def one_iteration(console: Console, llm: LlavaAnalyzer | None, profile: TradingProfile, skip_llm: bool) -> None:
    log = logging.getLogger(__name__)
    now = datetime.now()
    capture_ok = True
    llm_ok = True

    if not profile.regions:
        log.error("Perfil sem regiões — execute: python calibrate.py --profile <arquivo.json>")
        profile.regions["main_chart"] = dict(cfg.CAPTURE_REGION)

    snap = SnapshotSession(Path(cfg.SNAPSHOTS_DIR), now)
    raw_by_region: dict[str, bytes] = {}
    paths_written: dict[str, Path] = {}

    for name, rect in profile.regions.items():
        try:
            png = capture_region_png(dict(rect), None)
            raw_by_region[name] = png
            paths_written[name] = snap.write_raw_png(name, png)
            log_structured("capture", logging.INFO, "captura_regiao", region=name, w=rect["width"], h=rect["height"])
        except Exception as e:
            log.exception("Captura falhou em %s: %s", name, e)
            capture_ok = False
            with session_scope(cfg.DB_PATH) as s:
                s.add(OperatorLog(message=f"Captura falhou: {name}", level="ERROR", meta_json=json.dumps({"err": str(e)})))

    if not raw_by_region:
        log.error("Nenhuma região capturada — verifique o perfil ou calibrate.py.")
        return

    chart_key = "main_chart" if "main_chart" in raw_by_region else next(iter(raw_by_region))
    chart_bytes = raw_by_region.get(chart_key) or next(iter(raw_by_region.values()))

    for name, png in raw_by_region.items():
        try:
            proc = export_edges_preview_png(png)
            snap.write_processed_png(name, proc, suffix="edges")
        except Exception:
            pass

    preprocess = preprocess_chart(chart_bytes)
    patterns = patterns_to_dict(detect_basic_patterns(chart_bytes))
    trend = trend_to_dict(analyze_trend_from_silhouette(chart_bytes))
    regime = detect_market_regime(preprocess.metrics, trend, patterns)
    regime_dict = regime_to_prompt_dict(regime)

    by_ocr: dict[str, Any] = {}
    for rk, png in raw_by_region.items():
        spec = profile.pipeline_for(rk)
        try:
            res = run_region_ocr(rk, png, spec, profile.ocr_langs)
            by_ocr[rk] = res
            log_structured(
                "ocr",
                logging.INFO,
                "ocr_regiao",
                region=rk,
                mean_confidence=round(res.mean_confidence, 4),
                attempts=res.attempts_used,
            )
        except Exception as e:
            log.exception("OCR falhou em %s", rk)
            log_structured("ocr", logging.ERROR, "ocr_erro", region=rk, err=str(e))

    ocr_bundle = aggregate_ocr_bundle(by_ocr) if by_ocr else {
        "by_region": {},
        "price_candidates": [],
        "volume_candidates": [],
        "times": [],
        "texts": [],
        "merged_text": "",
        "ocr_scores": {},
        "ocr_global_score": 0.0,
    }

    th = profile.thresholds or {}
    edge_hi = float(th.get("edge_density_high", 0.22))
    edge_ex = float(th.get("edge_density_extreme", 0.38))
    allowed = _tuple_hours(profile.operating_hours) if profile.operating_hours else None

    risk = evaluate_contextual_risk(
        now,
        cfg.HIGH_RISK_HOURS,
        preprocess.metrics,
        ocr_bundle,
        trend,
        edge_density_high=edge_hi,
        edge_density_extreme=edge_ex,
        market_regime=regime.label,
        ocr_global_score=float(ocr_bundle.get("ocr_global_score") or 0.0) or None,
        allowed_operating_hours=allowed,
    )
    log_structured("risk", logging.INFO, "risco_ciclo", level=risk.level, flags=risk.flags)

    dimensions = score_operational_confidence(
        risk,
        preprocess.metrics,
        ocr_bundle,
        trend,
        cfg.MIN_CONFIDENCE_TO_SUGGEST,
        market_regime=regime.label,
    )

    with session_scope(cfg.DB_PATH) as s:
        hist = fetch_recent_analyses(s, profile.asset, cfg.RECENT_ANALYSES_FOR_PROMPT)
        reacts = fetch_similar_reactions(s, profile.asset, risk.level, limit=4)
        h_count = patterns.get("horizontal_lines") or patterns.get("horizontal_like") or 0
        if int(h_count) > 6:
            s.add(PatternRecord(asset=profile.asset, pattern_type="many_horizontal_lines", detection_data=json.dumps(patterns)))

    try:
        composite_bytes = build_composite(raw_by_region, profile.composite_layout or {})
        snap.write_composite(composite_bytes)
    except Exception as e:
        log.warning("Composite não gerado: %s", e)
        composite_bytes = chart_bytes

    ctx_dict = build_llm_context(
        asset=profile.asset,
        now=now,
        dimensions=dimensions,
        risk=risk,
        preprocess_metrics=preprocess.metrics,
        trend=trend,
        patterns=patterns,
        ocr=ocr_bundle,
        historical_analyses=hist,
        similar_reactions=reacts,
        market_regime=regime_dict,
        profile_name=profile.name,
    )

    img_b64 = base64.b64encode(composite_bytes).decode("ascii")
    messages = build_multimodal_messages(img_b64, ctx_dict)

    if skip_llm or llm is None:
        llm_resp = heuristic_llm_fallback(dimensions, risk)
        llm_ok = False
    else:
        try:
            llm_resp = llm.analyze_chart(composite_bytes, messages)
            log_structured("llm", logging.INFO, "llm_resposta", chars=len(llm_resp))
            llm_ok = True
        except Exception as e:
            log.exception("Chamada LLM falhou: %s", e)
            llm_resp = heuristic_llm_fallback(dimensions, risk)
            llm_ok = False
            log_structured("llm", logging.ERROR, "llm_erro", err=str(e))
            with session_scope(cfg.DB_PATH) as s:
                s.add(OperatorLog(message="Falha na chamada Ollama.", level="ERROR", meta_json=json.dumps({"err": str(e)})))

    parsed = parse_llm_response(llm_resp, dimensions)

    st_llm = "DESLIGADO" if skip_llm else ("OK" if llm_ok else "FALLBACK")

    primary_snap = paths_written.get(chart_key) or next(iter(paths_written.values()))
    meta = {
        "profile": profile.name,
        "asset": profile.asset,
        "regime": regime.label,
        "risk_level": risk.level,
        "flags": risk.flags,
        "ocr_global_score": ocr_bundle.get("ocr_global_score"),
        "regions": list(raw_by_region.keys()),
        "snapshot_stamp": snap.stamp,
    }
    meta_path = snap.write_metadata(meta)
    snap.write_analysis_sidecar(llm_resp[:12000])

    vision_blob = {
        "preprocess": preprocess.metrics,
        "trend": trend,
        "patterns": patterns,
        "regime": regime_dict,
        "profile": profile.name,
    }

    def _save_analysis() -> None:
        with session_scope(cfg.DB_PATH) as session:
            session.add(
                Analysis(
                    asset=profile.asset,
                    snapshot_path=str(primary_snap),
                    ocr_json=json.dumps(ocr_bundle, ensure_ascii=False),
                    vision_json=json.dumps(vision_blob, ensure_ascii=False),
                    risk_json=json.dumps({"level": risk.level, "flags": risk.flags, "lines": risk.checklist_lines}, ensure_ascii=False),
                    probability_continuation=float(parsed.probability_continuation),
                    confidence_level=parsed.confidence_level,
                    contextual_risk=parsed.contextual_risk,
                    recommendation=parsed.recommendation[:200],
                    justification=parsed.justification[:16000],
                    raw_llm_response=llm_resp[:32000],
                )
            )
            record_metric_event(
                session,
                profile_name=profile.name,
                asset=profile.asset,
                now=now,
                regime=regime.label,
                confidence_level=parsed.confidence_level,
                contextual_risk=parsed.contextual_risk,
                recommendation=parsed.recommendation,
                ocr_global_score=float(ocr_bundle.get("ocr_global_score") or 0.0) or None,
                capture_ok=capture_ok,
                llm_ok=llm_ok,
                meta={"composite_meta": str(meta_path), "regions_ok": list(raw_by_region.keys())},
            )

    try:
        _save_analysis()
    except Exception:
        log.exception("Falha ao persistir Analysis/MetricEvent.")

    hist_rows: list[dict] = []
    metrics_panel: dict = {}
    try:
        with session_scope(cfg.DB_PATH) as s:
            ah = fetch_recent_analyses(s, profile.asset, 12)
            for row in reversed(ah[-5:]):
                hist_rows.append(
                    {
                        "when": row.get("created_at", ""),
                        "confidence": row.get("confidence", ""),
                        "risk": row.get("risk", ""),
                        "rec": row.get("recommendation", ""),
                    }
                )
            metrics_panel = fetch_dashboard_metrics(s, since_hours=168)
    except Exception:
        log.exception("Histórico/métricas.")

    state = DashboardState(
        asset=profile.asset,
        clock=now,
        probability_pct=float(parsed.probability_continuation) * 100.0,
        confidence_level=parsed.confidence_level,
        contextual_risk=parsed.contextual_risk,
        recommendation=parsed.recommendation,
        justification_preview=parsed.justification,
        risk_flags=list(risk.flags),
        history_rows=hist_rows,
        profile_name=profile.name,
        regime_label=regime.label,
        regime_desc=regime.description_pt,
        status_capture="OK" if capture_ok else "ERRO",
        status_ocr=f"{float(ocr_bundle.get('ocr_global_score') or 0):.2f}",
        status_llm=st_llm,
        status_db="OK",
        metrics_summary=metrics_panel,
    )
    layout = build_dashboard(state)
    console.print(layout)
    log_structured("dashboard", logging.INFO, "render", profile=profile.name, regime=regime.label)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Market Copilot — copiloto local (sem ordens)")
    p.add_argument("--profile", type=str, default=None, help="JSON de perfil (regiões + OCR). Default: ACTIVE_PROFILE_PATH em config.")
    p.add_argument("--interactive-region", action="store_true", help="(Legado) seleciona uma região única e salva em capture_region.json")
    p.add_argument("--once", action="store_true")
    env_skip = os.environ.get("COPILOT_SKIP_LLM", "").lower() in ("1", "true", "yes")
    p.add_argument("--skip-llm", action="store_true", default=env_skip)
    p.add_argument("--region-file", type=str, default=None)
    return p


def main() -> None:
    args = build_arg_parser().parse_args()

    Path(cfg.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(cfg.SNAPSHOTS_DIR).mkdir(parents=True, exist_ok=True)
    Path(cfg.CHANNEL_LOG_DIR).mkdir(parents=True, exist_ok=True)

    setup_logging(cfg.LOG_FILE, cfg.LOG_LEVEL)
    setup_channel_logging(cfg.CHANNEL_LOG_DIR, cfg.LOG_LEVEL)

    logging.getLogger(__name__).info(
        "Market Copilot — perfil ativo sugerido: %s | Execução automática de ordens: DESLIGADO.",
        cfg.ACTIVE_PROFILE_PATH,
    )

    profile = resolve_trading_profile(args)

    llm_client: LlavaAnalyzer | None = None
    if not args.skip_llm:
        try:
            llm_client = LlavaAnalyzer(cfg.OLLAMA_HOST, cfg.OLLAMA_MODEL)
        except Exception as e:
            logging.getLogger(__name__).warning("Cliente Ollama indisponível: %s", e)
            llm_client = None

    console = Console(file=sys.stdout)

    if args.once:
        one_iteration(console, llm_client, profile, skip_llm=args.skip_llm or llm_client is None)
        return

    logging.getLogger(__name__).info("Loop %ss | modelo=%s", cfg.CAPTURE_INTERVAL_SECONDS, cfg.OLLAMA_MODEL)
    try:
        while True:
            console.clear()
            one_iteration(console, llm_client, profile, skip_llm=args.skip_llm or llm_client is None)
            time.sleep(cfg.CAPTURE_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Interrompido pelo operador.")
    logging.getLogger(__name__).info("Encerramento limpo.")


if __name__ == "__main__":
    main()
