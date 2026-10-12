import os
from typing import TypedDict, Annotated, Sequence, Literal
from pydantic import BaseModel, Field

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agentes.mcp_toolkit import ferramenta_busca_corporativa
from src.config import chave_gemini


# 1. MONITOR E CONTADOR DE CHAMADAS DE API
class MonitorAPI(BaseCallbackHandler):
    """Callback para rastrear com precisão chamadas à API do Gemini e consumo de tokens."""

    def __init__(self):
        super().__init__()
        self.chamadas_llm: int = 0
        self.chamadas_mcp: int = 0
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.total_tokens: int = 0

    def on_llm_end(self, response, **kwargs):
        self.chamadas_llm += 1
        for generations in getattr(response, "generations", []):
            for gen in generations:
                msg = getattr(gen, "message", None)
                usage = getattr(msg, "usage_metadata", None)
                if usage:
                    self.input_tokens += usage.get("input_tokens", 0)
                    self.output_tokens += usage.get("output_tokens", 0)
                    self.total_tokens += usage.get("total_tokens", 0)

    def on_tool_end(self, output, **kwargs):
        self.chamadas_mcp += 1

    def relatorio(self) -> str:
        chamadas_embeddings = self.chamadas_mcp
        total_requisicoes = self.chamadas_llm + chamadas_embeddings
        linhas = [
            "\n" + "=" * 55,
            "[RELATORIO DE CONSUMO DE API]",
            "=" * 55,
            f"- Chamadas LLM Chat (Gemini)        : {self.chamadas_llm}",
            f"- Chamadas Embeddings (MCP / Gemini) : {chamadas_embeddings}",
            f"- Total de Requisicoes de IA         : {total_requisicoes}",
        ]
        if self.total_tokens > 0:
            linhas.append(
                f"- Tokens (Prompt / Resposta / Total) : {self.input_tokens} / {self.output_tokens} / {self.total_tokens}"
            )
        linhas.append("=" * 55)
        return "\n".join(linhas)


# 2. ESTADO DO GRAFO
class EstadoCoordenador(TypedDict):
    role: str
    messages: Annotated[Sequence[BaseMessage], add_messages]
    proximo_passo: str
    query_atual: str


# Inicializa o LLM com retentativas automáticas em caso de picos de demanda (HTTP 503 / 429)
# Usa gemini-flash-lite-latest (versão otimizada, rápida e com cota ativa disponível)
MODELO_LLM = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")

llm = ChatGoogleGenerativeAI(
    model=MODELO_LLM,
    temperature=0,
    api_key=chave_gemini(),
    max_retries=5,
)


# 2. DEFINIÇÃO DA ESTRUTURA DE DECISÃO DO SUPERVISOR
class DecisaoSupervisor(BaseModel):
    proximo_passo: Literal["pesquisador", "redator"] = Field(
        description="Escolha 'pesquisador' se precisar buscar informações na empresa. Escolha 'redator' se for uma pergunta genérica que não exige consulta."
    )
    query_pesquisa: str = Field(
        default="",
        description="Se for pesquisar, formule a frase de busca exata baseada na pergunta do usuário."
    )

# 3. OS TRÊS NÓS DA ARQUITETURA

def supervisor_node(state: EstadoCoordenador):
    print("\n[Supervisor] Pensando...")
    messages = state["messages"]
    
    # Forçamos o LLM a responder seguindo a estrutura de decisão
    llm_estruturado = llm.with_structured_output(DecisaoSupervisor)
    
    instrucao = SystemMessage(
        content="Você é o Supervisor do sistema. Decida se é necessário acionar a busca corporativa ou responder diretamente."
    )
    
    # Invocamos o LLM passando a instrução e as mensagens
    decisao = llm_estruturado.invoke([instrucao] + messages)
    
    if decisao.proximo_passo == "pesquisador":
        print(f"[Supervisor] Decidiu buscar: '{decisao.query_pesquisa}'")
        return {"proximo_passo": "pesquisador", "query_atual": decisao.query_pesquisa}
    else:
        print("[Supervisor] Decidiu responder direto (sem busca).")
        return {"proximo_passo": "redator", "query_atual": ""}

