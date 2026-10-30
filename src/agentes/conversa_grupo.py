"""Padrão Conversação em Grupo (Group Chat) utilizando Microsoft AutoGen 0.4+.

Implementa o terceiro padrão arquitetural avaliado no estudo dirigido (Fase 3).
Orquestra três agentes autônomos em rodadas sequenciais (Round-Robin):
  1. Retrieval Agent: único agente conectado à ferramenta MCP segura (via JWT/RBAC).
  2. Analyst Agent: sintetiza as respostas com base estritamente nas evidências documentais.
  3. Validator Agent: audita a resposta contra alucinações e emite o sinal de término ("TERMINATE").

Conforme D-010, D-011 e D-013:
- O papel do usuário (role) não é exposto no schema do LLM; é assinado em token JWT (HS256)
  diretamente na closure da ferramenta MCP no cliente.
- A orquestração usa RoundRobinGroupChat para eliminar chamadas extras de mediação e garantir
  a ordem estrita: busca -> análise -> validação.
"""

import asyncio
import os
import sys
from typing import Any, Sequence

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.models import ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient

from src.agentes.mcp_toolkit import criar_ferramenta_autogen
from src.config import chave_gemini

# Modelo padrão otimizado e disponível
MODELO_PADRAO_GEMINI = "gemini-flash-lite-latest"
URL_BASE_GEMINI_OPENAI = "https://generativelanguage.googleapis.com/v1beta/openai/"


# ----------------------------------------------------------------------
# 1. CLIENTE DE MODELO COGNITIVO
# ----------------------------------------------------------------------

def criar_cliente_modelo(
    modelo: str | None = None,
    api_key: str | None = None,
) -> OpenAIChatCompletionClient:
    """Cria o cliente do Google Gemini compatível com o protocolo OpenAI no AutoGen 0.4.

    Utiliza o endpoint oficial da Google Generative Language API que expõe a
    interface Chat Completions padrão (RFC-compatible).
    """
    nome_modelo = modelo or os.environ.get("GEMINI_MODEL", MODELO_PADRAO_GEMINI)
    chave = api_key or chave_gemini()

    info = ModelInfo(
        vision=False,
        function_calling=True,
        json_output=True,
        structured_output=True,
        family="unknown",
    )

    return OpenAIChatCompletionClient(
        model=nome_modelo,
        api_key=chave,
        base_url=URL_BASE_GEMINI_OPENAI,
        model_info=info,
    )


# ----------------------------------------------------------------------
# 2. PROMPTS DAS PERSONAS ESPECIALIZADAS
# ----------------------------------------------------------------------

PROMPT_RETRIEVAL = """Você é o Agente de Recuperação Documental da empresa.
Sua ÚNICA responsabilidade na equipe é buscar informações na base interna corporativa usando a ferramenta 'buscar_documentos_corporativos'.

Diretrizes obrigatórias:
1. Ao receber a pergunta do usuário ou do grupo, acione SEMPRE a ferramenta de busca corporativa formulando a query de busca adequada.
2. Quando a ferramenta retornar o resultado:
   - Se documentos relevantes forem encontrados, apresente os trechos e fatos com máxima fidelidade para que o Analista possa trabalhar.
   - Se a ferramenta informar que nenhum documento foi encontrado ou que o acesso foi negado pelo perfil de segurança, declare expressamente: "Nenhum documento encontrado na base corporativa para este perfil de acesso."
3. NUNCA invente, presuma ou deduza fatos, números, senhas ou orçamentos que não constem na resposta da ferramenta.
"""

PROMPT_ANALYST = """Você é o Analista Corporativo da empresa.
Sua missão é examinar criticamente os dados trazidos pelo Agente de Recuperação e redigir uma resposta formal, clara, objetiva e completa para a dúvida do usuário.

Diretrizes obrigatórias:
1. Baseie sua resposta ESTRITAMENTE nas evidências e trechos documentais apresentados pelo Agente de Recuperação.
2. Se o Agente de Recuperação informar que nenhum documento foi localizado (ou que o perfil não possui autorização), informe educadamente ao usuário que a empresa não dispõe de registros acessíveis para a consulta solicitada.
3. Não presuma informações ausentes. Nunca alucine dados financeiros, projetos sigilosos ou políticas que não estejam expressamente documentadas.
4. Responda diretamente ao usuário em tom corporativo e polido.
"""

