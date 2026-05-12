"""Montagem de prompts especializados para o copiloto multimodal (llava)."""
from __future__ import annotations

import json
from typing import Any


def build_multimodal_messages(
    image_b64: str,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Retorna uma única mensagem user no formato esperado pelo cliente Ollama,
    com imagem + instruções alinhadas à filosofia de filtragem antes de sugerir.
    """
    system_block = context.get("risk_evaluation", {})
    pre = context.get("pre_analysis", {})

    hist = context.get("historical_analyses") or []
    reacts = context.get("similar_reactions") or []
    hist_txt = json.dumps(hist, ensure_ascii=False, indent=2) if hist else "[]"
    react_txt = json.dumps(reacts, ensure_ascii=False, indent=2) if reacts else "[]"

    text = f"""Você é um copiloto operacional de mercado experiente — NÃO um robô de execução.
Objetivos: reduzir viés emocional, aumentar percepção contextual e FILTRAR operações ruins antes que aconteçam.
O operador decide tudo; você NUNCA sugere execução automática.

Prioridade absoluta:
- Se o contexto operacional for ruim ou inconsistente, diga explicitamente "não operar" ou "mercado inconsistente".
- Alta probabilidade NÃO significa alta confiança quando o mercado está caótico ou contraditório.

Ativo: {context.get('asset')}
Horário local (referência da máquina): {context.get('timestamp_local')}

Pré-análise heurística LOCAL (qualidade de dados — pode divergir do gráfico; use também a imagem):
{json.dumps(pre, ensure_ascii=False, indent=2)}

Checklist de risco LOCAL:
{json.dumps(system_block, ensure_ascii=False, indent=2)}

Visão (métricas numéricas básicas, não são preços oficiais):
{json.dumps(context.get('vision'), ensure_ascii=False, indent=2)}

Regime de mercado (heurística local sobre a imagem — não é verdade absoluta):
{json.dumps(context.get('market_regime') or {}, ensure_ascii=False, indent=2)}

Perfil de layout ativo: {context.get('profile_name') or 'default'}

Texto OCR (imperfeito — não trate como dado oficial da corretora):
{json.dumps(context.get('ocr'), ensure_ascii=False, indent=2)}

Últimas análises persistidas no banco (contexto apenas):
{hist_txt}

Reações/contextos semelhantes no banco (se houver):
{react_txt}

Tarefas obrigatórias:
1) Este contexto (imagem + notas) parece adequado para operar com responsabilidade? Se não, recomende NÃO OPERAR sem rodeios.
2) Tendência aparente e qualidade estrutural — ajuste o tom ao REGIME DE MERCADO indicado acima (ex.: errático = mais conservador).
3) Inconsistências entre preço/estrutura e volume (inferido apenas visualmente quando visível na imagem).
4) Alertas específicos: horário desfavorável, possível armadilha institucional, espera por confirmação de volume, risco macro (se aplicável aos dados dados).

Ao final, você DEVE emitir estas quatro linhas em formato estrito (copie literalmente os rótulos):
Probabilidade de continuação: <número>%
Confiança da análise: <ALTA|MEDIA|BAIXA|INVALIDA>
Risco contextual: <BAIXO|MEDIO|ALTO>
Recomendação: <uma linha sobre não operar, aguardar, ou cenário probabilístico>

Depois dessas linhas, escreva a justificativa em prosa direta."""

    # Lista de imagens preenchida em ollama_client com o PNG atual (mantém formato do prompt original).
    return [{"role": "user", "content": text, "images": ([image_b64] if image_b64 else [])}]


def build_fallback_text_prompt(context: dict[str, Any]) -> str:
    """Sem imagem — útil apenas em teste/fora do multimodal."""
    msgs = build_multimodal_messages("", context)
    return msgs[0]["content"]