def pesquisador_node(state: EstadoCoordenador):
    query = state.get("query_atual", "")
    role = state["role"]
    print(f"[Pesquisador] Buscando dados como '{role}'...")
    
    # ATENÇÃO À REGRA DE OURO: A ferramenta é invocada usando a role que veio do Estado,
    # não é o LLM que escolhe a permissão, somos nós!
    resultado = ferramenta_busca_corporativa.invoke({"query": query, "role": role})
    
    # Guardamos o resultado da pesquisa como uma mensagem do sistema para o redator ler
    mensagem_pesquisa = SystemMessage(content=f"DADOS RETORNADOS DO MCP: {resultado}")
    
    return {"messages": [mensagem_pesquisa]}

def _extrair_texto(mensagem) -> str:
    """Extrai o texto legível da mensagem, seja ela string ou lista de blocos estruturados."""
    if hasattr(mensagem, "text") and mensagem.text:
        return mensagem.text
    conteudo = getattr(mensagem, "content", "")
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        partes = [b.get("text", "") for b in conteudo if isinstance(b, dict) and "text" in b]
        return "\n".join(partes) if partes else str(conteudo)
    return str(conteudo)


def redator_node(state: EstadoCoordenador):
    print("[Redator] Escrevendo resposta final...")
    
    instrucao = SystemMessage(
        content="Você é o redator final da empresa. Responda o usuário de forma formal e educada. "
                "Baseie-se ESTRITAMENTE nos 'DADOS RETORNADOS DO MCP' presentes no histórico. "
                "Se os dados do MCP indicarem 'Nenhum documento encontrado' ou ausência de registros autorizados, "
                "informe ao usuário de maneira formal que não constam informações sobre este tema "
                "disponíveis para consulta no seu perfil de acesso. "
                "Nunca invente informações nem cite assuntos desconexos."
    )
    
    resposta = llm.invoke([instrucao] + state["messages"])
    
    texto_resposta = _extrair_texto(resposta)
    print(f"\n--- [Resposta do Redator] ---\n{texto_resposta}\n")
    
    return {"messages": [resposta]}


# 4. ROTEAMENTO
def roteamento_supervisor(state: EstadoCoordenador):
    """Lê o estado e diz para qual nó ir a seguir."""
    return state.get("proximo_passo", "redator")


# 5. MONTAGEM DO GRAFO
workflow = StateGraph(EstadoCoordenador)

# Adiciona os nós (quem faz o trabalho)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("pesquisador", pesquisador_node)
workflow.add_node("redator", redator_node)

# Define o fluxo (as setas do diagrama)
workflow.add_edge(START, "supervisor")

workflow.add_conditional_edges(
    "supervisor",
    roteamento_supervisor,
    {
        "pesquisador": "pesquisador",
        "redator": "redator"
    }
)

workflow.add_edge("pesquisador", "redator")
workflow.add_edge("redator", END)

# Compila o grafo para uso
grafo_coordenador = workflow.compile()


def executar_coordenador(pergunta: str, role: str = "geral", exibir_metricas: bool = True) -> str:
    """Executa o fluxo completo do Coordenador de ponta a ponta com LLM e MCP reais.
    
    Rastreia e exibe as métricas de chamadas à API e consumo de tokens.
    Retorna a resposta textual final gerada pelo nó redator.
    """
    monitor = MonitorAPI()
    estado_inicial: EstadoCoordenador = {
        "role": role,
        "messages": [HumanMessage(content=pergunta)],
        "proximo_passo": "",
        "query_atual": "",
    }
    
    resultado = grafo_coordenador.invoke(estado_inicial, config={"callbacks": [monitor]})
    
    if exibir_metricas:
        print(monitor.relatorio())
        
    ultima_mensagem = resultado["messages"][-1]
    return _extrair_texto(ultima_mensagem)


if __name__ == "__main__":
    print("=" * 60)
    print("AGENTE COORDENADOR (Execução Real: LangGraph + MCP + Supabase)")
    print("=" * 60)
    
    pergunta_exemplo = "Qual o orçamento do projeto secreto?"
    
    print(f"\nPergunta: '{pergunta_exemplo}'\n")
    
    print("-" * 30 + " CENÁRIO 1: GERAL " + "-" * 30)
    resposta_g = executar_coordenador(pergunta_exemplo, role="geral")
    print(f"\n[Resposta Final (Geral)]:\n{resposta_g}\n")
    
    print("-" * 30 + " CENÁRIO 2: DIRETORIA " + "-" * 30)
    resposta_d = executar_coordenador(pergunta_exemplo, role="diretoria")
    print(f"\n[Resposta Final (Diretoria)]:\n{resposta_d}\n")
