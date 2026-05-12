#!/usr/bin/env python3
"""
Wizard visual de calibração — multi-monitor, regiões nomeadas e preview.
Uso: python calibrate.py --profile profiles/winfut_layout.json [--monitor 2]
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from io import BytesIO
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from capture.monitors import list_monitors, monitor_region
from capture.screen_capture import capture_region_png
from core.profile_loader import TradingProfile, load_trading_profile, save_trading_profile

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

STANDARD_KEYS = ["main_chart", "volume", "tape", "book", "clock", "position_area"]


def _ensure_profile(path: Path) -> TradingProfile:
    if path.is_file():
        return load_trading_profile(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    p = TradingProfile(
        name=path.stem,
        asset="WINFUT",
        regions={},
        ocr_langs=["pt", "en"],
        composite_layout={
            "rows": [["main_chart", "volume"], ["tape", "book"]],
            "cell_max_width": 640,
            "padding": 4,
            "labels": True,
        },
    )
    save_trading_profile(path, p)
    return p


class CalibratorApp:
    def __init__(self, profile_path: Path, monitor_index: int | None) -> None:
        self.profile_path = profile_path
        self.profile = _ensure_profile(profile_path)
        self.monitor_index = monitor_index
        self.monitors = [m for m in list_monitors() if not m.get("is_virtual_all")]
        self.selected_monitor = self.monitors[0]["index"] if self.monitors else 1
        self.current_key_idx = 0
        self.keys_queue = list(STANDARD_KEYS)
        self._pending_rect: dict[str, int] | None = None
        self.preview_win: tk.Toplevel | None = None
        self.preview_label: tk.Label | None = None
        self._photo_ref: ImageTk.PhotoImage | None = None

        self.root = tk.Tk()
        self.root.title("Market Copilot — Calibração de regiões")
        self.root.geometry("520x400")

        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text=f"Perfil: {self.profile_path}", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(frm, text="1) Escolha o monitor alvo (onde está o Profit / gráfico).").pack(anchor="w", pady=(8, 2))

        self.var_mon = tk.IntVar(value=self._default_monitor_var())
        for m in self.monitors:
            ttk.Radiobutton(
                frm,
                text=f"Monitor #{m['index']}  {m['width']}x{m['height']} @ ({m['left']},{m['top']})",
                variable=self.var_mon,
                value=m["index"],
            ).pack(anchor="w")

        ttk.Button(frm, text="Iniciar desenho de regiões", command=self._start_draw_flow).pack(pady=16)

        self.status = ttk.Label(frm, text="")
        self.status.pack(anchor="w")

    def _default_monitor_var(self) -> int:
        if self.monitor_index is not None:
            for m in self.monitors:
                if m["index"] == self.monitor_index:
                    return self.monitor_index
        return self.monitors[0]["index"] if self.monitors else 1

    def _start_draw_flow(self) -> None:
        self.selected_monitor = int(self.var_mon.get())
        self.current_key_idx = 0
        self._next_region_prompt()

    def _next_region_prompt(self) -> None:
        if self.current_key_idx >= len(self.keys_queue):
            save_trading_profile(self.profile_path, self.profile)
            messagebox.showinfo("Calibração", f"Regiões salvas em:\n{self.profile_path}")
            self.root.destroy()
            return

        key = self.keys_queue[self.current_key_idx]
        self.status.config(text=f"Desenhe a região: {key}  (Enter=confirmar área vazia pula)")
        self._open_overlay_for_key(key)

    def _open_overlay_for_key(self, key: str) -> None:
        mon = monitor_region(self.selected_monitor)
        geo = f"{mon['width']}x{mon['height']}+{mon['left']}+{mon['top']}"

        overlay = tk.Toplevel(self.root)
        overlay.geometry(geo)
        overlay.attributes("-alpha", 0.28)
        overlay.attributes("-topmost", True)
        overlay.overrideredirect(True)
        overlay.focus_force()
        canvas = tk.Canvas(overlay, highlightthickness=0, bg="#1a1a1a", cursor="crosshair")
        canvas.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            overlay,
            text=f"{key} — arraste o retângulo ou ajuste valores exatos abaixo | Enter=gravar | Esc=pular",
            fg="white",
            bg="black",
        ).place(x=8, y=8)

        coord_var = tk.StringVar(value="left=?, top=?, w=?, h=?")
        tk.Label(overlay, textvariable=coord_var, fg="white", bg="black").place(x=8, y=32)

        left_var = tk.StringVar(value="0")
        top_var = tk.StringVar(value="0")
        width_var = tk.StringVar(value="0")
        height_var = tk.StringVar(value="0")

        control_frame = tk.Frame(overlay, bg="black")
        control_frame.place(x=8, y=56)

        field_labels = [
            ("left", left_var),
            ("top", top_var),
            ("width", width_var),
            ("height", height_var),
        ]
        for idx, (label_text, var) in enumerate(field_labels):
            tk.Label(control_frame, text=f"{label_text}:", fg="white", bg="black").grid(row=idx, column=0, sticky="w", padx=(0, 4), pady=2)
            ttk.Entry(control_frame, width=8, textvariable=var).grid(row=idx, column=1, sticky="w", pady=2)

        tk.Label(
            control_frame,
            text="Ajuste manual e pressione Enter para confirmar a área exata.",
            fg="white",
            bg="black",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        def set_coords(left: int, top: int, w: int, h: int) -> None:
            left_var.set(str(left))
            top_var.set(str(top))
            width_var.set(str(w))
            height_var.set(str(h))
            coord_var.set(f"left={left}, top={top}, w={w}, h={h}")

        def parse_manual_coords() -> dict[str, int] | None:
            try:
                left = int(left_var.get())
                top = int(top_var.get())
                width = int(width_var.get())
                height = int(height_var.get())
            except ValueError:
                return None
            if width < 15 or height < 15:
                return None
            return {"left": left, "top": top, "width": width, "height": height}

        start: dict[str, int] = {}
        rect_id: int | None = None
        self._pending_rect = None

        def on_press(e: tk.Event) -> None:
            nonlocal rect_id
            start["x"], start["y"] = e.x_root, e.y_root
            if rect_id is not None:
                canvas.delete(rect_id)

        def on_drag(e: tk.Event) -> None:
            nonlocal rect_id
            x0, y0 = start["x"], start["y"]
            x1, y1 = e.x_root, e.y_root
            rx0 = min(x0, x1) - overlay.winfo_rootx()
            ry0 = min(y0, y1) - overlay.winfo_rooty()
            rx1 = max(x0, x1) - overlay.winfo_rootx()
            ry1 = max(y0, y1) - overlay.winfo_rooty()
            if rect_id is not None:
                canvas.delete(rect_id)
            rect_id = canvas.create_rectangle(rx0, ry0, rx1, ry1, outline="#00ffff", width=2)
            left, top, w, h = min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)
            set_coords(left, top, w, h)
            self._schedule_preview((left, top, w, h))

        def on_release(e: tk.Event) -> None:
            x0, y0 = start.get("x", e.x_root), start.get("y", e.y_root)
            x1, y1 = e.x_root, e.y_root
            left, top, w, h = min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)
            if w >= 15 and h >= 15:
                self._pending_rect = {"left": left, "top": top, "width": w, "height": h}

        def confirm(_: tk.Event | None = None) -> None:
            overlay.destroy()
            manual = parse_manual_coords()
            if manual is not None:
                self.profile.regions[key] = manual
            elif self._pending_rect is not None:
                self.profile.regions[key] = dict(self._pending_rect)
            self.current_key_idx += 1
            save_trading_profile(self.profile_path, self.profile)
            self._next_region_prompt()

        def cancel(_: tk.Event | None = None) -> None:
            overlay.destroy()
            self.current_key_idx += 1
            self._next_region_prompt()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        overlay.bind("<Return>", confirm)
        overlay.bind("<Escape>", cancel)

    def _schedule_preview(self, rect: tuple[int, int, int, int]) -> None:
        if Image is None:
            return

        def job() -> None:
            time.sleep(0.05)
            try:
                region = {"left": rect[0], "top": rect[1], "width": rect[2], "height": rect[3]}
                png = capture_region_png(region, None)
                im = Image.open(BytesIO(png)).convert("RGB")
                im.thumbnail((360, 220))
                self.root.after(0, lambda: self._show_preview(im))
            except Exception:
                pass

        threading.Thread(target=job, daemon=True).start()

    def _show_preview(self, im: "Image.Image") -> None:
        if ImageTk is None:
            return
        if self.preview_win is None or not self.preview_win.winfo_exists():
            self.preview_win = tk.Toplevel(self.root)
            self.preview_win.title("Preview captura")
            self.preview_win.geometry("+80+80")
            self.preview_label = tk.Label(self.preview_win, bg="black")
            self.preview_label.pack()
        self._photo_ref = ImageTk.PhotoImage(im)
        if self.preview_label:
            self.preview_label.configure(image=self._photo_ref)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    ap = argparse.ArgumentParser(description="Wizard de calibração Market Copilot")
    ap.add_argument("--profile", type=str, required=True, help="Caminho do JSON de perfil (ex.: profiles/winfut_layout.json)")
    ap.add_argument("--monitor", type=int, default=None, help="Índice MSS do monitor (1=primeiro físico)")
    args = ap.parse_args()
    path = Path(args.profile)
    CalibratorApp(path, args.monitor).run()


if __name__ == "__main__":
    main()
