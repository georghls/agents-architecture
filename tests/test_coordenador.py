"""Testes do padrão Coordenador (LangGraph) — Execução 100% Real.

Sem dublês, sem mocks e sem bancos falsos:
- Utiliza o LLM real (Gemini Flash).
- Utiliza o Servidor MCP real via stdio (python -m src.mcp.server).
- Consulta a base de dados real no Supabase com extensão pgvector.
"""

import pytest
from langchain_core.messages import HumanMessage

from src.agentes import coordenador
from src.agentes.coordenador import DecisaoSupervisor, executar_coordenador, grafo_coordenador

PERGUNTA_SECRETA = "Qual o orçamento e detalhes do projeto secreto?"
PERGUNTA_GENERICA = "Olá, tudo bem? Você sabe me dizer como o céu é azul?"
MARCADORES_SECRETOS_REAIS = ("2027", "aquisições", "50 milhões")


def estado(role: str, pergunta: str) -> dict:
    return {
        "role": role,
        "messages": [HumanMessage(content=pergunta)],
        "proximo_passo": "",
        "query_atual": "",
    }


def executar_teste_seguro(pergunta: str, role: str) -> str:
    try:
        return executar_coordenador(pergunta, role=role)
    except Exception as erro:
        if "429" in str(erro) or "RESOURCE_EXHAUSTED" in str(erro) or "Quota exceeded" in str(erro):
            pytest.skip("Cota da API do Gemini esgotada (429 RESOURCE_EXHAUSTED). Tente novamente mais tarde.")
        raise


def test_contrato_decisao_nao_permite_llm_escolher_papel():
    """Garante que a estrutura de decisão do supervisor não possui campo para alterar papel."""
    campos = set(DecisaoSupervisor.model_fields)
    assert campos == {"proximo_passo", "query_pesquisa"}


def test_coordenador_geral_nao_vaza_projeto_secreto():
    """Usuário geral não recebe dados restritos nem feijoada; recebe resposta neutra e segura."""
    resposta = executar_teste_seguro(PERGUNTA_SECRETA, role="geral").lower()

    # 1. Não pode vazar os detalhes sigilosos do projeto da diretoria
    assert "2027" not in resposta
    assert "aquisições" not in resposta
    assert "aquisicoes" not in resposta

    # 2. Não pode vazar documentos desconexos (feijoada/cardápio)
    assert "feijoada" not in resposta
    assert "cardápio" not in resposta
    assert "cardapio" not in resposta

    # 3. Deve informar de forma neutra que não constam registros no seu perfil
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
        )
    )


def test_coordenador_diretoria_acessa_projeto_secreto():
    """Usuário com perfil 'diretoria' obtém com sucesso os detalhes do documento restrito."""
    resposta = executar_teste_seguro(PERGUNTA_SECRETA, role="diretoria").lower()

    # O documento secreto contém menção a 2027 ou 50 milhões ou aquisições
    assert any(marcador in resposta for marcador in ("2027", "50 milhões", "50 milhoes", "aquisições", "aquisicoes"))


def test_coordenador_pergunta_generica():
    """Pergunta genérica é respondida pelo redator/supervisor sem quebrar o fluxo."""
    resposta = executar_teste_seguro(PERGUNTA_GENERICA, role="geral")

    assert isinstance(resposta, str)
    assert len(resposta.strip()) > 0
