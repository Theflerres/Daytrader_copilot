<div align="center">
  <img src="https://media.giphy.com/media/12W5Sg2koWYnwA/giphy.gif" width="800" alt="Hacker Terminal">
</div>

<div align="center">

```
╔═══════════════════════════════════════════════════╗
║           📈  MARKET COPILOT  v1.0 MVP            ║
║     local · multimodal · zero cloud · real-time   ║
╚═══════════════════════════════════════════════════╝
```

**Assistente operacional de mercado 100% local**
Captura multi-região → OpenCV → EasyOCR → LLaVA → terminal

---

<!-- GIF DE DEMO: grave o dashboard rodando e coloque aqui -->
<!-- Exemplo: ![demo](https://raw.githubusercontent.com/SEU_USER/SEU_REPO/main/assets/demo.gif) -->
> 📽️ *[coloque aqui um GIF do dashboard em ação — ex: gravado com [ScreenToGif](https://www.screentogif.com/)]*

---

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-LLaVA-orange?style=for-the-badge&logo=ollama&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-metrics-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Rich](https://img.shields.io/badge/Rich-terminal_UI-22c55e?style=for-the-badge)
![Platform](https://img.shields.io/badge/Plataforma-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge)
![License](https://img.shields.io/badge/Licença-MIT-green?style=for-the-badge)

</div>

---

> ⚠️ **AVISO:** Este software **não executa ordens** e não oferece garantia de resultado financeiro. É uma ferramenta auxiliar de análise visual. Toda decisão de trade é de responsabilidade exclusiva do operador.

---

## `> whoami`

O **Market Copilot** captura regiões específicas da sua plataforma de trade, processa com OpenCV + EasyOCR, monta um *composite* e envia ao LLaVA via Ollama — gerando contexto de mercado em tempo real direto no terminal. **Zero dado sai da sua máquina.**

<div align="center">
  <img src="[https://media.giphy.com/media/y0XAoHQPmv4CQ/giphy.gif](https://media.giphy.com/media/y0XAoHQPmv4CQ/giphy.gif)" width="600" alt="Cyberpunk UI Vision">
</div>

```
[tela de trade] ──► [captura multi-região]
                           │
                    [OpenCV + EasyOCR]
                           │
                    [composite image]
                           │
                    [LLaVA via Ollama]  ◄── 100% local
                           │
                  [dashboard Rich 3 colunas]
```

**Stack:**

| Camada | Tecnologia |
| --- | --- |
| 🖼️ Captura | MSS (multi-monitor, coordenadas absolutas) |
| 👁️ Visão | OpenCV — pré-processamento + edge detection |
| 🔤 OCR | EasyOCR — pipeline por região |
| 🤖 IA | LLaVA via Ollama (local, sem GPU obrigatória) |
| 🗄️ Persistência | SQLite — métricas + feedback supervisionado |
| 🖥️ Interface | Rich — dashboard 3 colunas no terminal |

---

## `> ls features/`

- 🔒 **100% local** — sem APIs externas, sem latência de rede, sem exposição de dados
- 🗺️ **Captura multi-região** — perfis JSON mapeiam áreas da tela (Gráfico, Volume, Tape, Book, Relógio, Posição)
- 🧠 **IA multimodal** — LLaVA analisa o composite visual gerado das capturas
- 💾 **Snapshots hierárquicos** — datasets estruturados por data/hora para auditoria e fine-tuning
- 📊 **Dashboard avançado** — interface de terminal em 3 colunas com `Rich`
- 📈 **Métricas e feedback** — SQLite para regimes de mercado, scores OCR e assertividade

---

## `> cat requirements.txt`

- Python 3.11+
- [Ollama](https://ollama.com/download) rodando localmente (padrão: `http://localhost:11434`)
- Modelo multimodal `llava` (ou variante configurada em `OLLAMA_MODEL`)

---

## `> ./install.sh`

### 1 — Baixar o modelo de IA

```bash
ollama pull llava
```

> 💡 Modelos multimodais alternativos funcionam desde que aceitem mensagens com `images`. Ajuste `OLLAMA_MODEL` em `config.py` se necessário.

### 2 — Instalar o projeto

```bash
# Criar ambiente virtual
python -m venv .venv

# Ativar — Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Ativar — Linux / macOS
source .venv/bin/activate

# Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt
```

> ⏳ A primeira instalação pode demorar por conta do PyTorch/EasyOCR. Sem GPU CUDA, o sistema roda via CPU automaticamente — suficiente para o MVP na maioria dos casos.

---

## `> cat setup/monitors.md`

O sistema usa **coordenadas absolutas** no desktop virtual do Windows, projetado para setups multi-monitor.

<!-- IMAGEM: diagrama do layout dos monitores -->
<!-- Exemplo: ![monitor-layout](https://raw.githubusercontent.com/SEU_USER/SEU_REPO/main/assets/monitor_layout.png) -->
> 🖼️ *[opcional: adicione aqui uma imagem do layout dos dois monitores com as regiões marcadas]*

**Sugestão de layout (1920×1080 + 2560×1080):**

| Monitor | Uso sugerido |
| --- | --- |
| 🖥️ Principal (1920×1080) | Plataforma de trade com gráfico, tape e book nas regiões mapeadas |
| 🖥️ Ultrawide (2560×1080) | Terminal **maximizado** — dashboard `Rich` em largura total |

> ℹ️ O `Rich` não controla fullscreen do SO — maximize a janela do terminal manualmente.

---

## `> ls profiles/`

O arquivo de perfil define os retângulos de cada região: `main_chart`, `volume`, `tape`, `book`, `clock`, `position_area`, …

| 📄 Arquivo | 🎯 Uso sugerido |
| --- | --- |
| `profiles/winfut_layout.json` | Índice (WIN) — Gráfico + Volume + Tape + Book |
| `profiles/wdofut_layout.json` | Dólar (WDO) — mesma estrutura |
| `profiles/scalp_layout.json` | Janelas curtas de pregão, thresholds mais sensíveis |
| `profiles/replay_layout.json` | Região ampla para tela de replay/gravação |

---

## `> ./calibrate.sh`

Use o wizard interativo para mapear as regiões ao seu layout real:

```bash
python calibrate.py --profile profiles/winfut_layout.json
```

```
[1] Lista monitores MSS disponíveis
[2] Desenha retângulo por região  ← Enter salva · Esc pula
[3] Preview assíncrono em tempo real enquanto arrasta
[4] Salva coordenadas automaticamente no JSON do perfil
```

<!-- GIF CALIBRAÇÃO: opcional, mostra o wizard funcionando -->
<!-- Exemplo: ![calibrate](https://raw.githubusercontent.com/SEU_USER/SEU_REPO/main/assets/calibrate.gif) -->
> 📽️ *[opcional: GIF do wizard de calibração em ação]*

---

## `> ./run.sh`

<div align="center">
  <img src="https://media1.tenor.com/m/tC6iAZEHDr0AAAAd/stalker2.gif" width="450" alt="Market Action">
</div>
<br>

```bash
# 🔁 Loop contínuo — dashboard atualizado a cada intervalo configurado
python main.py --profile profiles/winfut_layout.json

# 🧪 Um ciclo completo (Snapshot + OCR + LLM) — ideal para testes
python main.py --profile profiles/winfut_layout.json --once

# ⚡ Um ciclo só com captura e OCR, sem carregar a IA
python main.py --once --skip-llm
```

> 💡 Se `--profile` não for passado, carrega `ACTIVE_PROFILE_PATH` do `config.py`. Se não existir, entra no **modo legado** (`capture_region.json` ou `CAPTURE_REGION`).

**Todas as flags:**

| Flag | Descrição |
| --- | --- |
| `--profile <caminho>` | Perfil JSON de regiões, OCR e composite |
| `--once` | Executa apenas 1 ciclo |
| `--skip-llm` | Pula a chamada ao Ollama (também via `set COPILOT_SKIP_LLM=1` no Windows cmd) |
| `--interactive-region` | Seleção interativa de uma única região — salva JSON (modo legado) |
| `--region-file <caminho>` | Carrega um JSON de região alternativo |

---

## `> cat config.py`

| ⚙️ Variável | 📋 Descrição |
| --- | --- |
| `ACTIVE_PROFILE_PATH` | Perfil padrão quando `--profile` não é passado |
| `CAPTURE_INTERVAL_SECONDS` | Tempo entre ciclos no loop contínuo |
| `OLLAMA_MODEL` | Modelo multimodal (padrão: `llava`) |
| `OLLAMA_HOST` | Endpoint do Ollama |
| `HIGH_RISK_HOURS` | Janelas de alto risco (abertura, payroll, etc.) |
| `MIN_CONFIDENCE_TO_SUGGEST` | Limiar mínimo de confiança para gerar alertas |
| `CHANNEL_LOG_DIR` | Diretório dos logs JSONL por canal |
| `CAPTURE_REGION` | Fallback estático MSS (modo legado, uma única região) |

---

## `> ls data/ logs/`

**📸 Snapshots** — `data/snapshots/YYYY-MM-DD/HH/<região>/`

| Arquivo | Conteúdo |
| --- | --- |
| `raw_<stamp>.png` | Captura bruta da região |
| `edges_<stamp>.png` | Imagem pré-processada (OpenCV) |
| `meta_<stamp>.json` | Regime, risco, score OCR, perfil usado |
| `analysis_<stamp>.txt` | Texto bruto da análise do LLM |

**📝 Logs**

| Arquivo | Conteúdo |
| --- | --- |
| `logs/copilot.log` | Log geral em texto |
| `logs/channels/*.jsonl` | Logs rotativos por canal: `capture` `ocr` `llm` `risk` `dashboard` |

**🗄️ Banco de dados** — `data/copilot.db`

| Tabela | Conteúdo |
| --- | --- |
| `metric_events` | Taxa "não operar", regime, scores OCR, sucesso captura/LLM |
| `operator_feedback` | Precisão supervisionada (preenchimento manual futuro) |

---

## `> tree .`

```
market-copilot/
├── 📁 capture/        # Captura de tela (MSS), gerenciamento de monitores
├── 📁 context/        # Regras de risco, confiança e contexto para o prompt
├── 📁 core/           # Perfis JSON, constantes e logging estruturado
├── 📁 interface/      # Dashboard terminal em 3 colunas (Rich)
├── 📁 llm/            # Integração Ollama, prompts e parse de respostas
├── 📁 memory/         # SQLite, métricas e feedback do operador
├── 📁 vision/         # Pré-processamento OpenCV, pipeline OCR e composite
├── 📁 profiles/       # Layouts de tela prontos (JSON)
├── 📁 data/           # [gerado] Snapshots, banco .db
├── 📁 logs/           # [gerado] Logs em texto e canais JSONL
├── ⚙️  config.py
├── 🚀 main.py
└── 🎯 calibrate.py
```

---

## `> cat limitations.md`

| ⚠️ Limitação | Detalhe |
| --- | --- |
| 🔤 **OCR imperfeito** | Leitura de números no tape/book sujeita a falhas em oscilações rápidas |
| 🤖 **Alucinação da IA** | LLaVA pode gerar contextos incorretos — o parser estrutura com níveis de confiança, mas a validação final é sempre sua |
| 💻 **Custo de CPU/RAM** | Captura + OCR + LLM simultâneos são pesados — aumente `CAPTURE_INTERVAL_SECONDS` se o sistema ficar lento |

---

## `> cat LICENSE`

MIT — veja `LICENSE` para detalhes.

---

<div align="center">

*built for the terminal · runs offline · zero trust cloud*

</div>