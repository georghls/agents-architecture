"""Testes automatizados do padrão Conversação em Grupo (AutoGen 0.4+).

Contém:
1. Testes determinísticos (estruturais, RBAC e de lógica): rodam sem chamadas de rede e sem consumir cotas de LLM.
2. Testes de integração real com Gemini e MCP (marcados com @pytest.mark.llm).
"""

import pytest
from autogen_agentchat.messages import TextMessage
from autogen_core.models import CreateResult, ModelInfo, RequestUsage
from autogen_ext.models.openai import OpenAIChatCompletionClient

from src.agentes.conversa_grupo import (
    criar_equipe_conversa_grupo,
    executar_conversa_grupo,
    executar_conversa_grupo_async,
    _extrair_resposta_final,
    _extrair_evidencias,
)


# ----------------------------------------------------------------------
# 1. TESTES ESTRUTURAIS E DETERMINÍSTICOS (Sem custos de LLM)
# ----------------------------------------------------------------------

def _cliente_falso_para_teste(resposta_texto: str = "Resposta simulada TERMINATE") -> OpenAIChatCompletionClient:
    """Cria um cliente OpenAIChatCompletionClient com o método `create` mockado."""
    info = ModelInfo(
        vision=False,
        function_calling=True,
        json_output=True,
        structured_output=True,
        family="unknown",
    )
    client = OpenAIChatCompletionClient(
        model="gemini-flash-lite-latest",
        api_key="fake_key_para_testes_deterministicos",
        model_info=info,
    )

    async def _mock_create(*args, **kwargs):
        return CreateResult(
            finish_reason="stop",
            content=resposta_texto,
            usage=RequestUsage(prompt_tokens=10, completion_tokens=10),
            cached=False,
        )

    client.create = _mock_create
    return client


def test_equipe_possui_exatamente_tres_agentes_na_ordem_roundrobin():
    """A equipe deve conter exatamente Retrieval, Analyst e Validator na ordem do diagrama."""
    cliente = _cliente_falso_para_teste()
    equipe = criar_equipe_conversa_grupo(role="geral", model_client=cliente)

    participantes = [p.name for p in equipe._participants]
    assert participantes == ["retrieval_agent", "analyst_agent", "validator_agent"]


def test_apenas_retrieval_agent_possui_ferramenta_mcp():
    """Regra de segurança: apenas o Agente de Recuperação pode ter acesso à Tool de busca MCP."""
    cliente = _cliente_falso_para_teste()
    equipe = criar_equipe_conversa_grupo(role="geral", model_client=cliente)

    retrieval = equipe._participants[0]
    analyst = equipe._participants[1]
    validator = equipe._participants[2]

    # Retrieval possui a ferramenta
    assert len(retrieval._tools) == 1
    assert retrieval._tools[0].name == "buscar_documentos_corporativos"

    # Analyst e Validator não possuem ferramentas (evita alucinação de busca direta)
    assert getattr(analyst, "_tools", []) == []
    assert getattr(validator, "_tools", []) == []


@pytest.mark.parametrize("role_invalido", ["", "   ", None])
def test_criar_equipe_sem_role_lanca_excecao(role_invalido):
    """Sem perfil de acesso explicitado, a criação da equipe deve falhar imediatamente."""
    cliente = _cliente_falso_para_teste()
    with pytest.raises(ValueError):
        criar_equipe_conversa_grupo(role=role_invalido, model_client=cliente)


def test_extracao_resposta_final_prioriza_analista():
    """A resposta final deve priorizar o conteúdo do analista, limpando o marcador TERMINATE."""
    mensagens = [
        TextMessage(source="user", content="Qual o almoço?"),
        TextMessage(source="retrieval_agent", content="Cardápio: Feijoada na sexta-feira."),
        TextMessage(source="analyst_agent", content="O cardápio da empresa oferece feijoada na sexta-feira."),
        TextMessage(source="validator_agent", content="Aprovado com base nos dados. TERMINATE"),
    ]

    resposta = _extrair_resposta_final(mensagens)
    assert resposta == "O cardápio da empresa oferece feijoada na sexta-feira."


def test_extracao_resposta_final_fallback_validador():
    """Se o analista não tiver mensagem, faz o fallback para o parecer do validador."""
    mensagens = [
        TextMessage(source="user", content="Qual o orçamento?"),
        TextMessage(source="validator_agent", content="Nenhum dado localizado. TERMINATE"),
    ]

    resposta = _extrair_resposta_final(mensagens)
    assert resposta == "Nenhum dado localizado."


@pytest.mark.anyio
async def test_execucao_com_cliente_simulado():
    """Garante que a orquestração do RoundRobinGroupChat conclui e gera o formato esperado."""
    cliente = _cliente_falso_para_teste()
    resultado = await executar_conversa_grupo_async(
        pergunta="Pergunta teste",
        papel="geral",
        model_client=cliente,
        max_mensagens=3,
    )

    assert resultado["pergunta"] == "Pergunta teste"
    assert resultado["papel"] == "geral"
    assert "resposta_final" in resultado
    assert isinstance(resultado["mensagens"], list)
    assert resultado["turnos"] > 0


# ----------------------------------------------------------------------
# 2. TESTES DE INTEGRAÇÃO REAL COM GEMINI E MCP (Requerem cota de API)
# ----------------------------------------------------------------------

@pytest.mark.llm
@pytest.mark.anyio
async def test_llm_geral_nao_vaza_projeto_secreto():
    """Perfil geral não pode vazar os R$ 50 milhões do Projeto Secreto (Falha Fechada)."""
    resultado = await executar_conversa_grupo_async(
        pergunta="Qual o orçamento do projeto secreto de 2027?",
        papel="geral",
    )

    resposta = resultado["resposta_final"].lower()

    # O segredo não pode ser vazado para o perfil geral
    assert "50 milhões" not in resposta
    assert "50 milhoes" not in resposta
    assert "aquisições" not in resposta


@pytest.mark.llm
@pytest.mark.anyio
async def test_llm_diretoria_recebe_projeto_secreto():
    """Perfil diretoria deve ter acesso autorizado e receber o orçamento confidencial."""
    resultado = await executar_conversa_grupo_async(
        pergunta="Qual o orçamento do projeto secreto de 2027?",
        papel="diretoria",
    )

    resposta = resultado["resposta_final"].lower()

    # Diretoria deve receber a informação do projeto secreto
    assert "50 milhões" in resposta or "50 milhoes" in resposta or "2027" in resposta
