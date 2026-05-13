<div align="center">

# 📈 Market Copilot

**Assistente operacional de mercado 100% local — captura multi-região, visão computacional, OCR por pipeline e IA multimodal no terminal**

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/IA-Ollama%20%2B%20LLaVA-orange?style=flat-square)
![Platform](https://img.shields.io/badge/Plataforma-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=flat-square)
![License](https://img.shields.io/badge/Licença-MIT-green?style=flat-square)

</div>

---

> ⚠️ **AVISO:** Este software **não executa ordens** e não oferece garantia de resultado financeiro. É uma ferramenta auxiliar de análise visual. Toda decisão de trade é de responsabilidade exclusiva do operador.

---

## O que é?

O **Market Copilot** captura regiões específicas da sua plataforma de trade, processa as imagens com OpenCV e EasyOCR, combina tudo em um *composite* e envia para o modelo LLaVA via Ollama — gerando contexto de mercado em tempo real exibido em um dashboard de terminal. Nenhum dado sai da sua máquina.

**Funcionalidades principais:**

- **100% local** — sem APIs externas, sem latência de rede, sem exposição de dados
- **Captura multi-região** — perfis JSON mapeiam áreas específicas da tela (Gráfico, Volume, Tape, Book, Relógio, Posição)
- **IA multimodal** — LLaVA analisa visualmente o composite gerado a partir das capturas
- **Snapshots hierárquicos** — salva datasets estruturados por data/hora para auditoria e fine-tuning futuro
- **Dashboard avançado** — interface de terminal em 3 colunas com a biblioteca `Rich`
- **Métricas e feedback** — banco SQLite embutido para registrar regimes de mercado, precisão do OCR e assertividade das sugestões

---

## Pré-requisitos

- Python 3.11+
- [Ollama](https://ollama.com/download) instalado e em execução (padrão: `http://localhost:11434`)
- Modelo multimodal `llava` (ou variante configurada em `OLLAMA_MODEL`)

---

## Instalação

### 1. Baixar o modelo de IA

```bash
ollama pull llava
```

> Modelos multimodais alternativos funcionam desde que aceitem mensagens com `images`. Ajuste `OLLAMA_MODEL` em `config.py` se necessário.

### 2. Instalar o projeto

```bash
# Criar e ativar ambiente virtual
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

# Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt
```

> A primeira instalação pode demorar por conta do PyTorch/EasyOCR. Em máquinas sem GPU CUDA o sistema roda via CPU automaticamente — suficiente para o MVP na maioria dos casos.

---

## Setup de tela

O sistema usa coordenadas absolutas no desktop virtual do Windows, projetado para setups multi-monitor.

**Sugestão de layout (1920×1080 + 2560×1080):**

| Monitor | Uso sugerido |
| --- | --- |
| Principal (1920×1080) | Plataforma de trade (Profit, etc.) com gráfico, tape e book nas regiões mapeadas |
| Ultrawide (2560×1080) | Terminal **maximizado** para o dashboard `Rich` ocupar a largura total |

> O `Rich` não controla o fullscreen do sistema operacional — use a opção maximizar janela do terminal.

---

## Perfis de layout (`profiles/`)

O arquivo de perfil define os retângulos de cada região (`main_chart`, `volume`, `tape`, `book`, `clock`, `position_area`, …).

| Arquivo | Uso sugerido |
| --- | --- |
| `profiles/winfut_layout.json` | Índice (WIN) — Gráfico + Volume + Tape + Book |
| `profiles/wdofut_layout.json` | Dólar (WDO) — mesma estrutura |
| `profiles/scalp_layout.json` | Janelas curtas de pregão, thresholds mais sensíveis |
| `profiles/replay_layout.json` | Região ampla para tela de replay/gravação |

---

## Calibração

Use o wizard interativo para mapear as regiões ao seu layout real:

```bash
python calibrate.py --profile profiles/winfut_layout.json
```

1. Escolhe o monitor MSS (listado na janela)
2. Para cada região, desenha um retângulo na tela (`Enter` salva, `Esc` pula)
3. Preview assíncrono da captura enquanto arrasta
4. Salva automaticamente as coordenadas no JSON do perfil

---

## Execução

```bash
# Loop contínuo — dashboard atualizado a cada intervalo configurado
python main.py --profile profiles/winfut_layout.json

# Um ciclo completo (Snapshot + OCR + LLM) — ideal para testes
python main.py --profile profiles/winfut_layout.json --once

# Um ciclo só com captura e OCR, sem carregar a IA
python main.py --once --skip-llm
```

> Se `--profile` não for passado, o sistema carrega `ACTIVE_PROFILE_PATH` do `config.py`. Se o arquivo não existir, entra no **modo legado** (`capture_region.json` ou `CAPTURE_REGION`).

**Todas as flags disponíveis:**

| Flag | Descrição |
| --- | --- |
| `--profile <caminho>` | Perfil JSON de regiões, OCR e composite |
| `--once` | Executa apenas 1 ciclo |
| `--skip-llm` | Pula a chamada ao Ollama (também via `COPILOT_SKIP_LLM=1` no Windows cmd) |
| `--interactive-region` | Seleção interativa de uma única região e salva JSON (modo legado) |
| `--region-file <caminho>` | Carrega um JSON de região alternativo |

---

## Configuração (`config.py`)

| Variável | Descrição |
| --- | --- |
| `ACTIVE_PROFILE_PATH` | Perfil padrão carregado quando `--profile` não é passado |
| `CAPTURE_INTERVAL_SECONDS` | Tempo entre cada ciclo de análise no loop contínuo |
| `OLLAMA_MODEL` | Modelo multimodal a usar (padrão: `llava`) |
| `OLLAMA_HOST` | Endpoint do Ollama |
| `HIGH_RISK_HOURS` | Janelas de horário marcadas como alto risco (ex: abertura, payroll) |
| `MIN_CONFIDENCE_TO_SUGGEST` | Limiar mínimo de confiança do LLM para gerar alertas |
| `CHANNEL_LOG_DIR` | Diretório dos logs JSONL por canal |
| `CAPTURE_REGION` | Fallback estático MSS (modo legado, uma única região) |

---

## Snapshots e logs

**Snapshots** — gravados em `data/snapshots/YYYY-MM-DD/HH/`, organizados por tipo de região:

- `raw_<stamp>.png` e `edges_<stamp>.png` — imagem bruta e pré-processada
- `meta_<stamp>.json` — regime, risco, score OCR, perfil usado
- `analysis_<stamp>.txt` — texto bruto da análise do LLM

**Logs:**

- `logs/copilot.log` — log geral em texto
- `logs/channels/*.jsonl` — logs JSON rotativos por canal (`capture`, `ocr`, `llm`, `risk`, `dashboard`)

**Banco de dados** (`data/copilot.db`):

- `metric_events` — taxa de "não operar", regime, scores OCR, sucesso de captura/LLM
- `operator_feedback` — para evolução de precisão supervisionada (preenchimento manual futuro)

---

## Estrutura do projeto

```
├── capture/        # Captura de tela (MSS), gerenciamento de monitores
├── context/        # Regras de risco, confiança e contexto para o prompt
├── core/           # Perfis JSON, constantes e logging estruturado
├── interface/      # Dashboard terminal em 3 colunas (Rich)
├── llm/            # Integração Ollama, prompts e parse de respostas
├── memory/         # SQLite, métricas e feedback do operador
├── vision/         # Pré-processamento OpenCV, pipeline OCR e composite
├── profiles/       # Layouts de tela prontos (JSON)
├── data/           # [gerado] Snapshots, banco .db
├── logs/           # [gerado] Logs em texto e canais JSONL
├── config.py       # Configurações globais
├── main.py         # Ponto de entrada
└── calibrate.py    # Wizard de calibração
```

---

## Limitações

**OCR e visão são aproximações** — a leitura de números no tape/book está sujeita a falhas, especialmente com oscilações rápidas.

**Alucinação da IA** — modelos locais como o LLaVA podem gerar contextos incorretos. O parser estrutura as respostas com níveis de confiança, mas a validação final é sempre do operador.

**Custo de processamento** — captura contínua + OCR + LLM exige CPU/RAM/VRAM consideráveis. Aumente `CAPTURE_INTERVAL_SECONDS` se o sistema ficar lento.

---

## Licença

MIT