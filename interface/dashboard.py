"""Dashboard Rich — três colunas (humano / técnico / debug) para monitor ultrawide."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from rich import box
from rich.console import Group
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _risk_pt(risk: str) -> str:
    return {"BAIXO": "BAIXO", "MEDIO": "MÉDIO", "ALTO": "ALTO"}.get(risk.upper(), risk)


def _style_conf(conf: str) -> str:
    return {
        "ALTA": "bold green",
        "MEDIA": "yellow",
        "BAIXA": "bold red",
        "INVALIDA": "bold magenta",
    }.get(conf.upper(), "white")


def _style_risk(risk: str) -> str:
    return {"BAIXO": "cyan", "MEDIO": "yellow", "ALTO": "bold red reverse"}.get(risk.upper(), "white")


@dataclass
class DashboardState:
    asset: str
    clock: datetime
    probability_pct: float
    confidence_level: str
    contextual_risk: str
    recommendation: str
    justification_preview: str
    risk_flags: list[str]
    history_rows: list[dict[str, Any]]
    profile_name: str = ""
    regime_label: str = ""
    regime_desc: str = ""
    status_capture: str = "OK"
    status_ocr: str = "—"
    status_llm: str = "OK"
    status_db: str = "OK"
    metrics_summary: dict[str, Any] = field(default_factory=dict)


def _arrow_for_conf(label: str) -> str:
    u = label.upper()
    return "▼" if u in ("BAIXA", "INVALIDA") else ("▶" if u == "MEDIA" else "▲")


def _arrow_for_risk(label: str) -> str:
    u = label.upper()
    return "▲" if u == "ALTO" else "▼" if u == "BAIXO" else "▶"


def _human_panel(state: DashboardState) -> Panel:
    probs = Table.grid(expand=True)
    probs.add_column(justify="left", ratio=2)
    probs.add_column(justify="left")
    probs.add_row("Probabilidade de continuação:", Text(f"{state.probability_pct:.0f}%", style="bold white"))
    probs.add_row(
        "Confiança da análise:",
        Text(f"{_arrow_for_conf(state.confidence_level)} {state.confidence_level}", style=_style_conf(state.confidence_level)),
    )
    probs.add_row(
        "Risco contextual:",
        Text(f"{_arrow_for_risk(state.contextual_risk)} {_risk_pt(state.contextual_risk)}", style=_style_risk(state.contextual_risk)),
    )
    reco = Text(
        state.recommendation,
        style="bold yellow" if ("NÃO OPERAR" in state.recommendation.upper() or "NAO OPERAR" in state.recommendation.upper()) else "bold white",
    )
    upper_rec = state.recommendation.upper()
    prefix = ""
    if "NÃO OPERAR" in upper_rec or "NAO OPERAR" in upper_rec or state.confidence_level.upper() == "INVALIDA":
        prefix = "[bold red blink][!] RECOMENDAÇÃO CRÍTICA[/]\n"
    body = Group(
        Text.from_markup(prefix) if prefix else Text(""),
        probs,
        Text(""),
        Text(f"[dim]Perfil:[/] {state.profile_name or '—'}  [dim]Regime:[/] [cyan]{state.regime_label or '—'}[/]"),
        Text(f"[dim]{state.regime_desc[:220]}{'…' if len(state.regime_desc) > 220 else ''}[/]", justify="full"),
        Text(""),
        Text.from_markup("[bold]Interpretação[/]"),
        Text(state.justification_preview[:650] + ("…" if len(state.justification_preview) > 650 else ""), justify="full"),
        Text(""),
        reco,
    )
    return Panel(body, title="Painel humano", border_style="green", box=box.ROUNDED, padding=(1, 2))


def _technical_panel(state: DashboardState) -> Panel:
    m = state.metrics_summary or {}
    t = Table(title="Métricas (7d)", box=box.SIMPLE, expand=True)
    t.add_column("Indicador", style="dim")
    t.add_column("Valor")
    t.add_row("Amostras", str(m.get("samples", "—")))
    t.add_row("Taxa 'não operar'", str(m.get("dont_operar_rate", "—")))
    t.add_row("OCR médio", str(m.get("avg_ocr_score", "—")))
    t.add_row("Feedback humano (n)", str(m.get("feedback_samples", "—")))
    note = Text(m.get("feedback_pending_note", ""), style="dim", justify="left")

    hist = _history_table(state.history_rows)
    body = Group(t, Text(""), note, Text(""), Text.from_markup("[bold]Histórico recente[/]"), hist)
    return Panel(body, title="Painel técnico", border_style="blue", box=box.ROUNDED, padding=(1, 2))


def _debug_panel(state: DashboardState) -> Panel:
    st = Table.grid(expand=True)
    st.add_column("Subsistema", style="dim")
    st.add_column("Estado")
    st.add_row("Captura", state.status_capture)
    st.add_row("OCR (score)", state.status_ocr)
    st.add_row("LLM", state.status_llm)
    st.add_row("SQLite", state.status_db)

    fl = ", ".join(state.risk_flags) if state.risk_flags else "—"
    body = Group(
        st,
        Text(""),
        Text.from_markup("[bold]Flags de risco[/]"),
        Text(fl, overflow="fold"),
    )
    return Panel(body, title="Painel debug", border_style="grey50", box=box.ROUNDED, padding=(1, 2))


def build_dashboard(state: DashboardState) -> Layout:
    hdr = Panel.fit(
        Text.from_markup(
            f"[bold white]MARKET COPILOT[/]  •  [cyan]{state.asset}[/]  •  [dim]{state.clock:%Y-%m-%d %H:%M:%S}[/]"
        ),
        box=box.DOUBLE_EDGE,
        style="grey39",
        padding=(0, 2),
    )
    row = Layout()
    row.split_row(
        Layout(_human_panel(state), name="human", ratio=2),
        Layout(_technical_panel(state), name="tech", ratio=2),
        Layout(_debug_panel(state), name="dbg", ratio=1),
    )
    root = Layout()
    root.split_column(Layout(hdr, size=5), Layout(row, name="main", ratio=1))
    return root


def _history_table(rows: list[dict[str, Any]]) -> Table:
    t = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
    t.add_column("Quando")
    t.add_column("Conf")
    t.add_column("Risco")
    t.add_column("Rec", overflow="ellipsis", max_width=28)
    for r in reversed(rows[-6:]):
        t.add_row(str(r.get("when", ""))[:19], str(r.get("confidence", "")), str(r.get("risk", "")), str(r.get("rec", ""))[:56])
    return t
