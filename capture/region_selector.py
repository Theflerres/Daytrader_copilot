"""
Seleção interativa da região do gráfico com captura congelada da tela.
Retorna dict compatível com MSS: top, left, width, height.
"""
from __future__ import annotations

import json
import logging
import platform
from pathlib import Path
from typing import Any

import tkinter as tk

from mss import mss
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)


def _enable_windows_dpi_awareness() -> None:
    """Ativa DPI awareness para obter coordenadas físicas reais no Windows."""
    if platform.system() != "Windows":
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32
        # Per-monitor DPI aware v2 (Windows 10+)
        dpi_context = ctypes.c_void_p(-4)
        if hasattr(user32, "SetProcessDpiAwarenessContext"):
            user32.SetProcessDpiAwarenessContext(dpi_context)
            return
    except Exception:
        pass

    try:
        import ctypes

        shcore = ctypes.windll.shcore
        # PROCESS_PER_MONITOR_DPI_AWARE
        shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    try:
        import ctypes

        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
    except Exception as e:
        logger.debug("Não foi possível ativar DPI awareness: %s", e)


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


def _capture_virtual_screen() -> tuple[Image.Image, dict[str, int]]:
    """Captura screenshot da tela virtual inteira (todos os monitores) com MSS."""
    with mss() as sct:
        virtual = sct.monitors[0]
        shot = sct.grab(virtual)
    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    region = {
        "left": int(virtual["left"]),
        "top": int(virtual["top"]),
        "width": int(virtual["width"]),
        "height": int(virtual["height"]),
    }
    return img, region


def select_region_interactive(debug_output_path: str = "debug/selected_region.png") -> dict[str, int]:
    """
    Congela a tela virtual e permite arrastar uma região sobre a imagem congelada.
    Enter confirma; Esc cancela (levanta RuntimeError).

    Retorno: coordenadas absolutas reais do desktop virtual compatíveis com MSS.
    """
    _enable_windows_dpi_awareness()
    frozen_img, virtual_region = _capture_virtual_screen()

    result: dict[str, int] = {}
    start_canvas: dict[str, int] = {}

    root = tk.Tk()
    root.title("Selecionar Região")
    root.attributes("-topmost", True)
    root.configure(cursor="crosshair")

    screen_left = virtual_region["left"]
    screen_top = virtual_region["top"]
    screen_width = virtual_region["width"]
    screen_height = virtual_region["height"]

    root.geometry(f"{screen_width}x{screen_height}+{screen_left}+{screen_top}")
    root.overrideredirect(True)

    canvas = tk.Canvas(root, highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    photo = ImageTk.PhotoImage(frozen_img)
    canvas.create_image(0, 0, image=photo, anchor="nw")

    rect_id: int | None = None
    info_var = tk.StringVar(value="left=?, top=?, w=?, h=?")

    canvas.create_rectangle(10, 10, 650, 55, fill="black", stipple="gray50", outline="")
    canvas.create_text(
        20,
        20,
        anchor="nw",
        fill="white",
        font=("Segoe UI", 11, "bold"),
        text="Arraste para selecionar | Enter = OK | Esc = cancelar",
    )
    info_coords_id = canvas.create_text(
        20,
        40,
        anchor="nw",
        fill="cyan",
        font=("Consolas", 11),
        text=info_var.get(),
    )

    def refresh_info_text() -> None:
        canvas.itemconfigure(info_coords_id, text=info_var.get())

    def on_press(event: tk.Event) -> None:
        nonlocal rect_id
        start_canvas["x"], start_canvas["y"] = int(event.x), int(event.y)
        if rect_id is not None:
            canvas.delete(rect_id)
            rect_id = None

    def on_drag(event: tk.Event) -> None:
        nonlocal rect_id
        x0, y0 = start_canvas["x"], start_canvas["y"]
        x1, y1 = int(event.x), int(event.y)
        if rect_id is not None:
            canvas.delete(rect_id)

        rx0, ry0 = min(x0, x1), min(y0, y1)
        rx1, ry1 = max(x0, x1), max(y0, y1)
        rect_id = canvas.create_rectangle(rx0, ry0, rx1, ry1, outline="cyan", width=2)

        abs_left = screen_left + rx0
        abs_top = screen_top + ry0
        abs_width = rx1 - rx0
        abs_height = ry1 - ry0
        info_var.set(f"left={abs_left}, top={abs_top}, w={abs_width}, h={abs_height}")
        refresh_info_text()

    def on_release(event: tk.Event) -> None:
        x0, y0 = start_canvas["x"], start_canvas["y"]
        x1, y1 = int(event.x), int(event.y)

        rx0, ry0 = min(x0, x1), min(y0, y1)
        rx1, ry1 = max(x0, x1), max(y0, y1)

        width = rx1 - rx0
        height = ry1 - ry0
        if width < 20 or height < 20:
            return

        result["left"] = screen_left + rx0
        result["top"] = screen_top + ry0
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

    root.mainloop()
    root.destroy()

    if not result:
        raise RuntimeError("Seleção de região cancelada ou inválida.")

    try:
        crop_box = (
            result["left"] - screen_left,
            result["top"] - screen_top,
            result["left"] - screen_left + result["width"],
            result["top"] - screen_top + result["height"],
        )
        debug_img = frozen_img.crop(crop_box)
        dbg_path = Path(debug_output_path)
        dbg_path.parent.mkdir(parents=True, exist_ok=True)
        debug_img.save(dbg_path)
        logger.info("Screenshot de debug salvo em %s", dbg_path)
    except Exception as e:
        logger.warning("Falha ao salvar screenshot de debug da região: %s", e)

    logger.info("Região selecionada (coords MSS): %s", result)
    return result
