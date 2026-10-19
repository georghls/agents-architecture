import operator
import os
from typing import Annotated, TypedDict
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from src.agentes.coordenador import MonitorAPI, _extrair_texto
from src.agentes.mcp_toolkit import criar_ferramenta_busca
from src.config import chave_gemini


# 1. MODELOS DE DADOS E CONTRATOS DO PLANO
class Subtarefa(BaseModel):
    id: int = Field(
        description="Identificador numérico da tarefa (1, 2 ou 3)."
    )
    descricao: str = Field(
        description="Descrição curta do que esta tarefa pretende investigar."
    )
    query_busca: str = Field(
        description="Termo ou frase exata a ser pesquisada na base de documentos da empresa."
    )


class PlanoDeAcao(BaseModel):
    tarefas: list[Subtarefa] = Field(
        min_length=1,
        max_length=3,
        description="Lista de no mínimo 1 e no máximo 3 tarefas essenciais e independentes para responder à pergunta."
    )


# 2. ESTADOS DO GRAFO
class EstadoEntradaExecutor(TypedDict):
    id_tarefa: int
    descricao: str
    query_busca: str
    role: str


class EstadoPlanoExecutor(TypedDict):
    role: str
    pergunta: str
    plano: list[dict]
    resultados: Annotated[list[dict], operator.add]
    resposta_final: str


# 3. INICIALIZAÇÃO DO MODELO LLM
MODELO_LLM = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")

llm = ChatGoogleGenerativeAI(
    model=MODELO_LLM,
    temperature=0,
    api_key=chave_gemini(),
    max_retries=5,
)


# 4. NÓS DO GRAFO

def planejador_node(state: EstadoPlanoExecutor):
    """Analisa a pergunta do usuário e decompõe em 1 a 3 subtarefas de busca corporativa."""
    pergunta = state["pergunta"]
    print(f"\n[Planejador] Elaborando plano para: '{pergunta}'...")

    llm_estruturado = llm.with_structured_output(PlanoDeAcao)

    instrucao = SystemMessage(
        content=(
            "Você é o Planejador do sistema corporativo. Decomponha a pergunta do usuário em tarefas "
            "de busca na base documental interna da empresa.\n"
            "Diretrizes:\n"
            "1. Para perguntas diretas e simples (ex: 'qual o cardápio?'), gere apenas 1 tarefa pontual.\n"
            "2. Para perguntas com múltiplos aspectos (ex: orçamento, datas, metas), gere 2 ou no máximo 3 tarefas complementares.\n"
            "3. O plano DEVE conter entre 1 e 3 tarefas independentes que possam rodar em paralelo.\n"
            "4. Cada tarefa deve possuir uma query_busca objetiva e relevante."
        )
    )

    plano_gerado: PlanoDeAcao = llm_estruturado.invoke([instrucao, HumanMessage(content=pergunta)])
    tarefas_serializadas = [t.model_dump() for t in plano_gerado.tarefas]

    print(f"[Planejador] Plano gerado com {len(tarefas_serializadas)} tarefa(s):")
    for t in tarefas_serializadas:
        print(f"  - Tarefa {t['id']}: {t['descricao']} (Busca: '{t['query_busca']}')")

    return {"plano": tarefas_serializadas}


def distribuir_tarefas(state: EstadoPlanoExecutor) -> list[Send]:
    """Borda condicional de Fan-Out: distribui as tarefas em paralelo para o executor via Send API."""
    plano = state.get("plano", [])
    role = state["role"]
    return [
        Send(
            "executor",
            {
                "id_tarefa": t["id"],
                "descricao": t["descricao"],
                "query_busca": t["query_busca"],
                "role": role,
            },
        )
        for t in plano
    ]


def executor_node(state: EstadoEntradaExecutor):
    """Executa uma tarefa individual de pesquisa acionando a ferramenta MCP segura com a role do estado."""
    id_t = state["id_tarefa"]
    descricao = state["descricao"]
    query = state["query_busca"]
    role = state["role"]

    print(f"[Executor - Tarefa {id_t}] Buscando: '{query}' como perfil '{role}'...")

    # REGRA DE OURO (D-010 / D-011): A ferramenta MCP é criada com o papel seguro do estado.
    ferramenta = criar_ferramenta_busca(role)
    resultado = ferramenta.invoke({"query": query})

    return {
        "resultados": [
            {
                "id_tarefa": id_t,
                "descricao": descricao,
                "query_busca": query,
                "resultado_mcp": resultado,
            }
        ]
    }


