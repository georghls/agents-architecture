"""Testes do padrão Plano-Executor (LangGraph) — Execução 100% Real.

Sem dublês, sem mocks e sem bancos falsos:
- Utiliza o LLM real (Gemini Flash).
- Utiliza o Servidor MCP real via stdio (python -m src.mcp.server).
- Consulta a base de dados real no Supabase com extensão pgvector.
- Valida o paralelismo via LangGraph Send API (D-001, D-012).
"""

import pytest
from langgraph.types import Send

from src.agentes.plano_executor import (
    PlanoDeAcao,
    Subtarefa,
    distribuir_tarefas,
    executar_plano_executor,
    grafo_plano_executor,
)

PERGUNTA_SECRETA = "Qual o orçamento e detalhes do projeto secreto da empresa?"
PERGUNTA_SIMPLES = "Qual é o cardápio do almoço e da feijoada na empresa?"
PERGUNTA_GENERICA = "Olá, tudo bem? Você sabe me dizer como o céu é azul?"


def executar_teste_seguro(pergunta: str, role: str) -> str:
    try:
        return executar_plano_executor(pergunta, role=role)
    except Exception as erro:
        if "429" in str(erro) or "RESOURCE_EXHAUSTED" in str(erro) or "Quota exceeded" in str(erro):
            pytest.skip("Cota da API do Gemini esgotada (429 RESOURCE_EXHAUSTED). Tente novamente mais tarde.")
        raise


def test_contrato_plano_nao_permite_llm_escolher_papel():
    """Garante que a estrutura de tarefas e plano não possui campo para alterar papel (D-010)."""
    campos_subtarefa = set(Subtarefa.model_fields)
    assert campos_subtarefa == {"id", "descricao", "query_busca"}
    assert "role" not in campos_subtarefa
    assert "papel" not in campos_subtarefa

    campos_plano = set(PlanoDeAcao.model_fields)
    assert campos_plano == {"tarefas"}
    assert "role" not in campos_plano
    assert "papel" not in campos_plano


def test_contrato_limites_de_tarefas():
    """Valida que o plano aceita entre 1 e 3 tarefas (D-012)."""
    # 1 tarefa válida
    p1 = PlanoDeAcao(
        tarefas=[Subtarefa(id=1, descricao="Buscar dados", query_busca="projeto")]
    )
    assert len(p1.tarefas) == 1

    # 3 tarefas válidas
    p3 = PlanoDeAcao(
        tarefas=[
            Subtarefa(id=1, descricao="T1", query_busca="q1"),
            Subtarefa(id=2, descricao="T2", query_busca="q2"),
            Subtarefa(id=3, descricao="T3", query_busca="q3"),
        ]
    )
    assert len(p3.tarefas) == 3

    # 0 tarefas inválidas
    with pytest.raises(Exception):
        PlanoDeAcao(tarefas=[])

    # Mais de 3 tarefas inválidas
    with pytest.raises(Exception):
        PlanoDeAcao(
            tarefas=[
                Subtarefa(id=1, descricao="T1", query_busca="q1"),
                Subtarefa(id=2, descricao="T2", query_busca="q2"),
                Subtarefa(id=3, descricao="T3", query_busca="q3"),
                Subtarefa(id=4, descricao="T4", query_busca="q4"),
            ]
        )


def test_distribuir_tarefas_injeta_role_seguro_no_send():
    """Garante que a distribuição Fan-Out via Send injeta o papel seguro do estado."""
    estado_mock = {
        "role": "diretoria",
        "pergunta": "Qualquer pergunta",
        "plano": [
            {"id": 1, "descricao": "Investigar orçamento", "query_busca": "orçamento secreto"},
            {"id": 2, "descricao": "Investigar cronograma", "query_busca": "datas 2027"},
        ],
        "resultados": [],
        "resposta_final": "",
    }

    envios = distribuir_tarefas(estado_mock)
    assert len(envios) == 2
    for envio in envios:
        assert isinstance(envio, Send)
        assert envio.node == "executor"
        assert envio.arg["role"] == "diretoria"
        assert envio.arg["id_tarefa"] in (1, 2)


def test_plano_executor_geral_nao_vaza_projeto_secreto():
    """Usuário com perfil 'geral' não recebe dados restritos do projeto secreto."""
    resposta = executar_teste_seguro(PERGUNTA_SECRETA, role="geral").lower()

    # 1. Não pode vazar os dados sigilosos do documento da diretoria
    assert "2027" not in resposta
    assert "aquisições" not in resposta
    assert "aquisicoes" not in resposta
    assert "50 milhões" not in resposta
    assert "50 milhoes" not in resposta

    # 2. Não pode vazar documentos desconexos (feijoada/cardápio)
    assert "feijoada" not in resposta
    assert "cardápio" not in resposta
    assert "cardapio" not in resposta

    # 3. Deve informar de forma formal que não constam registros autorizados
    assert any(
        termo in resposta
        for termo in (
            "não constam",
            "nao constam",
            "não foram encontrad",
            "nao foram encontrad",
            "nenhum documento",
            "disponíveis",
            "disponiveis",
            "registros",
            "perfil",
        )
    )


def test_plano_executor_diretoria_acessa_projeto_secreto():
    """Usuário com perfil 'diretoria' obtém com sucesso os detalhes do documento restrito."""
    resposta = executar_teste_seguro(PERGUNTA_SECRETA, role="diretoria").lower()

    # O documento secreto contém menção a 2027 ou 50 milhões ou aquisições
    assert any(
        marcador in resposta
        for marcador in ("2027", "50 milhões", "50 milhoes", "aquisições", "aquisicoes")
    )


def test_plano_executor_pergunta_simples_acessa_documento_geral():
    """Usuário geral consegue consultar documento público (feijoada/almoço)."""
    resposta = executar_teste_seguro(PERGUNTA_SIMPLES, role="geral").lower()

    assert any(termo in resposta for termo in ("feijoada", "almoço", "almoco", "cardápio", "cardapio", "sexta"))
