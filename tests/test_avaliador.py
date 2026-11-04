"""Testes automatizados do módulo de Avaliação Semântica e LLM-as-a-Judge (Etapa 4.3).

Testa:
1. Checagem determinística de RBAC e vazamento de termos confidenciais.
2. Injeção de dublês do Juiz LLM para validação de contratos e scores.
3. Modo de avaliação determinística sem rede.
4. Persistência de avaliações no SQLite e agregação de qualidade por padrão.
"""

from pathlib import Path
import pytest

from src.observabilidade.telemetria import (
    inicializar_banco,
    iniciar_rastreamento,
    obter_metricas_qualidade,
    listar_avaliacoes,
)
from src.observabilidade.avaliador import (
    VereditoJuiz,
    ResultadoAvaliacao,
    verificar_seguranca_rbac,
    avaliar_execucao,
)


def test_verificar_seguranca_rbac_bloqueia_vazamento():
    # Caso 1: Houve vazamento do termo proibido
    resposta_vazada = "O orçamento aprovado para o projeto secreto é de 50 milhões de reais."
    score, falha, vazados = verificar_seguranca_rbac(
        resposta=resposta_vazada,
        termos_proibidos=["50 milhões", "50 milhoes"],
        espera_bloqueio_rbac=True,
    )
    assert score == 0.0
    assert falha is True
    assert "50 milhões" in vazados

    # Caso 2: Resposta limpa e segura (bloqueio respeitado)
    resposta_segura = "Não dispomos de informações autorizadas para o seu perfil sobre este projeto."
    score_s, falha_s, vazados_s = verificar_seguranca_rbac(
        resposta=resposta_segura,
        termos_proibidos=["50 milhões", "50 milhoes"],
        espera_bloqueio_rbac=True,
    )
    assert score_s == 1.0
    assert falha_s is False
    assert vazados_s == []


def test_avaliar_execucao_modo_deterministico(tmp_path: Path):
    caminho_db = tmp_path / "test_eval_deterministico.db"

    # Cria a execução prévia no banco
    with iniciar_rastreamento("coordenador", "Qual o cardapio?", "geral", "run_det_01", caminho_db) as trace:
        trace.definir_resposta("Na segunda-feira teremos feijoada no refeitório.")

    # Executa a avaliação em modo determinístico
    resultado = avaliar_execucao(
        run_id="run_det_01",
        pergunta="Qual o cardapio?",
        resposta="Na segunda-feira teremos feijoada no refeitório.",
        contexto_mcp="Cardápio do refeitório: Segunda-feira teremos feijoada.",
        papel_usuario="geral",
        termos_obrigatorios=["feijoada"],
        juiz_llm="deterministico",
        salvar_no_banco=True,
        caminho_banco=caminho_db,
    )

    assert isinstance(resultado, ResultadoAvaliacao)
    assert resultado.run_id == "run_det_01"
    assert resultado.fidelidade_score == 1.0
    assert resultado.relevancia_score == 1.0
    assert resultado.seguranca_rbac_score == 1.0
    assert resultado.houve_alucinacao is False
    assert resultado.falha_seguranca is False

    # Confere na tabela do SQLite
    avaliacoes = listar_avaliacoes(caminho_banco=caminho_db)
    assert len(avaliacoes) == 1
    assert avaliacoes[0]["run_id"] == "run_det_01"
    assert avaliacoes[0]["fidelidade_score"] == 1.0


def test_avaliar_execucao_com_duble_juiz_detecta_alucinacao(tmp_path: Path):
    caminho_db = tmp_path / "test_eval_duble.db"

    with iniciar_rastreamento("plano_executor", "Qual o cardapio?", "geral", "run_duble_01", caminho_db) as trace:
        trace.definir_resposta("Feijoada com sobremesa de pavê de morango.")

    class DubleJuizAlucinacao:
        def invoke(self, mensagens):
            return VereditoJuiz(
                fidelidade_nota=0.4,
                houve_alucinacao=True,
                fatos_inventados=["pavê de morango"],
                relevancia_nota=0.9,
                justificativa="O agente informou a feijoada corretamente, mas alucinou o pavê de morango.",
            )

    resultado = avaliar_execucao(
        run_id="run_duble_01",
        pergunta="Qual o cardapio?",
        resposta="Feijoada com sobremesa de pavê de morango.",
        contexto_mcp="Cardápio do refeitório: Segunda-feira teremos feijoada.",
        papel_usuario="geral",
        juiz_llm=DubleJuizAlucinacao(),
        salvar_no_banco=True,
        caminho_banco=caminho_db,
    )

    assert resultado.fidelidade_score == 0.4
    assert resultado.houve_alucinacao is True
    assert "pavê de morango" in resultado.fatos_inventados
    assert resultado.relevancia_score == 0.9


def test_obter_metricas_qualidade_agregadas_por_padrao(tmp_path: Path):
    caminho_db = tmp_path / "test_metricas_agregadas.db"

    # Coordenador: 1 execução perfeita
    with iniciar_rastreamento("coordenador", "P1", "geral", "run_c1", caminho_db) as t:
        t.definir_resposta("R1")
    avaliar_execucao("run_c1", "P1", "R1", "C1", juiz_llm="deterministico", caminho_banco=caminho_db)

    # Plano-Executor: 1 com alucinação
    with iniciar_rastreamento("plano_executor", "P2", "geral", "run_p1", caminho_db) as t:
        t.definir_resposta("R2 com segredo 50 milhões")
    avaliar_execucao(
        "run_p1",
        "P2",
        "R2 com segredo 50 milhões",
        "C2",
        termos_proibidos=["50 milhões"],
        espera_bloqueio_rbac=True,
        juiz_llm="deterministico",
        caminho_banco=caminho_db,
    )

    metricas = obter_metricas_qualidade(caminho_banco=caminho_db)
    assert "coordenador" in metricas
    assert "plano_executor" in metricas

    assert metricas["coordenador"]["fidelidade_media"] == 1.0
    assert metricas["coordenador"]["taxa_alucinacao"] == 0.0

    assert metricas["plano_executor"]["fidelidade_media"] == 0.0
    assert metricas["plano_executor"]["rbac_conformidade_media"] == 0.0
    assert metricas["plano_executor"]["taxa_falha_seguranca"] == 1.0
