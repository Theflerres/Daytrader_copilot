# Market Copilot (MVP + refinamento operacional)

Copiloto operacional de mercado **100% local** (captura multi-região, visão, OCR por pipeline, **composite** para o **Ollama + llava**, SQLite, métricas e painel **Rich** em três colunas).

**Este software não executa ordens** e não garante resultado financeiro.

## Setup dois monitores (1920×1080 + 2560×1080)

- **Monitor principal (1920×1080):** Profit, gráfico, tape, DOM — regiões calibradas com coordenadas **absolutas** no desktop virtual do Windows.
- **Monitor ultrawide (2560×1080):** abra o **terminal** (PowerShell, Windows Terminal ou Cursor) **maximizado** neste monitor para o dashboard Rich ocupar a largura útil. O Rich não controla fullscreen do SO; use maximizar janela.

O arquivo de perfil (`profiles/*.json`) define quais retângulos pertencem a cada região (`main_chart`, `volume`, `tape`, `book`, `clock`, `position_area`, …).

## Perfis de layout (`profiles/`)

Exemplos incluídos (ajuste coordenadas ao seu layout real ou use o wizard):

| Arquivo | Uso sugerido |
|---------|----------------|
| `profiles/winfut_layout.json` | WIN — gráfico + volume + tape + book |
| `profiles/wdofut_layout.json` | WDO — mesma ideia |
| `profiles/scalp_layout.json` | Janelas de pregão mais curtas + thresholds um pouco mais sensíveis |
| `profiles/replay_layout.json` | Uma região ampla (replay / gravação) |

`config.py`:

- `ACTIVE_PROFILE_PATH` — perfil carregado quando você **não** passa `--profile`.
- `CHANNEL_LOG_DIR` — logs JSONL rotativos por subsistema (`capture`, `ocr`, `llm`, `risk`, `dashboard`).

## Wizard de calibração

```bash
python calibrate.py --profile profiles/winfut_layout.json
```

1. Escolhe o monitor MSS (lista na janela).
2. Para cada região padrão, desenha retângulo na tela (Enter grava, Esc pula).
3. **Preview** assíncrono da captura enquanto arrasta.
4. Salva automaticamente o JSON do perfil.

## Execução com perfil

```bash
python main.py --profile profiles/scalp_layout.json --once
```

Sem `--profile`: usa `ACTIVE_PROFILE_PATH` se o arquivo existir; senão, cai no **modo legado** (`capture_region.json` ou `CAPTURE_REGION`).

## Snapshots hierárquicos (dataset)

Cada ciclo grava sob `data/snapshots/YYYY-MM-DD/HH/`:

- pastas por tipo (`chart`, `volume`, `tape`, `composite`, …) com `raw_<stamp>.png` e `edges_<stamp>.png` (pré-processamento);
- `meta_<stamp>.json` (regime, risco, OCR score, perfil);
- `analysis_<stamp>.txt` (texto bruto da análise).

## Métricas e feedback futuro

- Tabela `metric_events`: taxa de “não operar”, regime, hora, scores OCR, sucesso captura/LLM.
- Tabela `operator_feedback`: para evolução de **precisão supervisionada** (preenchimento manual futuro).

## Logs

- Texto: `logs/copilot.log`
- JSON rotativos: `logs/channels/*.jsonl` (um por canal).

---

## Requisitos

- Python **3.11+** (Windows, Linux ou macOS)
- [Ollama](https://ollama.com/download) instalado e em execução
- Modelo multimodal **`llava`** (ou variante configurada)

## Instalação do Ollama e do modelo `llava`

1. Instale o Ollama a partir do site oficial: [https://ollama.com/download](https://ollama.com/download).
2. Garanta que o serviço está ativo (por padrão em `http://localhost:11434`).
3. Baixe o modelo (exemplo com `llava`):

   ```bash
   ollama pull llava
   ```

   Modelos multimodais alternativos podem funcionar desde que aceitem mensagens `images`; ajuste `OLLAMA_MODEL` em `config.py` se necessário.

## Instalação do projeto

No diretório do repositório:

```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt
```

**Nota (PyTorch / EasyOCR):** a primeira instalação pode demorar. Em máquinas sem GPU CUDA, o PyTorch usará CPU — suficiente para o MVP em muitos casos.

## Configuração da região de captura

**Preferido:** perfis JSON + `python calibrate.py --profile ...` (multi-região, multi-monitor).

Modo legado (uma única região `main_chart`):

1. Ajuste `CAPTURE_REGION` em **`config.py`**, ou
2. Execute:

   ```bash
   python main.py --interactive-region --once --skip-llm
   ```

   As coordenadas são salvas em `data/capture_region.json`.

| Variável                     | Função                                                        |
|-----------------------------|----------------------------------------------------------------|
| `ACTIVE_PROFILE_PATH`       | Perfil JSON padrão (`profiles/winfut_layout.json`)            |
| `CHANNEL_LOG_DIR`           | Pasta dos logs JSONL por canal                                |
| `CAPTURE_REGION`             | Fallback estático MSS (modo legado)                           |
| `CAPTURE_INTERVAL_SECONDS`   | Intervalo entre snapshots no loop                              |
| `OLLAMA_MODEL`               | Por padrão `llava`                                             |
| `OLLAMA_HOST`                | Endpoint do Ollama                                             |
| `HIGH_RISK_HOURS`             | Janelas locais marcadas como risco alto (abertura/fechamento)   |
| `MIN_CONFIDENCE_TO_SUGGEST`  | Piso textual de confiança para cenários mais agressivos        |

Logs: `logs/copilot.log`. Banco: `data/copilot.db`. Imagens: `data/snapshots/`.

## Execução

Um único ciclo (bom para validar OCR e captura **sem** chamar LLM pesado):

```bash
python main.py --once --skip-llm
```

Ciclo completo com multimodal:

```bash
python main.py --once
```

Loop contínuo (dashboard redesenhado a cada intervalo configurado):

```bash
python main.py
```

Outras flags:

| Flag                     | Significado                                                 |
|-------------------------|-------------------------------------------------------------|
| `--profile`             | Caminho do JSON de perfil (regiões + OCR + composite)         |
| `--skip-llm`             | Pula chamada ao Ollama (útil pra testes) — também pode usar `set COPILOT_SKIP_LLM=1` (Windows cmd) |
| `--once`                | Um ciclo apenas                                              |
| `--interactive-region`  | Selecionar região e salvar JSON                              |
| `--region-file caminho.json` | Carregar JSON de região alternativo                    |

## Estrutura do código

```
capture/          # MSS, monitores, seleção de região
vision/           # OpenCV, OCR por pipeline, composite, snapshots hierárquicos
context/          # Risco, confiança, regime de mercado, contexto LLM
core/             # Perfis JSON + logging estruturado
llm/              # Ollama (llava), prompts, parse
memory/           # SQLite, métricas, feedback
interface/        # Dashboard Rich (3 colunas)
profiles/         # Layouts nomeados (winfut, wdofut, scalp, replay)
config.py | main.py | calibrate.py
```

## Responsabilidades e limites

- **Zero execução automática de ordens** neste projeto.
- OCR e visão são **aproximações imperfeitas** — use como apoio, não como verdade oficial do book.
- A IA multimodal pode alucinar; o parser tenta estruturar probabilidade/confiança/risco, mas a **validação final é sempre sua**.

Licença: defina conforme uso do seu repositório (não inclusa aqui por padrão).
