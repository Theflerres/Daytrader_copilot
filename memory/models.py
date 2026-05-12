"""Modelos SQLAlchemy — análises, reações de mercado, padrões e log do operador."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Analysis(Base):
    """Análises geradas pelo copiloto (texto + métricas extraídas)."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    asset: Mapped[str] = mapped_column(String(32), default="WINFUT")
    snapshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ocr_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    vision_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    probability_continuation: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    contextual_risk: Mapped[str | None] = mapped_column(String(16), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(64), nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_llm_response: Mapped[str | None] = mapped_column(Text, nullable=True)


class MarketReaction(Base):
    """Memória de reação contextual do mercado (schema alinhado ao prompt v2)."""

    __tablename__ = "market_reactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    asset: Mapped[str] = mapped_column(String(32))
    event_type: Mapped[str] = mapped_column(String(32))
    event_description: Mapped[str] = mapped_column(Text)
    market_condition_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_reaction: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PatternRecord(Base):
    """Detecções visuais básicas persistidas para consulta histórica."""

    __tablename__ = "patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    asset: Mapped[str] = mapped_column(String(32))
    pattern_type: Mapped[str] = mapped_column(String(64))
    detection_data: Mapped[str | None] = mapped_column(Text, nullable=True)


class OperatorFeedback(Base):
    """Feedback humano esparso para medir evolução (precisão contextual futura)."""

    __tablename__ = "operator_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    analysis_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    label: Mapped[str] = mapped_column(String(32))  # ok | false_positive | false_negative | skip


class MetricEvent(Base):
    """Evento agregado por ciclo — base para dashboard de métricas e estudos offline."""

    __tablename__ = "metric_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    profile_name: Mapped[str] = mapped_column(String(64), default="default")
    asset: Mapped[str] = mapped_column(String(32))
    hour_bucket: Mapped[int] = mapped_column(Integer)
    regime: Mapped[str] = mapped_column(String(48))
    confidence_level: Mapped[str] = mapped_column(String(16))
    contextual_risk: Mapped[str] = mapped_column(String(16))
    dont_operar: Mapped[int] = mapped_column(Integer, default=0)  # 0/1
    ocr_global_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    capture_ok: Mapped[int] = mapped_column(Integer, default=1)
    llm_ok: Mapped[int] = mapped_column(Integer, default=1)
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class OperatorLog(Base):
    """Registro opcional do operador (sessão, observações estruturadas)."""

    __tablename__ = "operator_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    message: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(16), default="INFO")
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
