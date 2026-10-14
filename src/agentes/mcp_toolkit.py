"""Ponte entre os agentes (LangChain/LangGraph) e o servidor MCP real.

Os agentes nunca falam com o banco: a ferramenta abaixo abre um cliente MCP,
inicia ``python -m src.mcp.server`` via stdio e chama
``buscar_documentos_corporativos``. Ver D-007 e D-008 em ``docs/decisions.md``.
"""

import asyncio
import os
import sys
from typing import Any

from langchain_core.tools import BaseTool, tool
from mcp import Client, StdioServerParameters
from mcp.client.stdio import get_default_environment

from src.config import RAIZ_PROJETO

# Contrato do servidor (D-007). O LLM só informa `query`; o `role` é fixado pelo
# código na criação da ferramenta (D-010) e traduzido aqui para o contrato MCP.
NOME_FERRAMENTA_MCP = "buscar_documentos_corporativos"
TIMEOUT_SEGUNDOS = 60.0

# Só estes segredos são repassados ao subprocesso, além do ambiente básico do SDK.
_VARIAVEIS_REPASSADAS = ("DATABASE_URL", "GEMINI_API_KEY")


def parametros_servidor() -> StdioServerParameters:
    """Como iniciar o servidor MCP como subprocesso stdio."""
    env = get_default_environment()
    for nome in _VARIAVEIS_REPASSADAS:
        if os.environ.get(nome):
            env[nome] = os.environ[nome]
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp.server"],
        cwd=str(RAIZ_PROJETO),
        env=env,
    )


def _texto_do_resultado(resultado) -> str:
    partes = [bloco.text for bloco in resultado.content if getattr(bloco, "type", None) == "text"]
    return "\n".join(partes).strip()


async def _chamar_mcp(alvo: Any, query: str, role: str) -> str:
    async with Client(alvo, read_timeout_seconds=TIMEOUT_SEGUNDOS) as cliente:
        resultado = await cliente.call_tool(
            NOME_FERRAMENTA_MCP,
            {"pergunta": query, "papel_do_usuario": role},
        )
    texto = _texto_do_resultado(resultado)
    if resultado.is_error:
        print(f"[Cliente MCP] Ferramenta retornou erro: {texto}", file=sys.stderr)
        return "Erro MCP: a ferramenta de busca falhou; nenhum documento foi retornado."
    return texto or "Erro MCP: resposta vazia do servidor."


def consultar_mcp(query: str, role: str, alvo: Any = None) -> str:
    """
    Consulta o servidor MCP e devolve o texto da ferramenta.

    ``alvo`` permite injetar outro destino aceito por ``mcp.Client`` (ex.: a
    instância ``MCPServer`` em processo, nos testes). Por padrão, sobe o
    servidor real via stdio. Falhas viram texto ``Erro MCP: ...`` para o
    agente; o detalhe técnico vai para o stderr.
    """
    alvo = alvo if alvo is not None else parametros_servidor()
    try:
        return asyncio.run(_chamar_mcp(alvo, query, role))
    except Exception as erro:  # noqa: BLE001 - transporte/SDK podem lançar classes variadas
        print(f"[Cliente MCP] Falha ao consultar o servidor: {erro!r}", file=sys.stderr)
        return "Erro MCP: não foi possível consultar o servidor de documentos."


def criar_ferramenta_busca(role: str) -> BaseTool:
    """
    Cria a ferramenta de busca com o papel do usuário já fixado (D-010).

    O ``role`` deve vir da sessão autenticada / estado do grafo, nunca do LLM.
    Ele fica preso na closure e não aparece no schema da ferramenta, então o
    modelo só consegue informar ``query``.
    """
    if not isinstance(role, str) or not role.strip():
        raise ValueError("role da sessão é obrigatório para criar a ferramenta de busca.")
    papel_da_sessao = role.strip()

    @tool("ferramenta_busca_corporativa")
    def ferramenta_busca_corporativa(query: str) -> str:
        """
        Busca documentos corporativos internos na base de dados da empresa.
        Use esta ferramenta SEMPRE que precisar responder a perguntas sobre
        projetos da empresa, orçamentos, regras internas ou documentos em geral.
        """
        print(f"\n[Ferramenta MCP] Pesquisando por '{query}' com permissão de '{papel_da_sessao}'...")
        resultado = consultar_mcp(query, papel_da_sessao)
        print(f"[Ferramenta MCP] Resultado retornado: {resultado}\n")
        return resultado

    return ferramenta_busca_corporativa


def criar_toolkit_corporativo(role: str) -> list[BaseTool]:
    """Lista de ferramentas entregue aos agentes, já presa ao papel da sessão."""
    return [criar_ferramenta_busca(role)]

