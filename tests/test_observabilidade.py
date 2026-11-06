"""Testes automatizados da camada de Observabilidade, Telemetria e FinOps (Etapa 4.1).

Valida:
1. Precisão dos cálculos de custos (FinOps) em USD e BRL.
2. Criação das tabelas e índices no SQLite.
3. Ciclo de vida de TraceContexto, spans e persistência.
4. Propagação assíncrona do trace atual via ContextVar.
5. Agregações estatísticas para o Dashboard de LLMOps.
6. Integração do Coordenador com gravação de telemetria sem rede.
"""

from pathlib import Path
import sqlite3
import pytest

from src.observabilidade.custos import (
    calcular_custo_execucao,
    TABELA_PRECOS_GEMINI,
    TAXA_CAMBIO_USD_BRL_PADRAO,
)
from src.observabilidade.telemetria import (
    inicializar_banco,
    iniciar_rastreamento,
    obter_trace_atual,
    listar_execucoes,
    obter_resumo_estatistico,
    obter_evidencias_execucao,
)


def test_calculo_custo_finops_gemini_flash_lite():
    # 1.000.000 de tokens input = $0.075; 1.000.000 tokens output = $0.30
    estimativa = calcular_custo_execucao(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        modelo="gemini-flash-lite-latest",
        taxa_cambio_usd_brl=5.0,
    )
    assert estimativa["custo_input_usd"] == pytest.approx(0.075)
    assert estimativa["custo_output_usd"] == pytest.approx(0.30)
    assert estimativa["custo_total_usd"] == pytest.approx(0.375)
    assert estimativa["custo_total_brl"] == pytest.approx(1.875)
    assert estimativa["total_tokens"] == 2_000_000


def test_calculo_custo_modelo_desconhecido_usa_fallback():
    estimativa = calcular_custo_execucao(
        input_tokens=1000,
        output_tokens=500,
        modelo="modelo-experimental-novo-99",
    )
    assert estimativa["custo_total_usd"] > 0.0
    assert estimativa["total_tokens"] == 1500


