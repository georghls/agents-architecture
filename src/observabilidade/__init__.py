"""Módulo de Observabilidade, Telemetria e FinOps (LLMOps) para o projeto multiagente."""

from src.observabilidade.custos import calcular_custo_execucao, TABELA_PRECOS_GEMINI
from src.observabilidade.telemetria import (
    TraceContexto,
    SpanContexto,
    iniciar_rastreamento,
    obter_trace_atual,
    listar_execucoes,
    obter_resumo_estatistico,
    inicializar_banco,
    salvar_avaliacao,
    listar_avaliacoes,
    obter_metricas_qualidade,
)
from src.observabilidade.avaliador import (
    VereditoJuiz,
    ResultadoAvaliacao,
    avaliar_execucao,
    verificar_seguranca_rbac,
    criar_juiz_llm,
)

__all__ = [
    "TraceContexto",
    "SpanContexto",
    "iniciar_rastreamento",
    "obter_trace_atual",
    "listar_execucoes",
    "obter_resumo_estatistico",
    "inicializar_banco",
    "calcular_custo_execucao",
    "TABELA_PRECOS_GEMINI",
    "salvar_avaliacao",
    "listar_avaliacoes",
    "obter_metricas_qualidade",
    "VereditoJuiz",
    "ResultadoAvaliacao",
    "avaliar_execucao",
    "verificar_seguranca_rbac",
    "criar_juiz_llm",
]