PROMPT_VALIDATOR = """Você é o Validador e Auditor Corporativo de Qualidade e Segurança.
Sua responsabilidade é inspecionar criticamente a resposta elaborada pelo Analista, confrontando-a com as evidências trazidas pelo Agente de Recuperação.

Critérios de auditoria:
1. Integridade: A resposta do Analista contém apenas afirmações sustentadas pelas evidências recuperadas?
2. Segurança e Falha Fechada: Se nenhum dado foi encontrado pelo Recuperador, o Analista admitiu corretamente a ausência de dados sem especular?
3. Encerramento:
   - Se a resposta do Analista estiver correta, fiel e segura, valide a resposta e finalize OBRIGATORIAMENTE sua mensagem incluindo a palavra 'TERMINATE'.
   - Se identificar incoerências, extrapolações ou omissões graves, aponte exatamente o que deve ser corrigido pelo Analista sem incluir a palavra de término.
"""


# ----------------------------------------------------------------------
# 3. CRIAÇÃO DA EQUIPE DE CONVERSAÇÃO
# ----------------------------------------------------------------------

def criar_equipe_conversa_grupo(
    role: str,
    model_client: Any | None = None,
    alvo_mcp: Any | None = None,
    max_mensagens: int = 6,
) -> RoundRobinGroupChat:
    """Instancia os três agentes e monta a equipe de conversa em grupo (D-013).

    Args:
        role: Papel de acesso RBAC da sessão do usuário ('geral', 'diretoria', etc.).
              O papel é fixado na ferramenta MCP segura e nunca exposto ao modelo.
        model_client: Cliente de LLM a ser utilizado pelos agentes (injetável para testes).
        alvo_mcp: Destino opcional do MCP (ex.: parâmetros de subprocesso ou instância em testes).
        max_mensagens: Limite de mensagens na sala para evitar loops infinitos.
    """
    if not isinstance(role, str) or not role.strip():
        raise ValueError("O papel (role) da sessão é obrigatório para a equipe de conversação.")

    cliente = model_client or criar_cliente_modelo()

    # Apenas o Retrieval Agent recebe a ferramenta de busca corporativa
    ferramenta_busca = criar_ferramenta_autogen(role=role, alvo=alvo_mcp)

    agente_retrieval = AssistantAgent(
        name="retrieval_agent",
        description="Agente encarregado de consultar documentos internos via servidor MCP.",
        system_message=PROMPT_RETRIEVAL,
        model_client=cliente,
        tools=[ferramenta_busca],
    )

    agente_analyst = AssistantAgent(
        name="analyst_agent",
        description="Analista corporativo encarregado de sintetizar as respostas baseando-se nas evidências.",
        system_message=PROMPT_ANALYST,
        model_client=cliente,
    )

    agente_validator = AssistantAgent(
        name="validator_agent",
        description="Validador e auditor encarregado de aprovar a resposta e encerrar a sessão.",
        system_message=PROMPT_VALIDATOR,
        model_client=cliente,
    )

    # Condição de parada dupla: sinal TERMINATE emitido pelo validador OU limite estrito de turnos
    condicao_termino = TextMentionTermination("TERMINATE") | MaxMessageTermination(max_messages=max_mensagens)

    return RoundRobinGroupChat(
        participants=[agente_retrieval, agente_analyst, agente_validator],
        termination_condition=condicao_termino,
    )


# ----------------------------------------------------------------------
# 4. FUNÇÕES PÚBLICAS DE EXECUÇÃO
# ----------------------------------------------------------------------

def _extrair_resposta_final(mensagens: Sequence[Any]) -> str:
    """Extrai a resposta final útil formulada para o usuário.

    Prioriza a última manifestação substancial do Analista (quem redige a resposta).
    Se o Analista não respondeu, utiliza o parecer do Validador.
    """
    for msg in reversed(mensagens):
        fonte = getattr(msg, "source", "")
        conteudo = getattr(msg, "content", "")
        if isinstance(conteudo, str) and conteudo.strip():
            # Limpa o marcador de controle se estiver presente
            limpo = conteudo.replace("TERMINATE", "").strip()
            if fonte == "analyst_agent" and limpo:
                return limpo

    # Fallback: última mensagem não vazia
    for msg in reversed(mensagens):
        conteudo = getattr(msg, "content", "")
        if isinstance(conteudo, str) and conteudo.strip():
            limpo = conteudo.replace("TERMINATE", "").strip()
            if limpo:
                return limpo

    return "Não foi possível obter uma resposta conclusiva dos agentes."


