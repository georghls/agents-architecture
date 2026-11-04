"""Testes automatizados do pipeline de benchmark e consolidação de LLMOps (Etapa 4.5)."""

import json
from pathlib import Path
from unittest.mock import patch
import pytest

from scripts.executar_benchmark import parse_args, imprimir_tabela_resumo
from src.observabilidade.telemetria import (
    inicializar_banco,
    iniciar_rastreamento,
    salvar_avaliacao,
    obter_resumo_estatistico,
    obter_metricas_qualidade,
)


def test_argumentos_benchmark_padrao():
    with patch("sys.argv", ["scripts/executar_benchmark.py"]):
        args = parse_args()
        assert "coordenador" in args.padroes
        assert "plano_executor" in args.padroes
        assert "conversa_grupo" in args.padroes
        assert args.modo_avaliador == "deterministico"
        assert args.delay == 2.0


def test_argumentos_benchmark_customizados():
    with patch("sys.argv", [
        "scripts/executar_benchmark.py",
        "--padroes", "coordenador",
        "--limite", "5",
        "--modo-avaliador", "llm",
        "--delay", "0.5",
    ]):
        args = parse_args()
        assert args.padroes == ["coordenador"]
        assert args.limite == 5
        assert args.modo_avaliador == "llm"
        assert args.delay == 0.5


def test_imprimir_tabela_resumo_sem_erros(tmp_path: Path, capsys):
    banco = tmp_path / "bench_test.db"
    inicializar_banco(banco)

    # Insere dados para os 3 padrões
    for padrao in ["coordenador", "plano_executor", "conversa_grupo"]:
        run_id = f"run_{padrao}_01"
        with iniciar_rastreamento(padrao, "Pergunta teste", "geral", run_id, banco) as t:
            t.registrar_tokens(200, 100)
            t.definir_resposta("Resposta teste")

        salvar_avaliacao({
            "run_id": run_id,
            "fidelidade_score": 1.0,
            "relevancia_score": 0.9,
            "seguranca_rbac_score": 1.0,
            "houve_alucinacao": False,
            "falha_seguranca": False,
            "justificativa": "OK",
        }, caminho_banco=banco)

    imprimir_tabela_resumo(banco)
    saida = capsys.readouterr().out

    assert "RELATÓRIO COMPARATIVO DE LLMOPS" in saida
    assert "coordenador" in saida
    assert "plano_executor" in saida
    assert "conversa_grupo" in saida
    assert "100.0%" in saida  # Fidelidade