def sintetizador_node(state: EstadoPlanoExecutor):
    """Consolida as evidências de todas as tarefas paralelas (Fan-In) e gera a resposta final."""
    print("\n[Sintetizador] Consolidando resultados de todas as tarefas...")
    pergunta = state["pergunta"]
    resultados = state.get("resultados", [])

    blocos_evidencias = []
    for r in resultados:
        blocos_evidencias.append(
            f"--- [Tarefa {r['id_tarefa']}: {r['descricao']}] ---\n"
            f"Busca realizada: {r['query_busca']}\n"
            f"Evidência retornada: {r['resultado_mcp']}"
        )
    contexto_evidencias = "\n\n".join(blocos_evidencias)

    instrucao = SystemMessage(
        content=(
            "Você é o sintetizador final do sistema corporativo. "
            "Sua missão é responder à pergunta original do usuário com base ESTRITAMENTE nas evidências "
            "coletadas pelas tarefas de pesquisa abaixo.\n\n"
            "Regras obrigatórias de conformidade:\n"
            "1. Responda de forma clara, educada e formal em português.\n"
            "2. Se as evidências indicarem 'Nenhum documento encontrado', erro de acesso ou ausência de registros "
            "autorizados para o tema, informe explicitamente que não constam informações sobre este assunto "
            "disponíveis para o seu perfil de acesso.\n"
            "3. NUNCA invente informações, não alucine dados corporativos e não cite conteúdos alheios.\n\n"
            f"EVIDÊNCIAS COLETADAS VIA MCP:\n{contexto_evidencias}"
        )
    )

    resposta = llm.invoke([instrucao, HumanMessage(content=pergunta)])
    texto_resposta = _extrair_texto(resposta)

    print(f"\n--- [Resposta Final do Plano-Executor] ---\n{texto_resposta}\n")
    return {"resposta_final": texto_resposta}


# 5. MONTAGEM DO GRAFO LANGGRAPH (FAN-OUT / FAN-IN)
workflow = StateGraph(EstadoPlanoExecutor)

workflow.add_node("planejador", planejador_node)
workflow.add_node("executor", executor_node)
workflow.add_node("sintetizador", sintetizador_node)

workflow.add_edge(START, "planejador")
workflow.add_conditional_edges("planejador", distribuir_tarefas, ["executor"])
workflow.add_edge("executor", "sintetizador")
workflow.add_edge("sintetizador", END)

grafo_plano_executor = workflow.compile()


def executar_plano_executor(pergunta: str, role: str = "geral", exibir_metricas: bool = True) -> str:
    """Executa o agente Plano-Executor de ponta a ponta com rastreamento de métricas."""
    monitor = MonitorAPI()
    estado_inicial: EstadoPlanoExecutor = {
        "role": role,
        "pergunta": pergunta,
        "plano": [],
        "resultados": [],
        "resposta_final": "",
    }

    resultado = grafo_plano_executor.invoke(estado_inicial, config={"callbacks": [monitor]})

    if exibir_metricas:
        print(monitor.relatorio())

    return resultado["resposta_final"]


if __name__ == "__main__":
    print("=" * 60)
    print("AGENTE PLANO-EXECUTOR (LangGraph + Fan-Out Paralelo + MCP)")
    print("=" * 60)

    pergunta_teste = "Qual o orçamento e os detalhes do projeto secreto da empresa?"

    print(f"\nPergunta: '{pergunta_teste}'\n")

    print("-" * 30 + " CENÁRIO 1: GERAL " + "-" * 30)
    resp_geral = executar_plano_executor(pergunta_teste, role="geral")
    print(f"[Resultado Geral]:\n{resp_geral}\n")

    print("-" * 30 + " CENÁRIO 2: DIRETORIA " + "-" * 30)
    resp_diretoria = executar_plano_executor(pergunta_teste, role="diretoria")
    print(f"[Resultado Diretoria]:\n{resp_diretoria}\n")
