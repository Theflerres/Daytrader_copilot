"""
Configuração central do Market Copilot (MVP).
Todas as variáveis ajustáveis devem ficar aqui.
"""
from __future__ import annotations

import os
from pathlib import Path

# Diretório raiz do projeto (pasta onde este arquivo está)
ROOT_DIR = Path(__file__).resolve().parent

# Região legada (sem perfil JSON)
CAPTURE_REGION = {"top": 100, "left": 0, "width": 1280, "height": 720}

# Perfil padrão quando --profile não é passado e este arquivo existe
ACTIVE_PROFILE_PATH = str(ROOT_DIR / "profiles" / "winfut_layout.json")

# Logs JSON rotativos por subsistema (captura, ocr, llm, risk, dashboard)
CHANNEL_LOG_DIR = str(ROOT_DIR / "logs" / "channels")

CAPTURE_INTERVAL_SECONDS = 30

OLLAMA_MODEL = "llava"
OLLAMA_HOST = "http://localhost:11434"

DB_PATH = str(ROOT_DIR / "data" / "copilot.db")
SNAPSHOTS_DIR = str(ROOT_DIR / "data" / "snapshots")
LOG_FILE = str(ROOT_DIR / "logs" / "copilot.log")

LOG_LEVEL = os.environ.get("COPILOT_LOG_LEVEL", "INFO")

# Janelas (hora início, min início, hora fim, min fim) consideradas alto risco operacional.
HIGH_RISK_HOURS = [
    (9, 0, 9, 15),
    (17, 45, 18, 15),
]

# Confiança mínima para o copiloto “sugerir” operação (nível textual)
MIN_CONFIDENCE_TO_SUGGEST = "MEDIA"

# Ativo padrão exibido no dashboard (WDOFUT, WINFUT, etc.)
DEFAULT_ASSET = "WINFUT"

# Quantidade de análises recentes a injetar no prompt
RECENT_ANALYSES_FOR_PROMPT = 5

# Se True, primeira execução sem região salva pode abrir o seletor interativo
USE_INTERACTIVE_REGION_ON_FIRST_RUN = True
REGION_SAVE_FILE = str(ROOT_DIR / "data" / "capture_region.json")

# Idiomas EasyOCR (pt + en cobre timestamps e números em interfaces BR)
OCR_LANGS = ["pt", "en"]

# Torch: CPU por padrão no MVP local (troque conforme sua GPU)
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
