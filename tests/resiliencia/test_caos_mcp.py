"""Testes de resiliência a falhas de transporte e processo no MCP (Etapa 4.4).

Valida:
1. Queda ou inexistência do subprocesso stdio do servidor MCP vira 'Erro MCP' amigável.
2. Degradação graciosa dos agentes quando o servidor MCP está inalcançável.
"""

from unittest.mock import patch
import pytest
from pydantic import BaseModel

from mcp import StdioServerParameters
from src.agentes.mcp_toolkit import consultar_mcp
from src.agentes.coordenador import grafo_coordenador, EstadoCoordenador, _extrair_texto
from langchain_core.messages import HumanMessage, AIMessage


def test_falha_transporte_mcp_vira_erro_amigavel():
    # Aponta para um executável fictício inexistente
    alvo_ficticio = StdioServerParameters(
        command="executavel_fantasma_inexistente_12345",
        args=["-m", "src.mcp.server"],
    )

    resultado = consultar_mcp(
        query="qualquer pergunta",
        role="geral",
        alvo=alvo_ficticio,
    )

    assert "Erro MCP:" in resultado
    assert "não foi possível consultar o servidor" in resultado


def test_coordenador_com_mcp_indisponivel_degrada_graciosamente():
    """Verifica que o grafo Coordenador não explode com exceção não tratada quando o MCP falha."""

    class Decisao(BaseModel):
        proximo_passo: str = "pesquisador"
        query_pesquisa: str = "cardapio feijoada"

    class DubleLLM:
        def with_structured_output(self, schema):
            class DubleEstruturado:
                def invoke(self, mensagens):
                    return Decisao()
            return DubleEstruturado()

        def invoke(self, mensagens):
            conteudo = " ".join(str(getattr(m, "content", "")) for m in mensagens)
            if "Erro MCP" in conteudo:
                return AIMessage(content="Lamentamos, mas o serviço de documentos está temporariamente indisponível.")
            return AIMessage(content="Resposta normal.")

    with patch("src.agentes.coordenador.llm", DubleLLM()), \
         patch("src.agentes.mcp_toolkit.consultar_mcp", return_value="Erro MCP: não foi possível consultar o servidor de documentos."):

        estado_inicial: EstadoCoordenador = {
            "role": "geral",
            "messages": [HumanMessage(content="Qual o cardápio da feijoada?")],
            "proximo_passo": "",
            "query_atual": "",
        }

        # Não deve disparar exceção; deve concluir o grafo graciosamente
        resultado = grafo_coordenador.invoke(estado_inicial)
        texto_final = _extrair_texto(resultado["messages"][-1])

        assert "temporariamente indisponível" in texto_final
