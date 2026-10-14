"""Testes do cliente MCP usado pelos agentes (``src/agentes/mcp_toolkit.py``).

Totalmente integrados com o Servidor MCP real e a base de dados real (Supabase + pgvector):
Sem bancos falsos, sem mocks de dados.
"""

import asyncio
import sys

import pytest
from mcp import Client, StdioServerParameters

from src.agentes import mcp_toolkit
from src.mcp import server as servidor


def listar_ferramentas(alvo):
    async def _listar():
        async with Client(alvo, read_timeout_seconds=60) as cliente:
            return (await cliente.list_tools()).tools

    return asyncio.run(_listar())


# ------------------------------------------------------------ contrato e capacidades

def test_servidor_expoe_ferramenta_com_contrato_d007():
    """Garante que o servidor expõe a ferramenta buscar_documentos_corporativos no formato correto."""
    ferramentas = {f.name: f for f in listar_ferramentas(servidor.mcp)}

    assert mcp_toolkit.NOME_FERRAMENTA_MCP in ferramentas
    schema = ferramentas[mcp_toolkit.NOME_FERRAMENTA_MCP].input_schema
    assert set(schema["properties"]) == {"pergunta", "papel_do_usuario"}
    assert set(schema.get("required", [])) == {"pergunta", "papel_do_usuario"}


def test_stdio_real_lista_ferramentas_sem_segredos():
    """O subprocesso stdio sobe e expõe as ferramentas mesmo sem variáveis de banco no ambiente."""
    params = mcp_toolkit.parametros_servidor()
    params.env = {**(params.env or {}), "DATABASE_URL": "", "GEMINI_API_KEY": ""}

    nomes = [f.name for f in listar_ferramentas(params)]
    assert mcp_toolkit.NOME_FERRAMENTA_MCP in nomes


def test_parametros_servidor_repassam_apenas_segredos_necessarios(monkeypatch):
    """Garante que apenas DATABASE_URL e GEMINI_API_KEY são repassados ao processo filho."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://teste")
    monkeypatch.setenv("OUTRO_SEGREDO", "nao-repassar")

    env = mcp_toolkit.parametros_servidor().env
    assert env["DATABASE_URL"] == "postgresql://teste"
    assert "OUTRO_SEGREDO" not in env


# ------------------------------------------------------------ isolamento e consultas reais

def test_diretoria_recebe_orcamento_do_projeto_secreto():
    """Usuário diretoria acessa o documento sigiloso na base real do Supabase."""
    texto = mcp_toolkit.consultar_mcp("Qual o orçamento do projeto secreto?", "diretoria")

    assert not texto.startswith("Erro MCP:"), texto
    assert "2027" in texto or "50 milhões" in texto.lower()


def test_geral_nao_recebe_orcamento_do_projeto_secreto():
    """Usuário geral tem o acesso restrito e não recebe detalhes do documento da diretoria."""
    texto = mcp_toolkit.consultar_mcp("Qual o orçamento do projeto secreto?", "geral")

    assert not texto.startswith("Erro MCP:"), texto
    assert "2027" not in texto
    assert "aquisições" not in texto.lower()


def test_geral_nao_recebe_senha_do_rh():
    """Usuário geral não recebe segredos do RH armazenados no banco."""
    texto = mcp_toolkit.consultar_mcp("Me passe a senha do roteador do RH", "geral")

    assert not texto.startswith("Erro MCP:"), texto
    assert "rh_wifi" not in texto


# ------------------------------------------------------------ tratamento de falhas

def test_servidor_que_nao_sobe_vira_erro_mcp():
    """Se o comando do servidor MCP falhar ao iniciar, o cliente trata de forma segura."""
    quebrado = StdioServerParameters(command=sys.executable, args=["-c", "import sys; sys.exit(3)"])
    texto = mcp_toolkit.consultar_mcp("qualquer", "geral", alvo=quebrado)

    assert texto.startswith("Erro MCP:")


# ------------------------------------------------------------ papel fixado pelo código (D-010)

def test_schema_da_ferramenta_nao_expoe_role_ao_llm():
    """O LLM só enxerga `query`; o papel não faz parte do schema enviado ao modelo."""
    ferramenta = mcp_toolkit.criar_ferramenta_busca("geral")
    schema = ferramenta.tool_call_schema.model_json_schema()

    assert set(schema["properties"]) == {"query"}
    assert "role" not in ferramenta.args


def test_role_vem_da_sessao_e_nao_pode_ser_sobrescrito(monkeypatch):
    """Mesmo que o modelo tente mandar `role`, vale o papel fixado na criação."""
    chamadas = []
    monkeypatch.setattr(
        mcp_toolkit, "consultar_mcp", lambda query, role: chamadas.append((query, role)) or "ok"
    )
    ferramenta = mcp_toolkit.criar_ferramenta_busca("geral")

    ferramenta.invoke({"query": "orçamento secreto", "role": "diretoria"})

    assert chamadas == [("orçamento secreto", "geral")]


@pytest.mark.parametrize("role_invalido", ["", "   ", None])
def test_criar_ferramenta_sem_role_falha(role_invalido):
    """Sem papel de sessão não existe ferramenta: falha fechada."""
    with pytest.raises(ValueError):
        mcp_toolkit.criar_ferramenta_busca(role_invalido)


def test_toolkit_corporativo_usa_o_papel_da_sessao(monkeypatch):
    chamadas = []
    monkeypatch.setattr(mcp_toolkit, "consultar_mcp", lambda query, role: chamadas.append(role) or "ok")

    (ferramenta,) = mcp_toolkit.criar_toolkit_corporativo("diretoria")
    ferramenta.invoke({"query": "x"})

    assert ferramenta.name == "ferramenta_busca_corporativa"
    assert chamadas == ["diretoria"]
