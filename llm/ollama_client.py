"""Cliente Ollama para modelo multimodal (llava): imagem + texto local."""
from __future__ import annotations

import base64
import logging
from typing import Any

import ollama

logger = logging.getLogger(__name__)


class LlavaAnalyzer:
    def __init__(self, host: str, model: str, timeout_sec: float = 180.0) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout_sec = timeout_sec
        self._client = ollama.Client(host=self.host, timeout=timeout_sec)

    def analyze_chart(self, image_png: bytes, messages: list[dict[str, Any]]) -> str:
        """
        Recebe messages já montadas pelo prompt_builder (contém texto + campo images).
        Garante que a imagem atual substitua qualquer placeholder vazio na primeira mensagem user.
        """
        if not messages:
            raise ValueError("messages vazio.")

        msgs = [dict(m) for m in messages]
        b64 = base64.b64encode(image_png).decode("ascii")

        user0 = msgs[0]
        if user0.get("role") != "user":
            raise ValueError("Primeira mensagem deve ser 'user' no MVP.")
        user0["images"] = [b64]

        try:
            resp = self._client.chat(model=self.model, messages=msgs)
        except Exception as e:
            logger.exception("Erro ao chamar Ollama (%s modelo=%s): %s", self.host, self.model, e)
            raise

        msg = getattr(resp, "message", None)
        text = getattr(msg, "content", "") if msg is not None else ""
        if not text and isinstance(resp, dict):
            text = (resp.get("message") or {}).get("content") or ""

        logger.info("LLM retornou %d caracteres de texto.", len(text))
        return text.strip() if text else 'Recomendação: aguardar; modelo retornou vazio. Verifique GPU/RAM ou "ollama pull llava".'
