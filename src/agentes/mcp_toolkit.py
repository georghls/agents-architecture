"""Ponte entre os agentes (LangChain/LangGraph) e o servidor MCP real.

Os agentes nunca falam com o banco: a ferramenta abaixo abre um cliente MCP,
inicia ``python -m src.mcp.server`` via stdio e chama
``buscar_documentos_corporativos``. Ver D-007 e D-008 em ``docs/decisions.md``.
"""

import asyncio
import os
import sys
from typing import Any

from autogen_core.tools import FunctionTool
from langchain_core.tools import BaseTool, tool
from mcp import Client, StdioServerParameters
from mcp.client.stdio import get_default_environment

from src.autorizacao.tokens import gerar_token_sessao
from src.config import RAIZ_PROJETO

# Contrato do servidor (D-007 / D-011). O LLM só informa `query`; o papel de acesso
# é autenticado via JWT de sessão (A-05) e a ferramenta MCP recebe apenas `pergunta`.
NOME_FERRAMENTA_MCP = "buscar_documentos_corporativos"
TIMEOUT_SEGUNDOS = 60.0

# Só estes segredos são repassados ao subprocesso, além do ambiente básico do SDK.
_VARIAVEIS_REPASSADAS = ("DATABASE_URL", "GEMINI_API_KEY", "AUTH_SECRET_KEY")


def parametros_servidor(role: str | None = None, token: str | None = None) -> StdioServerParameters:
    """Como iniciar o servidor MCP como subprocesso stdio com credencial JWT (A-05)."""
    env = get_default_environment()
    for nome in _VARIAVEIS_REPASSADAS:
        if os.environ.get(nome):
            env[nome] = os.environ[nome]

    if token:
        env["MCP_AUTH_TOKEN"] = token
    elif role:
        env["MCP_AUTH_TOKEN"] = gerar_token_sessao(papel=role)
    elif os.environ.get("MCP_AUTH_TOKEN"):
        env["MCP_AUTH_TOKEN"] = os.environ["MCP_AUTH_TOKEN"]

    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp.server"],
        cwd=str(RAIZ_PROJETO),
        env=env,
    )


def _texto_do_resultado(resultado) -> str:
    partes = [bloco.text for bloco in resultado.content if getattr(bloco, "type", None) == "text"]
    return "\n".join(partes).strip()


async def _chamar_mcp(alvo: Any, query: str) -> str:
    async with Client(alvo, read_timeout_seconds=TIMEOUT_SEGUNDOS) as cliente:
        resultado = await cliente.call_tool(
            NOME_FERRAMENTA_MCP,
            {"pergunta": query},
        )
    texto = _texto_do_resultado(resultado)
    if resultado.is_error:
        print(f"[Cliente MCP] Ferramenta retornou erro: {texto}", file=sys.stderr)
        return "Erro MCP: a ferramenta de busca falhou; nenhum documento foi retornado."
    return texto or "Erro MCP: resposta vazia do servidor."


async def consultar_mcp_async(query: str, role: str, alvo: Any = None) -> str:
    """
    Consulta o servidor MCP assincronamente e devolve o texto da ferramenta.
    Permite concorrência nativa para tarefas paralelas (D-001, D-012).
    """
    alvo = alvo if alvo is not None else parametros_servidor(role=role)
    try:
        return await _chamar_mcp(alvo, query)
    except Exception as erro:  # noqa: BLE001 - transporte/SDK podem lançar classes variadas
        print(f"[Cliente MCP] Falha ao consultar o servidor (async): {erro!r}", file=sys.stderr)
        return "Erro MCP: não foi possível consultar o servidor de documentos."


def consultar_mcp(query: str, role: str, alvo: Any = None) -> str:
    """
    Consulta o servidor MCP e devolve o texto da ferramenta.

    ``alvo`` permite injetar outro destino aceito por ``mcp.Client`` (ex.: a
    instância ``MCPServer`` em processo, nos testes). Por padrão, sobe o
    servidor real via stdio com token JWT autenticado para o ``role`` da sessão.
    Falhas viram texto ``Erro MCP: ...`` para o agente; o detalhe técnico vai para o stderr.
    """
    return asyncio.run(consultar_mcp_async(query, role, alvo=alvo))




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


def criar_ferramenta_autogen(role: str, alvo: Any = None) -> FunctionTool:
    """Cria a ferramenta assíncrona do AutoGen com o papel do usuário fixado (D-010, D-013).

    O papel da sessão é injetado diretamente na closure e associado ao token JWT
    no subprocesso MCP. O modelo/LLM do AutoGen recebe apenas o parâmetro `query`.
    """
    if not isinstance(role, str) or not role.strip():
        raise ValueError("role da sessão é obrigatório para criar a ferramenta AutoGen.")
    papel_da_sessao = role.strip()

    async def buscar_documentos_corporativos(query: str) -> str:
        """Busca documentos corporativos internos na base de dados da empresa.
        Use esta ferramenta SEMPRE que precisar responder a perguntas sobre
        projetos da empresa, orçamentos, regras internas ou documentos em geral.
        """
        print(f"\n[AutoGen MCP Tool] Pesquisando por '{query}' com permissão de '{papel_da_sessao}'...")
        resultado = await consultar_mcp_async(query, papel_da_sessao, alvo=alvo)
        print(f"[AutoGen MCP Tool] Retorno: {resultado[:100]}...\n")
        return resultado

    return FunctionTool(
        buscar_documentos_corporativos,
        description=(
            "Busca documentos corporativos internos na base de dados da empresa. "
            "Use esta ferramenta SEMPRE que precisar responder a perguntas sobre "
            "projetos, orçamentos, regras internas ou documentação corporativa."
        ),
    )

