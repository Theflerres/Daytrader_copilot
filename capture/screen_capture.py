"""Captura de tela com MSS — imagem PNG em memória ou arquivo."""
from __future__ import annotations

import io
import logging
import time
from pathlib import Path
from typing import Iterator

from mss import mss
from PIL import Image

logger = logging.getLogger(__name__)


def capture_region_png(region: dict, output_path: str | None = None) -> bytes:
    """
    Captura a região informada ({top, left, width, height}) e devolve PNG em bytes.
    Se output_path for passado, grava também no disco.
    """
    with mss() as sct:
        shot = sct.grab(region)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(data)
    return data


class ContinuousCaptureLoop:
    """
    Gerador síncrono: a cada intervalo produz PNG bytes (utilidade para testes).
    O fluxo principal em main.py usa sleep explícito + capture_region_png.
    """

    def __init__(self, region: dict, interval_seconds: float) -> None:
        self.region = region
        self.interval_seconds = interval_seconds

    def __iter__(self) -> Iterator[bytes]:
        while True:
            try:
                yield capture_region_png(self.region)
            except Exception as e:
                logger.exception("Falha na captura contínua: %s", e)
            time.sleep(self.interval_seconds)
