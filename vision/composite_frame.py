"""
Monta uma única imagem (composite) a partir de vários PNGs nomeados — melhora contexto multimodal.
Layout configurável por linhas de chaves de região.
"""
from __future__ import annotations

import io
import logging
from typing import Any

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def _load_png(b: bytes) -> Image.Image:
    return Image.open(io.BytesIO(b)).convert("RGB")


def build_composite(
    images: dict[str, bytes],
    layout: dict[str, Any],
    *,
    cell_max_width: int | None = None,
    padding: int = 4,
    draw_labels: bool = True,
    background: tuple[int, int, int] = (24, 24, 24),
) -> bytes:
    """
    images: chave = nome da região (ex.: main_chart), valor = PNG bytes.
    layout: { "rows": [["main_chart","volume"], ["tape","book"]], "cell_max_width": 640 }
    """
    rows_cfg = layout.get("rows") or [["main_chart"]]
    cmw = int(layout.get("cell_max_width") or cell_max_width or 520)
    pad = int(layout.get("padding", padding))
    labels = bool(layout.get("labels", draw_labels))

    rows: list[list[Image.Image | None]] = []
    row_keys: list[list[str | None]] = []
    for row_keys_raw in rows_cfg:
        row_imgs: list[Image.Image | None] = []
        rk: list[str | None] = []
        for key in row_keys_raw:
            key = str(key)
            rk.append(key)
            raw = images.get(key)
            if not raw:
                row_imgs.append(None)
                continue
            try:
                im = _load_png(raw)
                w, h = im.size
                if w > cmw:
                    nh = max(1, int(h * (cmw / w)))
                    im = im.resize((cmw, nh), Image.Resampling.LANCZOS)
                row_imgs.append(im)
            except Exception as e:
                logger.warning("Falha ao carregar região %s no composite: %s", key, e)
                row_imgs.append(None)
        rows.append(row_imgs)
        row_keys.append(rk)

    # Altura por linha = max altura; largura total = soma larguras + pads
    row_heights: list[int] = []
    row_widths: list[int] = []
    for row_imgs in rows:
        hmax = 0
        wsum = pad
        for im in row_imgs:
            if im is None:
                continue
            hmax = max(hmax, im.size[1])
            wsum += im.size[0] + pad
        row_heights.append(max(hmax, 40))
        row_widths.append(wsum)

    total_w = max(row_widths) if row_widths else 400
    total_h = sum(row_heights) + pad * (len(rows) + 1)
    canvas = Image.new("RGB", (total_w, total_h), color=background)
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    y = pad
    for ri, row_imgs in enumerate(rows):
        x = pad
        hline = row_heights[ri]
        keys_line = row_keys[ri]
        for ci, im in enumerate(row_imgs):
            key = keys_line[ci] if ci < len(keys_line) else ""
            if im is None:
                x += pad
                continue
            w, h = im.size
            y_off = y + (hline - h) // 2
            canvas.paste(im, (x, y_off))
            if labels and key and font:
                draw.rectangle((x, y_off - 14, x + w, y_off), fill=(0, 0, 0))
                draw.text((x + 2, y_off - 12), key, fill=(200, 200, 200), font=font)
            x += w + pad
        y += hline + pad

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