def test_inicializar_banco_cria_esquema_sqlite(tmp_path: Path):
    caminho_db = tmp_path / "teste_telemetria.db"
    retornado = inicializar_banco(caminho_db)
    assert retornado == caminho_db
    assert caminho_db.exists()

    with sqlite3.connect(caminho_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = {linha[0] for linha in cursor.fetchall()}
        assert "execucoes" in tabelas
        assert "spans" in tabelas


def test_ciclo_de_vida_trace_e_persistencia(tmp_path: Path):
    caminho_db = tmp_path / "telemetria_ciclo.db"

    assert obter_trace_atual() is None

    with iniciar_rastreamento(
        padrao="coordenador",
        pergunta="Qual o cardapio da feijoada?",
        papel="geral",
        run_id="run_teste_001",
        caminho_banco=caminho_db,
    ) as trace:
        assert obter_trace_atual() is trace
        assert trace.run_id == "run_teste_001"

        with trace.span("consulta_mcp", tipo="tool_mcp", detalhes={"query": "feijoada"}):
            trace.registrar_chamada_mcp(1)

        trace.registrar_chamada_llm(2)
        trace.registrar_tokens(input_tokens=150, output_tokens=50)
        trace.definir_resposta("A feijoada ocorre todas as sextas-feiras.")

    # Fora do with, o trace atual deve ser resetado
    assert obter_trace_atual() is None

    # Verifica os dados gravados no SQLite
    with sqlite3.connect(caminho_db) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM execucoes WHERE run_id = ?", ("run_teste_001",))
        linha = cursor.fetchone()
        assert linha is not None
        assert linha["padrao_arquitetural"] == "coordenador"
        assert linha["pergunta"] == "Qual o cardapio da feijoada?"
        assert linha["papel_usuario"] == "geral"
        assert linha["resposta_final"] == "A feijoada ocorre todas as sextas-feiras."
        assert linha["chamadas_mcp"] == 1
        assert linha["chamadas_llm"] == 2
        assert linha["total_tokens"] == 200
        assert linha["latencia_total_ms"] >= 0.0
        assert linha["custo_usd"] > 0.0
        assert linha["sucesso"] == 1

        # Verifica span registrado
        cursor.execute("SELECT * FROM spans WHERE run_id = ?", ("run_teste_001",))
        spans = cursor.fetchall()
        assert len(spans) == 1
        assert spans[0]["nome_span"] == "consulta_mcp"
        assert spans[0]["tipo"] == "tool_mcp"


def test_consultas_analiticas_dashboard(tmp_path: Path):
    caminho_db = tmp_path / "dashboard_teste.db"

    # Simula 2 execuções do Coordenador e 1 do Plano-Executor
    with iniciar_rastreamento("coordenador", "P1", "geral", "run_1", caminho_db) as t1:
        t1.registrar_tokens(100, 50)
        t1.definir_resposta("R1")

    with iniciar_rastreamento("coordenador", "P2", "diretoria", "run_2", caminho_db) as t2:
        t2.registrar_tokens(200, 100)
        t2.definir_resposta("R2")

    with iniciar_rastreamento("plano_executor", "P3", "geral", "run_3", caminho_db) as t3:
        t3.registrar_tokens(400, 200)
        t3.definir_resposta("R3")

    execucoes = listar_execucoes(caminho_banco=caminho_db)
    assert len(execucoes) == 3

    resumo = obter_resumo_estatistico(caminho_banco=caminho_db)
    assert "coordenador" in resumo
    assert "plano_executor" in resumo
    assert resumo["coordenador"]["total_execucoes"] == 2
    assert resumo["plano_executor"]["total_execucoes"] == 1
    assert resumo["coordenador"]["tokens_medios"] == pytest.approx(225.0)  # (150 + 300) / 2


def test_rastreamento_e_recuperacao_evidencias_mcp(tmp_path: Path):
    """Garante que o contexto MCP registrado no trace é persistido e recuperado para o Juiz LLM (D-024)."""
    caminho_db = tmp_path / "evidencias_teste.db"

    with iniciar_rastreamento("coordenador", "Qual o cardápio?", "geral", "run_ev_01", caminho_db) as t:
        t.registrar_evidencia_mcp("Documento encontrado: Cardápio de segunda tem feijoada.")
        t.definir_resposta("Temos feijoada na segunda.")

    evidencia_recuperada = obter_evidencias_execucao("run_ev_01", caminho_banco=caminho_db)
    assert "Cardápio de segunda tem feijoada" in evidencia_recuperada


def test_custo_contabiliza_chamadas_embedding():
    """Garante que chamadas de embedding somam ao custo total quando informadas (D-024)."""
    sem_emb = calcular_custo_execucao(1000, 500, chamadas_embedding=0)
    com_emb = calcular_custo_execucao(1000, 500, chamadas_embedding=3)
    assert com_emb["custo_total_usd"] > sem_emb["custo_total_usd"]


def test_get_embedding_respeita_task_type_assimetrico(monkeypatch):
    """Verifica que get_embedding repassa task_type ('retrieval_query' vs 'retrieval_document') ao SDK google-genai (D-024)."""
    from src.busca import embeddings

    configs_recebidos = []

    class _FakeEmbedding:
        values = [0.25] * 3072

    class _FakeResult:
        embeddings = [_FakeEmbedding()]

    class _FakeModels:
        def embed_content(self, *, model, contents, config):
            configs_recebidos.append((model, contents, config.task_type))
            return _FakeResult()

    class _FakeClient:
        models = _FakeModels()

    monkeypatch.setattr(embeddings, "_obter_cliente", lambda: _FakeClient())

    vetor_q = embeddings.get_embedding("Qual o orçamento?", task_type="retrieval_query")
    vetor_d = embeddings.get_embedding("Texto do documento", task_type="retrieval_document")

    assert len(vetor_q) == 3072
    assert len(vetor_d) == 3072
    assert configs_recebidos[0] == ("models/gemini-embedding-2", "Qual o orçamento?", "retrieval_query")
    assert configs_recebidos[1] == ("models/gemini-embedding-2", "Texto do documento", "retrieval_document")


def test_coordenador_validador_node_bloqueia_vazamento():
    """Garante que o validador_node do Coordenador retém qualquer segredo proibido para o perfil (D-025)."""
    from langchain_core.messages import AIMessage, HumanMessage
    from src.agentes.coordenador import validador_node

    estado_vazado = {
        "role": "geral",
        "messages": [
            HumanMessage(content="Qual o orçamento?"),
            AIMessage(content="O orçamento do Projeto Secreto é de 50 milhões."),
        ],
        "proximo_passo": "redator",
        "query_atual": "",
    }
    atualizacao = validador_node(estado_vazado)
    assert "messages" in atualizacao
    nova_msg = atualizacao["messages"][-1].content
    assert "50 milhões" not in nova_msg
    assert "não constam" in nova_msg.lower()


def test_plano_executor_replanejamento_limitado_em_falha_transitoria():
    """Garante que avaliador_execucao_node e rotear_apos_avaliacao fazem no máximo 1 retry em falha MCP (D-025)."""
    from langgraph.types import Send
    from src.agentes.plano_executor import avaliador_execucao_node, rotear_apos_avaliacao

    estado_falha_1 = {
        "role": "geral",
        "pergunta": "Qual o cardápio?",
        "plano": [{"id": 1, "descricao": "Cardápio", "query_busca": "cardápio"}],
        "resultados": [
            {
                "id_tarefa": 1,
                "descricao": "Cardápio",
                "query_busca": "cardápio",
                "resultado_mcp": "Erro MCP: não foi possível consultar o servidor de documentos.",
            }
        ],
        "tentativas_replanejamento": 0,
    }

    delta = avaliador_execucao_node(estado_falha_1)
    assert delta["tentativas_replanejamento"] == 1

    estado_apos_avaliacao = {**estado_falha_1, **delta}
    rota = rotear_apos_avaliacao(estado_apos_avaliacao)
    assert isinstance(rota, list)
    assert len(rota) == 1
    assert isinstance(rota[0], Send)
    assert rota[0].node == "executor"

    # Na 2ª vez (após o limite MAX_REPLANEJAMENTOS = 1), encerra indo para 'sintetizador' sem loop infinito
    estado_apos_retry = {
        **estado_apos_avaliacao,
        "resultados": estado_falha_1["resultados"] * 2,
    }
    rota_final = rotear_apos_avaliacao(estado_apos_retry)
    assert rota_final == "sintetizador"


def test_citacao_estruturada_e_revogacao_documento(monkeypatch):
    """Valida formatação de citação completa (documento | versao | chunk) e função revogar_documento (D-025)."""
    from src.mcp.server import _formatar_citacao
    from src.ingestao import ingestao

    citacao_curta = _formatar_citacao("manual.md", "v1", 2, formato_curto=True)
    assert citacao_curta == " [manual.md | v1 | chunk 2]"

    citacao_longa = _formatar_citacao("manual.md", "v2", 1, formato_curto=False)
    assert citacao_longa == " (Origem: manual.md | v2 | chunk 1)"

    with pytest.raises(ValueError):
        ingestao.revogar_documento("   ")