def _extrair_evidencias(mensagens: Sequence[Any]) -> list[str]:
    """Coleta os trechos de documentos ou resultados de ferramentas trafegados na conversa."""
    evidencias = []
    for msg in mensagens:
        # Mensagens de resultado de chamada de ferramenta
        if getattr(msg, "type", "") in ("ToolCallResultMessage", "FunctionExecutionResultMessage"):
            conteudo = getattr(msg, "content", "")
            if isinstance(conteudo, list):
                for item in conteudo:
                    texto = getattr(item, "content", str(item))
                    if texto:
                        evidencias.append(str(texto))
            elif isinstance(conteudo, str) and conteudo:
                evidencias.append(conteudo)
    return evidencias


async def executar_conversa_grupo_async(
    pergunta: str,
    papel: str = "geral",
    model_client: Any | None = None,
    alvo_mcp: Any | None = None,
    max_mensagens: int = 6,
) -> dict:
    """Executa a conversa em grupo de forma assíncrona.

    Retorna dicionário estruturado com:
      - 'pergunta': Pergunta original do usuário.
      - 'papel': Papel de autorização da sessão.
      - 'resposta_final': Síntese da resposta final validada.
      - 'mensagens': Histórico completo de mensagens e falas dos agentes.
      - 'evidencias': Trechos documentais recuperados no MCP.
      - 'turnos': Quantidade total de mensagens trocadas.
      - 'motivo_parada': Motivo da finalização do chat.
    """
    deve_fechar_cliente = model_client is None
    cliente = model_client or criar_cliente_modelo()

    try:
        equipe = criar_equipe_conversa_grupo(
            role=papel,
            model_client=cliente,
            alvo_mcp=alvo_mcp,
            max_mensagens=max_mensagens,
        )

        tarefa_inicial = (
            f"Pergunta do usuário: '{pergunta}'.\n"
            f"Por favor, investiguem a base interna corporativa, analisem os fatos e forneçam uma resposta precisa."
        )

        resultado = await equipe.run(task=tarefa_inicial)

        mensagens_formatadas = []
        for msg in resultado.messages:
            conteudo = getattr(msg, "content", "")
            fonte = getattr(msg, "source", "sistema")
            tipo = msg.__class__.__name__

            # Formata o conteúdo para string legível caso seja lista
            if isinstance(conteudo, list):
                conteudo_str = "\n".join(str(getattr(c, "content", c)) for c in conteudo)
            else:
                conteudo_str = str(conteudo)

            mensagens_formatadas.append({
                "autor": fonte,
                "tipo": tipo,
                "conteudo": conteudo_str,
            })

        resposta_final = _extrair_resposta_final(resultado.messages)
        evidencias = _extrair_evidencias(resultado.messages)

        return {
            "pergunta": pergunta,
            "papel": papel,
            "resposta_final": resposta_final,
            "mensagens": mensagens_formatadas,
            "evidencias": evidencias,
            "turnos": len(resultado.messages),
            "motivo_parada": str(resultado.stop_reason),
        }
    finally:
        if deve_fechar_cliente and hasattr(cliente, "close"):
            await cliente.close()
            # No Windows, dá tempo aos sockets de conexão do loop fecharem graciosamente
            await asyncio.sleep(0.05)


def executar_conversa_grupo(
    pergunta: str,
    papel: str = "geral",
    model_client: Any | None = None,
    alvo_mcp: Any | None = None,
    max_mensagens: int = 6,
) -> dict:
    """Interface síncrona para execução da conversa em grupo."""
    return asyncio.run(
        executar_conversa_grupo_async(
            pergunta=pergunta,
            papel=papel,
            model_client=model_client,
            alvo_mcp=alvo_mcp,
            max_mensagens=max_mensagens,
        )
    )
