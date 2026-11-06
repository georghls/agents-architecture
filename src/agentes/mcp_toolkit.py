"""Ponte entre os agentes (LangChain/LangGraph) e o servidor MCP real.

Os agentes nunca falam com o banco: a ferramenta abaixo abre um cliente MCP,
inicia ``python -m src.mcp.server`` via stdio e chama
``buscar_documentos_corporativos``. Ver D-007 e D-008 em ``docs/decisions.md``.
"""

import asyncio
from contextlib import contextmanager
import os
import sys
import threading
from typing import Any

from autogen_core.tools import FunctionTool
from langchain_core.tools import BaseTool, tool
from mcp import Client, StdioServerParameters
from mcp.client.stdio import get_default_environment

from src.autorizacao.tokens import gerar_token_sessao
from src.config import RAIZ_PROJETO
from src.observabilidade.telemetria import obter_trace_atual

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


async def _executar_call_tool_no_cliente(cliente: Client, query: str) -> str:
    resultado = await cliente.call_tool(
        NOME_FERRAMENTA_MCP,
        {"pergunta": query},
    )
    texto = _texto_do_resultado(resultado)
    if resultado.is_error:
        print(f"[Cliente MCP] Ferramenta retornou erro: {texto}", file=sys.stderr)
        return "Erro MCP: a ferramenta de busca falhou; nenhum documento foi retornado."
    return texto or "Erro MCP: resposta vazia do servidor."


class _SessaoMCPCompartilhada:
    """Mantém um único processo servidor MCP stdio aquecido para múltiplas buscas paralelas (D-001, D-024).

    Inicializa o subprocesso sob demanda (lazy) na primeira consulta real e serializa
    as chamadas JSON-RPC no pipe stdio com Lock assíncrono, evitando 3 cold boots
    de processos Python no padrão Plano–Executor.
    """

    def __init__(self, role: str):
        self.role = role.strip()
        self._init_lock = threading.Lock()
        self._iniciado = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop_event: asyncio.Event | None = None
        self._ready_event = threading.Event()
        self._erro_init: BaseException | None = None
        self._cliente: Client | None = None
        self._call_lock: asyncio.Lock | None = None

    def _garantir_iniciado(self) -> None:
        with self._init_lock:
            if self._iniciado:
                return
            self._iniciado = True
            self._thread = threading.Thread(target=self._rodar_loop, daemon=True)
            self._thread.start()
            self._ready_event.wait(timeout=TIMEOUT_SEGUNDOS)
            if self._erro_init is not None:
                raise self._erro_init

    def _rodar_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self._ciclo_vida())
        finally:
            loop.close()

    async def _ciclo_vida(self) -> None:
        self._stop_event = asyncio.Event()
        self._call_lock = asyncio.Lock()
        alvo = parametros_servidor(role=self.role)
        try:
            async with Client(alvo, read_timeout_seconds=TIMEOUT_SEGUNDOS) as cliente:
                self._cliente = cliente
                self._ready_event.set()
                await self._stop_event.wait()
        except BaseException as exc:  # noqa: BLE001
            self._erro_init = exc
            self._ready_event.set()

    async def _chamar_serializado(self, query: str) -> str:
        assert self._call_lock is not None and self._cliente is not None
        async with self._call_lock:
            return await _executar_call_tool_no_cliente(self._cliente, query)

    def consultar_sincrono(self, query: str) -> str:
        self._garantir_iniciado()
        assert self._loop is not None
        fut = asyncio.run_coroutine_threadsafe(self._chamar_serializado(query), self._loop)
        return fut.result(timeout=TIMEOUT_SEGUNDOS)

    def fechar(self) -> None:
        with self._init_lock:
            if not self._iniciado or self._loop is None:
                return
            if self._stop_event is not None and not self._loop.is_closed():
                self._loop.call_soon_threadsafe(self._stop_event.set)
            if self._thread is not None:
                self._thread.join(timeout=5.0)
            self._iniciado = False


_lock_sessoes = threading.Lock()
_sessoes_compartilhadas: dict[str, list[_SessaoMCPCompartilhada]] = {}


@contextmanager
def sessao_mcp_compartilhada(role: str):
    """Context manager que compartilha a mesma instância do servidor MCP entre tarefas paralelas (D-001, D-024)."""
    papel = role.strip()
    sessao = _SessaoMCPCompartilhada(papel)
    with _lock_sessoes:
        _sessoes_compartilhadas.setdefault(papel, []).append(sessao)
    try:
        yield sessao
    finally:
        with _lock_sessoes:
            pilha = _sessoes_compartilhadas.get(papel, [])
            if sessao in pilha:
                pilha.remove(sessao)
        sessao.fechar()


def _obter_sessao_compartilhada(role: str) -> _SessaoMCPCompartilhada | None:
    papel = (role or "").strip()
    with _lock_sessoes:
        pilha = _sessoes_compartilhadas.get(papel, [])
        return pilha[-1] if pilha else None


async def _chamar_mcp(alvo: Any, query: str, role: str | None = None) -> str:
    if alvo is None and role:
        sessao = _obter_sessao_compartilhada(role)
        if sessao is not None:
            return await asyncio.to_thread(sessao.consultar_sincrono, query)

    alvo_efetivo = alvo if alvo is not None else parametros_servidor(role=role)
    async with Client(alvo_efetivo, read_timeout_seconds=TIMEOUT_SEGUNDOS) as cliente:
        return await _executar_call_tool_no_cliente(cliente, query)


async def consultar_mcp_async(query: str, role: str, alvo: Any = None) -> str:
    """
    Consulta o servidor MCP assincronamente e devolve o texto da ferramenta.
    Permite concorrência nativa para tarefas paralelas (D-001, D-012, D-024).
    """
    trace = obter_trace_atual()
    if trace:
        trace.registrar_chamada_mcp(1)
        with trace.span("mcp_busca", tipo="tool_mcp", detalhes={"query": query, "role": role}) as span_ctx:
            try:
                resposta = await _chamar_mcp(alvo, query, role=role)
                span_ctx.detalhes["evidencia"] = resposta
                trace.registrar_evidencia_mcp(resposta)
                return resposta
            except Exception as erro:  # noqa: BLE001 - transporte/SDK podem lançar classes variadas
                print(f"[Cliente MCP] Falha ao consultar o servidor (async): {erro!r}", file=sys.stderr)
                msg_erro = "Erro MCP: não foi possível consultar o servidor de documentos."
                span_ctx.detalhes["evidencia"] = msg_erro
                trace.registrar_evidencia_mcp(msg_erro)
                return msg_erro
    try:
        return await _chamar_mcp(alvo, query, role=role)
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

