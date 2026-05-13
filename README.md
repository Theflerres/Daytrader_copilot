<div align="center">

# 📈 Market Copilot (MVP)

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![Ollama](https://img.shields.io/badge/AI-Ollama%20%2B%20LLaVA-orange)
![License](https://img.shields.io/badge/license-MIT-green)

O **Market Copilot** é um assistente operacional de mercado **100% local**. Ele utiliza captura de tela multi-região, visão computacional (OpenCV), OCR (EasyOCR) processado em pipeline e Inteligência Artificial Multimodal para fornecer um contexto em tempo real do mercado, exibido em um dashboard dinâmico no terminal.

</div>

---

> [!WARNING]
> **AVISO IMPORTANTE:** **Este software não executa ordens** e não garante qualquer tipo de resultado financeiro. Ele é estritamente uma ferramenta de análise visual auxiliar. Toda decisão de trade é de responsabilidade exclusiva do operador.

## ✨ Principais Funcionalidades

- **Processamento 100% Local:** Sem chamadas a APIs na nuvem, garantindo privacidade e zero latência de rede externa.
- **Captura Multi-Região:** Suporte a perfis em JSON para mapear áreas específicas da plataforma de trade (Gráfico, Volume, Tape, Book, Relógio).
- **IA Multimodal (LLaVA):** Combina (*composite*) as capturas de tela e analisa visualmente o contexto do mercado.
- **Snapshots Hierárquicos:** Gravação de datasets estruturados por data/hora (`raw`, `edges`, `meta.json`, `analysis.txt`) para auditoria e fine-tuning futuro.
- **Dashboard Avançado:** Interface de terminal rica construída com a biblioteca `Rich`, oferecendo logs, painel de contexto e análise do LLM simultaneamente.
- **Métricas e Feedback:** Banco SQLite embutido (`metric_events` e `operator_feedback`) para registrar regimes de mercado, precisão do OCR e assertividade das sugestões.

---

## 🖥️ Layout e Perfis de Tela

O sistema foi desenhado pensando em setups de múltiplos monitores, operando com coordenadas absolutas no desktop virtual do Windows. 

> [!TIP]
> **Sugestão de Setup (Base: 1920×1080 + 2560×1080):**
> - **Monitor Principal:** Plataforma de trade (Profit, etc.) com gráfico, tape e book nas regiões mapeadas.
> - **Monitor Secundário:** Terminal (PowerShell/Cursor) maximizado para renderizar o dashboard `Rich` em toda a sua extensão.

### Perfis Inclusos (`profiles/`)

| Arquivo JSON | Sugestão de Uso |
| :--- | :--- |
| `winfut_layout.json` | **Índice (WIN)** — Gráfico + Volume + Tape + Book |
| `wdofut_layout.json` | **Dólar (WDO)** — Gráfico + Volume + Tape + Book |
| `scalp_layout.json` | Janelas de pregão mais curtas, *thresholds* sensíveis |
| `replay_layout.json` | Região ampla focada em tela de replay/gravação |

---

## ⚙️ Pré-requisitos e Instalação

Certifique-se de ter o **Python 3.11+** instalado em sua máquina.

### 1. Preparando a Inteligência Artificial (Ollama)

Certifique-se de que o serviço do [Ollama](https://ollama.com/download) está rodando (geralmente em `http://localhost:11434`) e baixe o modelo multimodal:

```bash
ollama pull llava
(Nota: Outros modelos multimodais podem ser usados configurando a variável OLLAMA_MODEL no config.py)2. Instalando o ProjetoAbra seu terminal no diretório do projeto e execute:Bash# Criando ambiente virtual
python -m venv .venv

# Ativando o ambiente virtual:
# No Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# No Linux/macOS:
source .venv/bin/activate

# Instalando dependências
pip install --upgrade pip
pip install -r requirements.txt
[!NOTE]A primeira instalação pode demorar devido ao PyTorch/EasyOCR. Se não houver GPU CUDA disponível, o sistema rodará via CPU de forma automática, o que atende bem à maioria dos casos do MVP.🎯 Calibração e Execução1. Calibrando a Região de Captura (Recomendado)Use o Wizard interativo para mapear exatamente onde estão os elementos na sua tela.Bashpython calibrate.py --profile profiles/winfut_layout.json
O script listará os monitores.Desenhe retângulos na tela para cada região exigida (Enter salva, Esc pula).O JSON será atualizado automaticamente com as novas coordenadas.2. Rodando o CopilotO comando abaixo inicia o loop contínuo (modo principal), atualizando o dashboard periodicamente de acordo com o intervalo configurado.Bashpython main.py --profile profiles/winfut_layout.json
Comandos Úteis de Execução:ComandoDescriçãopython main.py --onceExecuta apenas 1 ciclo (Snapshot + OCR + LLM). Ótimo para testes.python main.py --once --skip-llmExecuta 1 ciclo apenas para testar captura e OCR, sem pesar a máquina com IA.python main.py --interactive-regionModo legado de calibração para uma única região (main_chart).Se você não passar a flag --profile, o sistema tentará carregar o ACTIVE_PROFILE_PATH definido em config.py. Se não encontrar, cairá no modo legado.🛠️ Configurações Principais (config.py)Ajuste o comportamento do bot diretamente no arquivo config.py:ACTIVE_PROFILE_PATH: Perfil padrão a ser carregado.CAPTURE_INTERVAL_SECONDS: Tempo de pausa entre cada ciclo de análise.HIGH_RISK_HOURS: Janelas de horário marcadas como de alto risco (ex: abertura de mercado, pay-roll).MIN_CONFIDENCE_TO_SUGGEST: Limiar mínimo de confiança do LLM para gerar alertas direcionados.CHANNEL_LOG_DIR: Diretório dos logs JSONL (capture, ocr, llm, risk, dashboard).📂 Estrutura de DiretóriosPlaintext├── capture/       # Módulo MSS, gerenciamento de monitores e seleção
├── context/       # Regras de risco, confiança, e contexto para o prompt do LLM
├── core/          # Perfis JSON, constantes e sistema de logging estruturado
├── interface/     # UI de terminal em 3 colunas (biblioteca Rich)
├── llm/           # Integração com Ollama, prompts e parse de respostas
├── memory/        # Banco de dados SQLite, sistema de métricas e feedback
├── vision/        # Pré-processamento OpenCV, OCR pipeline e composite de imagens
├── profiles/      # Arquivos JSON com layouts de tela prontos
├── data/          # (Gerado) Snapshots, arquivos brutos e banco .db
├── logs/          # (Gerado) Logs em texto e pastas de canais JSONL
├── config.py      # Configurações globais
├── main.py        # Ponto de entrada do sistema
└── calibrate.py   # Wizard de calibração de regiões
⚖️ Limitações do SistemaOCR e Visão são aproximações: A leitura de números no tape/book via OCR está sujeita a falhas, especialmente com rápidas oscilações.Alucinação da IA: Modelos locais como o LLaVA podem alucinar (ver padrões que não existem). O parser tenta estruturar os dados com níveis de confiança, mas a validação final e interpretação do contexto humano são insubstituíveis.Peso de Processamento: Rodar capturas contínuas, OCR e LLMs simultaneamente exige recursos significativos da máquina (CPU/RAM/VRAM). Ajuste o CAPTURE_INTERVAL_SECONDS se o PC apresentar lentidão.