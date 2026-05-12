"""Enumeração de monitores via MSS (coordenadas absolutas no desktop virtual)."""
from __future__ import annotations

from typing import Any

from mss import mss


def list_monitors() -> list[dict[str, Any]]:
    """
    Retorna lista de monitores; índice 0 é virtual 'all', índice 1+ são físicos.
    Cada item: left, top, width, height, index.
    """
    with mss() as sct:
        mons = sct.monitors
    out: list[dict[str, Any]] = []
    for i, m in enumerate(mons):
        out.append(
            {
                "index": i,
                "left": int(m["left"]),
                "top": int(m["top"]),
                "width": int(m["width"]),
                "height": int(m["height"]),
                "is_virtual_all": i == 0,
            }
        )
    return out


def monitor_region(index: int) -> dict[str, int]:
    """Retorna dict MSS {left, top, width, height} para o monitor informado."""
    with mss() as sct:
        if index < 0 or index >= len(sct.monitors):
            index = 1 if len(sct.monitors) > 1 else 0
        m = sct.monitors[index]
        return {"left": int(m["left"]), "top": int(m["top"]), "width": int(m["width"]), "height": int(m["height"])}
