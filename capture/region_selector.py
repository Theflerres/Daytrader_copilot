"""
Seleção interativa da região do gráfico (tela cheia + arrastar retângulo).
Retorna dict compatível com MSS: top, left, width, height.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import simpledialog

logger = logging.getLogger(__name__)


def save_region(path: str, region: dict[str, int]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(region, indent=2), encoding="utf-8")
    logger.info("Região salva em %s", path)


def load_saved_region(path: str) -> dict[str, int] | None:
    """Carrega region do JSON; None se arquivo inexistente ou inválido."""
    p = Path(path)
    if not p.is_file():
        return None
    try:
        data: Any = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return {
            "top": int(data["top"]),
            "left": int(data["left"]),
            "width": int(data["width"]),
            "height": int(data["height"]),
        }
    except Exception as e:
        logger.warning("Não foi possível carregar região salva: %s", e)
        return None


def select_region_interactive() -> dict[str, int]:
    """
    Abre overlay em tela cheia: arraste com o botão esquerdo para definir o retângulo.
    Enter confirma; Esc cancela (levanta RuntimeError).
    """
    result: dict[str, int] = {}
    start: dict[str, int] = {}

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.25)
    root.configure(cursor="crosshair")

    canvas = tk.Canvas(root, highlightthickness=0, bg="gray20")
    canvas.pack(fill=tk.BOTH, expand=True)
    rect_id: int | None = None

    def on_press(event: tk.Event) -> None:
        nonlocal rect_id
        start["x"], start["y"] = event.x_root, event.y_root
        if rect_id is not None:
            canvas.delete(rect_id)
            rect_id = None

    info_var = tk.StringVar(value="left=?, top=?, w=?, h=?")
    tk.Label(root, textvariable=info_var, bg="gray10", fg="white").place(x=20, y=50)

    def on_drag(event: tk.Event) -> None:
        nonlocal rect_id
        x0, y0 = start["x"], start["y"]
        x1, y1 = event.x_root, event.y_root
        if rect_id is not None:
            canvas.delete(rect_id)
        # Converte coords de tela para coords do canvas
        rx0 = min(x0, x1) - root.winfo_rootx()
        ry0 = min(y0, y1) - root.winfo_rooty()
        rx1 = max(x0, x1) - root.winfo_rootx()
        ry1 = max(y0, y1) - root.winfo_rooty()
        rect_id = canvas.create_rectangle(rx0, ry0, rx1, ry1, outline="cyan", width=2)
        info_var.set(
            f"left={min(x0, x1)}, top={min(y0, y1)}, w={abs(x1 - x0)}, h={abs(y1 - y0)}"
        )

    def on_release(event: tk.Event) -> None:
        x0, y0 = start["x"], start["y"]
        x1, y1 = event.x_root, event.y_root
        left = min(x0, x1)
        top = min(y0, y1)
        width = abs(x1 - x0)
        height = abs(y1 - y0)
        if width < 20 or height < 20:
            return
        result["left"] = left
        result["top"] = top
        result["width"] = width
        result["height"] = height

    def confirm(_: tk.Event | None = None) -> None:
        root.quit()

    def cancel(_: tk.Event | None = None) -> None:
        result.clear()
        root.quit()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Return>", confirm)
    root.bind("<Escape>", cancel)

    tk.Label(root, text="Arraste para selecionar a região do gráfico | Enter = OK | Esc = cancelar", bg="gray10", fg="white").place(
        x=20, y=20
    )

    root.mainloop()
    root.destroy()

    if not result:
        raise RuntimeError("Seleção de região cancelada ou inválida.")
    logger.info("Região selecionada: %s", result)
    return result
