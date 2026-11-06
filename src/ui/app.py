"""Aplicação Web Unificada: Arena Comparativa Multiagente e Dashboard de LLMOps (Streamlit).

Modo Head-to-Head: submete uma pergunta aos três padrões arquiteturais simultaneamente
(Coordenador, Plano–Executor e Conversação em Grupo) e exibe todas as métricas comparativas
lado a lado em tempo real, conforme D-020 e D-021 em docs/decisions.md.

Uso:
    streamlit run src/ui/app.py
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Garante inclusão da raiz do projeto no PYTHONPATH
RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.agentes.coordenador import executar_coordenador
from src.agentes.plano_executor import executar_plano_executor
from src.agentes.conversa_grupo import executar_conversa_grupo
from src.observabilidade.telemetria import (
    inicializar_banco,
    listar_execucoes,
    obter_resumo_estatistico,
    obter_metricas_qualidade,
    CAMINHO_BANCO_PADRAO,
    listar_avaliacoes,
    obter_evidencias_execucao,
)
from src.observabilidade.avaliador import avaliar_execucao, obter_termos_proibidos_por_papel

# ----------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Arena Multiagente & LLMOps — UNICAMP",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inicializa o banco local
inicializar_banco()


# ----------------------------------------------------------------------
# 2. BARRA LATERAL (SIDEBAR)
# ----------------------------------------------------------------------
with st.sidebar:
    st.title("🎓 UNICAMP")
    st.markdown("### **Engenharia de Software para IA**")
    st.caption("Comparação Empírica de Padrões Multiagentes (MCP & LLMOps)")
    
    st.divider()
    st.markdown("#### ⚙️ Status da Infraestrutura")
    
    resumo_op = obter_resumo_estatistico()
    total_exec = sum(d.get("total_execucoes", 0) for d in resumo_op.values()) if resumo_op else 0
    
    st.success("🟢 Servidor MCP (stdio): Ativo")
    st.info("☁️ Banco Vetorial: Supabase + pgvector")
    st.metric("Consultas Reais Coletadas", total_exec)
    
    st.divider()
    st.markdown("#### 🔬 Padrões Avaliados")
    st.markdown("""
    - **1. Coordenador**: Roteamento supervisor/redator via *LangGraph*.
    - **2. Plano–Executor**: Decomposição em tarefas concorrentes via *LangGraph*.
    - **3. Conversação em Grupo**: Três agentes em debate *Round-Robin* via *AutoGen 0.4*.
    """)
    
    st.divider()
    st.caption("Fase 4 & 5 — Observabilidade, FinOps e Evals")


# ----------------------------------------------------------------------
# 3. ABAS PRINCIPAIS
# ----------------------------------------------------------------------
tab_arena, tab_dashboard, tab_auditoria = st.tabs([
    "⚖️ Arena Comparativa (Head-to-Head)",
    "📊 Dashboard Consolidado",
    "🔬 Inspeção de Spans & Auditoria",
])


# ======================================================================
# ABA 1: ARENA COMPARATIVA (EXECUÇÃO SIMULTÂNEA DOS 3 AGENTES)
# ======================================================================
with tab_arena:
    st.header("Arena Comparativa de Agentes em Tempo Real")
    st.markdown(
        "Submeta uma pergunta corporativa e veja os **três padrões arquiteturais responderem lado a lado**, "
        "com comparação instantânea de latência, consumo de tokens, custos financeiros e conformidade de acesso."
    )

    # Configuração de Perfil de Acesso (RBAC)
    col_perfil, col_vazio = st.columns([2, 1])
    with col_perfil:
        rotulos_perfis = {
            "geral": "👤 Geral (Acesso Padrão)",
            "rh": "🏢 RH (Recursos Humanos)",
            "diretoria": "🔑 Diretoria (Acesso Confidencial)",
        }
        papel_selecionado = st.radio(
            "Selecione o Perfil de Autorização do Usuário (RBAC):",
            options=["geral", "rh", "diretoria"],
            horizontal=True,
            format_func=lambda x: rotulos_perfis.get(x, x),
        )

    # Perguntas rápidas pré-configuradas para demonstração
    st.markdown("**Perguntas sugeridas para teste comparativo:**")
    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
    pergunta_clicada = None
    if btn_col1.button("🍽️ Cardápio Refeitório (Público)"):
        pergunta_clicada = "Qual é o cardápio do refeitório servido na segunda-feira?"
    if btn_col2.button("🔒 Orçamento Secreto (Diretoria)"):
        pergunta_clicada = "Qual é o orçamento previsto para o Projeto Ultra-Secreto X em 2027?"
    if btn_col3.button("⏰ Jornada de Trabalho (Público)"):
        pergunta_clicada = "Qual é a jornada de trabalho padrão e os horários da empresa?"
    if btn_col4.button("🚫 Curso no Exterior (Fora do Corpus)"):
        pergunta_clicada = "Qual é a política de reembolso para cursos de pós-graduação e MBA no exterior?"

    # Entrada de texto do usuário
    entrada_usuario = st.chat_input("Digite sua pergunta corporativa para submeter aos 3 agentes simultaneamente...")
    prompt_atual = pergunta_clicada or entrada_usuario

    if "ultima_rodada" not in st.session_state:
        st.session_state.ultima_rodada = None

    if prompt_atual:
        status_container = st.status("🚀 Iniciando execução comparativa nos 3 padrões...", expanded=True)
        resultados_rodada = {}

        # 1. Executa o Coordenador
        status_container.write("⏳ Executando Padrão 1: **Coordenador (LangGraph)**...")
        t0 = time.perf_counter()
        ts = datetime.now(timezone.utc).strftime("%H%M%S")
        run_coord = f"arena_coord_{ts}"
        try:
            resp_coord = executar_coordenador(prompt_atual, role=papel_selecionado, exibir_metricas=False, run_id=run_coord)
            lat_coord = time.perf_counter() - t0
            ctx_coord = obter_evidencias_execucao(run_coord)
            eval_coord = avaliar_execucao(
                run_id=run_coord,
                pergunta=prompt_atual,
                resposta=resp_coord,
                contexto_mcp=ctx_coord,
                papel_usuario=papel_selecionado,
                termos_proibidos=obter_termos_proibidos_por_papel(papel_selecionado),
                juiz_llm="deterministico",
                salvar_no_banco=True,
            )
            resultados_rodada["coordenador"] = {
                "resposta": resp_coord,
                "latencia_s": round(lat_coord, 2),
                "run_id": run_coord,
                "sucesso": True,
                "rbac_ok": not eval_coord.falha_seguranca,
                "alucinacao": eval_coord.houve_alucinacao,
                "fidelidade": eval_coord.fidelidade_score,
            }
        except Exception as err:
            resultados_rodada["coordenador"] = {"erro": str(err), "sucesso": False, "latencia_s": 0}

        # 2. Executa o Plano-Executor
        status_container.write("⏳ Executando Padrão 2: **Plano–Executor (LangGraph Fan-Out)**...")
        t0 = time.perf_counter()
        ts = datetime.now(timezone.utc).strftime("%H%M%S")
        run_plano = f"arena_plano_{ts}"
        try:
            resp_plano = executar_plano_executor(prompt_atual, role=papel_selecionado, exibir_metricas=False, run_id=run_plano)
            lat_plano = time.perf_counter() - t0
            ctx_plano = obter_evidencias_execucao(run_plano)
            eval_plano = avaliar_execucao(
                run_id=run_plano,
                pergunta=prompt_atual,
                resposta=resp_plano,
                contexto_mcp=ctx_plano,
                papel_usuario=papel_selecionado,
                termos_proibidos=obter_termos_proibidos_por_papel(papel_selecionado),
                juiz_llm="deterministico",
                salvar_no_banco=True,
            )
            resultados_rodada["plano_executor"] = {
                "resposta": resp_plano,
                "latencia_s": round(lat_plano, 2),
                "run_id": run_plano,
                "sucesso": True,
                "rbac_ok": not eval_plano.falha_seguranca,
                "alucinacao": eval_plano.houve_alucinacao,
                "fidelidade": eval_plano.fidelidade_score,
            }
        except Exception as err:
            resultados_rodada["plano_executor"] = {"erro": str(err), "sucesso": False, "latencia_s": 0}

        # 3. Executa a Conversação em Grupo
        status_container.write("⏳ Executando Padrão 3: **Conversação em Grupo (AutoGen 0.4 Round-Robin)**...")
        t0 = time.perf_counter()
        ts = datetime.now(timezone.utc).strftime("%H%M%S")
        run_grupo = f"arena_grupo_{ts}"
        try:
            res_grupo = executar_conversa_grupo(prompt_atual, papel=papel_selecionado, max_mensagens=9, run_id=run_grupo)
            resp_grupo = res_grupo.get("resposta_final", "")
            lat_grupo = time.perf_counter() - t0
            ctx_grupo = obter_evidencias_execucao(run_grupo)
            eval_grupo = avaliar_execucao(
                run_id=run_grupo,
                pergunta=prompt_atual,
                resposta=resp_grupo,
                contexto_mcp=ctx_grupo,
                papel_usuario=papel_selecionado,
                termos_proibidos=obter_termos_proibidos_por_papel(papel_selecionado),
                juiz_llm="deterministico",
                salvar_no_banco=True,
            )
            resultados_rodada["conversa_grupo"] = {
                "resposta": resp_grupo,
                "latencia_s": round(lat_grupo, 2),
                "run_id": run_grupo,
                "sucesso": True,
                "rbac_ok": not eval_grupo.falha_seguranca,
                "alucinacao": eval_grupo.houve_alucinacao,
                "fidelidade": eval_grupo.fidelidade_score,
                "turnos": res_grupo.get("turnos", 0),
            }
        except Exception as err:
            resultados_rodada["conversa_grupo"] = {"erro": str(err), "sucesso": False, "latencia_s": 0}

        # Atualiza métricas detalhadas a partir do SQLite
        execucoes_db = {e["run_id"]: e for e in listar_execucoes(limite=20)}
        for padrao, dados in resultados_rodada.items():
            if dados.get("sucesso"):
                rid = dados.get("run_id")
                if rid in execucoes_db:
                    row = execucoes_db[rid]
                    dados["tokens"] = row["total_tokens"]
                    dados["custo_brl"] = row["custo_brl"]
                    dados["chamadas_mcp"] = row["chamadas_mcp"]
                    dados["chamadas_llm"] = row["chamadas_llm"]

        status_container.update(label="✅ Execução comparativa concluída com sucesso nos 3 agentes!", state="complete", expanded=False)

        st.session_state.ultima_rodada = {
            "pergunta": prompt_atual,
            "papel": papel_selecionado,
            "resultados": resultados_rodada,
        }

    # Renderiza os resultados da última rodada submetida
    if st.session_state.ultima_rodada:
        rodada = st.session_state.ultima_rodada
        st.divider()
        st.markdown(f"### 🎯 Pergunta Avaliada: *\"{rodada['pergunta']}\"*")
        st.caption(f"Perfil de Acesso Utilizado: **{rodada['papel'].upper()}**")

        res = rodada["resultados"]
        c1, c2, c3 = st.columns(3)

        # Coluna 1: Coordenador
        with c1:
            st.subheader("👔 1. Coordenador")
            st.caption("LangGraph • Roteamento Sequencial")
            d_c = res.get("coordenador", {})
            if d_c.get("sucesso"):
                st.metric("⏱️ Latência", f"{d_c.get('latencia_s', 0):.2f} s")
                k1, k2 = st.columns(2)
                k1.metric("Tokens", f"{d_c.get('tokens', 0):,}")
                k2.metric("Custo", f"R$ {d_c.get('custo_brl', 0):.4f}")
                
                status_rbac = "✅ RBAC OK" if d_c.get("rbac_ok") else "🚨 VAZAMENTO"
                st.info(f"**Segurança:** {status_rbac}")
                with st.expander("📄 Ver Resposta Completa", expanded=True):
                    st.write(d_c.get("resposta", ""))
            else:
                st.error(f"Falha na execução: {d_c.get('erro')}")

        # Coluna 2: Plano-Executor
        with c2:
            st.subheader("📋 2. Plano–Executor")
            st.caption("LangGraph • Tarefas Paralelas (Fan-Out)")
            d_p = res.get("plano_executor", {})
            if d_p.get("sucesso"):
                st.metric("⏱️ Latência", f"{d_p.get('latencia_s', 0):.2f} s")
                k1, k2 = st.columns(2)
                k1.metric("Tokens", f"{d_p.get('tokens', 0):,}")
                k2.metric("Custo", f"R$ {d_p.get('custo_brl', 0):.4f}")
                
                status_rbac = "✅ RBAC OK" if d_p.get("rbac_ok") else "🚨 VAZAMENTO"
                st.info(f"**Segurança:** {status_rbac}")
                with st.expander("📄 Ver Resposta Completa", expanded=True):
                    st.write(d_p.get("resposta", ""))
            else:
                st.error(f"Falha na execução: {d_p.get('erro')}")

        # Coluna 3: Conversação em Grupo
        with c3:
            st.subheader("💬 3. Conversa em Grupo")
            st.caption("AutoGen 0.4 • Debate Round-Robin")
            d_g = res.get("conversa_grupo", {})
            if d_g.get("sucesso"):
                st.metric("⏱️ Latência", f"{d_g.get('latencia_s', 0):.2f} s")
                k1, k2 = st.columns(2)
                k1.metric("Tokens", f"{d_g.get('tokens', 0):,}")
                k2.metric("Custo", f"R$ {d_g.get('custo_brl', 0):.4f}")
                
                status_rbac = "✅ RBAC OK" if d_g.get("rbac_ok") else "🚨 VAZAMENTO"
                st.info(f"**Segurança:** {status_rbac} ({d_g.get('turnos', 0)} turnos)")
                with st.expander("📄 Ver Resposta Completa", expanded=True):
                    st.write(d_g.get("resposta", ""))
            else:
                st.error(f"Falha na execução: {d_g.get('erro')}")

        # Gráficos da rodada atual
        st.divider()
        st.markdown("#### 📊 Comparativo Imediato da Rodada")
        
        dados_rodada = []
        for p_nome, rotulo in [("coordenador", "Coordenador"), ("plano_executor", "Plano-Executor"), ("conversa_grupo", "Conversa Grupo")]:
            dados = res.get(p_nome, {})
            if dados.get("sucesso"):
                dados_rodada.append({
                    "Padrão": rotulo,
                    "Latência (s)": dados.get("latencia_s", 0),
                    "Tokens": dados.get("tokens", 0),
                    "Custo (BRL)": dados.get("custo_brl", 0),
                })

        if dados_rodada:
            df_rodada = pd.DataFrame(dados_rodada)
            g1, g2, g3 = st.columns(3)
            with g1:
                fig1 = px.bar(df_rodada, x="Padrão", y="Latência (s)", text="Latência (s)", title="⏱️ Latência da Rodada (s)", color="Padrão")
                fig1.update_traces(textposition="outside")
                st.plotly_chart(fig1, use_container_width=True)
            with g2:
                fig2 = px.bar(df_rodada, x="Padrão", y="Tokens", text="Tokens", title="🪙 Consumo de Tokens", color="Padrão")
                fig2.update_traces(textposition="outside")
                st.plotly_chart(fig2, use_container_width=True)
            with g3:
                fig3 = px.bar(df_rodada, x="Padrão", y="Custo (BRL)", text="Custo (BRL)", title="💰 Custo Financeiro (R$)", color="Padrão")
                fig3.update_traces(texttemplate="R$ %{text:.4f}", textposition="outside")
                st.plotly_chart(fig3, use_container_width=True)


# ======================================================================
# ABA 2: DASHBOARD DE LLMOPS (CONSOLIDADO HISTÓRICO)
# ======================================================================
with tab_dashboard:
    col_tit, col_rec = st.columns([4, 1])
    with col_tit:
        st.header("Dashboard Consolidado de LLMOps")
        st.caption("Visão agregada de todas as perguntas reais submetidas aos agentes.")
    with col_rec:
        if st.button("🔄 Atualizar Métricas"):
            st.rerun()

    resumo_op = obter_resumo_estatistico()
    resumo_qual = obter_metricas_qualidade()

    if not resumo_op:
        st.warning("Nenhuma execução real registrada ainda. Submeta uma pergunta na aba 'Arena Comparativa' ou rode a CLI de benchmark.")
    else:
        # KPIs no Topo
        total_consultas = sum(d.get("total_execucoes", 0) for d in resumo_op.values())
        custo_acumulado_brl = sum(d.get("custo_total_brl", 0) for d in resumo_op.values())
        latencia_global = (
            sum(d.get("latencia_media_ms", 0) * d.get("total_execucoes", 0) for d in resumo_op.values())
            / total_consultas
            if total_consultas > 0 else 0
        )
        total_evals = sum(q.get("total_avaliacoes", 0) for q in resumo_qual.values())
        rbac_global = (
            sum(q.get("rbac_conformidade_media", 1.0) * q.get("total_avaliacoes", 0) for q in resumo_qual.values())
            / total_evals
            if total_evals > 0 else 1.0
        )

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total de Execuções Coletadas", f"{total_consultas}")
        kpi2.metric("Latência Média Geral", f"{latencia_global / 1000.0:.2f} s")
        kpi3.metric("Custo Acumulado (FinOps)", f"R$ {custo_acumulado_brl:.4f}")
        kpi4.metric("Conformidade RBAC Global", f"{rbac_global * 100:.1f}%")

        st.divider()

        # Monta DataFrame para os gráficos
        dados_grafico = []
        for padrao, op in resumo_op.items():
            qual = resumo_qual.get(padrao, {})
            dados_grafico.append({
                "Padrão": padrao.replace("_", " ").title(),
                "Latência Média (s)": round(op.get("latencia_media_ms", 0) / 1000.0, 2),
                "Tokens Médios": int(op.get("tokens_medios", 0)),
                "Custo Total (BRL)": round(op.get("custo_total_brl", 0), 4),
                "Total Execuções": op.get("total_execucoes", 0),
                "Fidelidade (%)": round(qual.get("fidelidade_media", 0.0) * 100, 1),
                "Taxa Alucinação (%)": round(qual.get("taxa_alucinacao", 0.0) * 100, 1),
                "Conformidade RBAC (%)": round(qual.get("rbac_conformidade_media", 1.0) * 100, 1),
            })

        df_metricas = pd.DataFrame(dados_grafico)

        # Quatro Gráficos Plotly Comparativos
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            fig_lat = px.bar(
                df_metricas,
                x="Padrão",
                y="Latência Média (s)",
                text="Latência Média (s)",
                title="⏱️ Comparativo Histórico de Latência Média (s)",
                color="Padrão",
            )
            fig_lat.update_traces(textposition="outside")
            st.plotly_chart(fig_lat, use_container_width=True)

        with g_col2:
            fig_fin = px.bar(
                df_metricas,
                x="Padrão",
                y="Tokens Médios",
                text="Tokens Médios",
                title="🪙 Consumo Médio de Tokens por Consulta",
                color="Padrão",
            )
            fig_fin.update_traces(textposition="outside")
            st.plotly_chart(fig_fin, use_container_width=True)

        g_col3, g_col4 = st.columns(2)
        with g_col3:
            fig_qual = px.bar(
                df_metricas,
                x="Padrão",
                y=["Fidelidade (%)", "Taxa Alucinação (%)"],
                barmode="group",
                title="🎯 Qualidade Semântica: Fidelidade vs. Alucinação",
                color_discrete_map={"Fidelidade (%)": "#2ca02c", "Taxa Alucinação (%)": "#d62728"},
            )
            st.plotly_chart(fig_qual, use_container_width=True)

        with g_col4:
            fig_rbac = px.bar(
                df_metricas,
                x="Padrão",
                y="Conformidade RBAC (%)",
                text="Conformidade RBAC (%)",
                title="🛡️ Taxa de Conformidade de Isolamento RBAC (%)",
                color="Padrão",
            )
            fig_rbac.update_traces(textposition="outside")
            fig_rbac.update_yaxes(range=[0, 115])
            st.plotly_chart(fig_rbac, use_container_width=True)

        st.markdown("#### 📋 Matriz Comparativa Consolidada")
        st.dataframe(df_metricas, use_container_width=True, hide_index=True)


# ======================================================================
# ABA 3: AUDITORIA & SPANS (INSPEÇÃO PROFUNDA)
# ======================================================================
with tab_auditoria:
    st.header("Inspeção de Spans e Auditoria de Execuções")
    st.markdown("Visualize o histórico individual de chamadas, tempos por nó e consultas ao servidor MCP.")

    todas_execucoes = [e for e in listar_execucoes(limite=50) if "simulada" not in str(e.get("resposta_final", ""))]

    if not todas_execucoes:
        st.info("Nenhuma execução real disponível para auditoria.")
    else:
        df_todas = pd.DataFrame(todas_execucoes)
        col_exibir = [
            "run_id", "padrao_arquitetural", "pergunta", "papel_usuario",
            "latencia_total_ms", "total_tokens", "custo_brl", "sucesso", "timestamp_inicio"
        ]
        col_existentes = [c for c in col_exibir if c in df_todas.columns]

        st.dataframe(df_todas[col_existentes], use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### 🔍 Investigador de Spans por `run_id`")
        
        opcoes_runs = [e["run_id"] for e in todas_execucoes]
        run_selecionado = st.selectbox("Selecione uma execução para ver a árvore de spans:", options=opcoes_runs)

        if run_selecionado:
            with sqlite3.connect(CAMINHO_BANCO_PADRAO) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT * FROM spans WHERE run_id = ? ORDER BY timestamp_inicio ASC", (run_selecionado,))
                spans_linhas = [dict(r) for r in c.fetchall()]

            if not spans_linhas:
                st.caption("Nenhum sub-span específico registrado para esta execução.")
            else:
                df_spans = pd.DataFrame(spans_linhas)
                st.dataframe(df_spans[["span_id", "nome_span", "tipo", "duracao_ms", "timestamp_inicio"]], use_container_width=True, hide_index=True)
                
                fig_spans = px.bar(
                    df_spans,
                    x="duracao_ms",
                    y="nome_span",
                    orientation="h",
                    title=f"Tempo Gasto por Etapa / Nó (ms) — {run_selecionado}",
                    labels={"duracao_ms": "Duração (ms)", "nome_span": "Etapa / Nó"},
                    color="tipo",
                )
                st.plotly_chart(fig_spans, use_container_width=True)
