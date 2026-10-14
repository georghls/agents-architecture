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


# ------------------------------------------------------------ contrato e capacidades (D-011)

def test_servidor_expoe_ferramenta_com_contrato_d011():
    """Garante que a ferramenta buscar_documentos_corporativos recebe apenas 'pergunta'.
    
    O papel do usuário não é exposto como argumento na ferramenta MCP; ele é
    autenticado via token JWT na sessão (A-05).
    """
    ferramentas = {f.name: f for f in listar_ferramentas(servidor.mcp)}

    assert mcp_toolkit.NOME_FERRAMENTA_MCP in ferramentas
    schema = ferramentas[mcp_toolkit.NOME_FERRAMENTA_MCP].input_schema
    assert set(schema["properties"]) == {"pergunta"}
    assert set(schema.get("required", [])) == {"pergunta"}


def test_stdio_real_lista_ferramentas_sem_segredos():
    """O subprocesso stdio sobe e expõe as ferramentas mesmo sem variáveis de banco no ambiente."""
    params = mcp_toolkit.parametros_servidor()
    params.env = {**(params.env or {}), "DATABASE_URL": "", "GEMINI_API_KEY": ""}

    nomes = [f.name for f in listar_ferramentas(params)]
    assert mcp_toolkit.NOME_FERRAMENTA_MCP in nomes


def test_parametros_servidor_repassam_apenas_segredos_necessarios(monkeypatch):
    """Garante que apenas DATABASE_URL, GEMINI_API_KEY e AUTH_SECRET_KEY são repassados ao processo filho."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://teste")
    monkeypatch.setenv("AUTH_SECRET_KEY", "chave-teste-32-caracteres-minimo")
    monkeypatch.setenv("OUTRO_SEGREDO", "nao-repassar")

    env = mcp_toolkit.parametros_servidor().env
    assert env["DATABASE_URL"] == "postgresql://teste"
    assert env["AUTH_SECRET_KEY"] == "chave-teste-32-caracteres-minimo"
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


# ------------------------------------------------------------ autenticação confiável (A-05 - JWT)

from src.autorizacao.tokens import (
    TokenAusenteErro,
    TokenExpiradoErro,
    TokenInvalidoErro,
    gerar_token_sessao,
    validar_token_sessao,
)


def test_geracao_e_validacao_token_jwt():
    """Gera token assinado e valida se claims e papel são preservados com precisão."""
    token = gerar_token_sessao("diretoria", usuario_id="user_teste", expiracao_segundos=120)
    payload = validar_token_sessao(token)

    assert payload["sub"] == "user_teste"
    assert payload["papel"] == "diretoria"
    assert "exp" in payload


def test_token_expirado_falha():
    """Token com expiração retroativa é rejeitado imediatamente."""
    token_expirado = gerar_token_sessao("geral", expiracao_segundos=-10)

    with pytest.raises(TokenExpiradoErro):
        validar_token_sessao(token_expirado)


def test_token_adulterado_falha():
    """Se o payload for adulterado (ex: trocar geral por diretoria), a assinatura invalida."""
    token = gerar_token_sessao("geral")
    partes = token.split(".")
    # Substitui a última letra da assinatura para simular adulteração
    token_corrompido = f"{partes[0]}.{partes[1]}.{'A' if partes[2][-1] != 'A' else 'B'}"

    with pytest.raises(TokenInvalidoErro):
        validar_token_sessao(token_corrompido)


def test_token_com_chave_errada_falha():
    """Token assinado com chave de outro emissor é rejeitado."""
    token = gerar_token_sessao("diretoria", segredo="outra-chave-secreta-diferente-32chars")

    with pytest.raises(TokenInvalidoErro):
        validar_token_sessao(token)


def test_token_sem_papel_falha():
    """Tentativa de emitir token sem papel de acesso falha fechado."""
    with pytest.raises(ValueError):
        gerar_token_sessao("")


def test_servidor_sem_token_retorna_erro_auth():
    """Sem token de autenticação, o servidor MCP recusa o acesso por padrão."""
    params = mcp_toolkit.parametros_servidor(token="")
    params.env = {k: v for k, v in (params.env or {}).items() if k != "MCP_AUTH_TOKEN"}

    texto = mcp_toolkit.consultar_mcp("qualquer", "geral", alvo=params)
    assert "erro" in texto.lower() or "acesso negado" in texto.lower()


def test_servidor_com_token_forjado_retorna_erro_auth():
    """Tentativa de enviar token forjado com chave arbitrária é barrada no servidor."""
    token_forjado = gerar_token_sessao("diretoria", segredo="chave-invasor-nao-autorizada-32ch")
    params = mcp_toolkit.parametros_servidor(token=token_forjado)

    texto = mcp_toolkit.consultar_mcp("qualquer", "geral", alvo=params)
    assert "erro" in texto.lower() or "acesso negado" in texto.lower()

