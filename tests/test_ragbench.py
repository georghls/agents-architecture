"""Testes automatizados para a integração do benchmark `galileo-ai/ragbench` (D-027).

Valida:
1. O contrato e integridade de `data/ragbench_golden_dataset.json`.
2. A extração de janela contextual e geração de documentos pelo `ragbench_loader.py`.
3. A recuperação e o isolamento RBAC real via servidor MCP e Supabase (`pgvector`)
   para os três domínios do RAGBench (`delucionqa` -> `geral`, `cuad` -> `rh`, `finqa` -> `diretoria`).
"""

import json
from pathlib import Path

from src.agentes import mcp_toolkit
from src.config import RAIZ_PROJETO
from src.ingestao.ingestao import carregar_documentos_de_arquivos
from src.ingestao.ragbench_loader import (
    MAPEAMENTO_DOMINIOS_RBAC,
    construir_amostra_ragbench,
    extrair_janela_contextual_sentencas,
    extrair_termos_chave_resposta,
)

CAMINHO_RAGBENCH_DATASET = RAIZ_PROJETO / "data" / "ragbench_golden_dataset.json"


def test_ragbench_golden_dataset_contrato_e_pares_rbac():
    """Verifica que o arquivo data/ragbench_golden_dataset.json existe e segue o schema do benchmark."""
    assert CAMINHO_RAGBENCH_DATASET.exists(), f"Dataset não encontrado: {CAMINHO_RAGBENCH_DATASET}"
    itens = json.loads(CAMINHO_RAGBENCH_DATASET.read_text(encoding="utf-8"))
    assert isinstance(itens, list)
    assert len(itens) == 15

    subsets_vistos = set()
    autorizados = [i for i in itens if not i["espera_bloqueio_rbac"]]
    bloqueados = [i for i in itens if i["espera_bloqueio_rbac"]]

    assert len(autorizados) == 9  # 3 delucionqa (geral) + 3 cuad (rh) + 3 finqa (diretoria)
    assert len(bloqueados) == 6   # 3 cuad bloqueados p/ geral + 3 finqa bloqueados p/ geral

    for item in itens:
        subset = item["ragbench_subset"]
        subsets_vistos.add(subset)
        assert subset in MAPEAMENTO_DOMINIOS_RBAC
        assert isinstance(item["pergunta"], str) and len(item["pergunta"]) > 10

        if item["espera_bloqueio_rbac"]:
            assert item["perfil_esperado"] == "geral"
            assert item["deve_conter_evidencia"] is False
            assert len(item["resposta_esperada_nao_contem"]) >= 1
        else:
            assert item["perfil_esperado"] == MAPEAMENTO_DOMINIOS_RBAC[subset]["papel"]
            assert item["deve_conter_evidencia"] is True
            assert len(item["resposta_esperada_contem"]) >= 1

    assert subsets_vistos == {"techqa", "cuad", "finqa"}


def test_ragbench_loader_extracao_contextual_e_offline(tmp_path: Path):
    """Testa a extração de janela de sentenças e geração determinística offline sem rede."""
    falso_row_cuad = {
        "id": "CONTRATO_TESTE_01",
        "question": "What is the license fee threshold?",
        "response": "The license fee threshold is 450,000 dollars per fiscal year.",
        "adherence_score": True,
        "all_relevant_sentence_keys": ["0d"],
        "documents_sentences": [
            [
                ["0a", "SOFTWARE LICENSE AGREEMENT"],
                ["0b", "Party A and Party B"],
                ["0c", "Section 1. Definitions"],
                ["0d", "The annual license fee threshold is 450,000 dollars per fiscal year."],
                ["0e", "Section 2. Term and Termination"],
            ]
        ],
    }

    janela = extrair_janela_contextual_sentencas(falso_row_cuad, janela=1)
    assert "450,000" in janela
    assert "SOFTWARE LICENSE AGREEMENT" in janela

    termos = extrair_termos_chave_resposta(
        falso_row_cuad["response"],
        janela,
        pergunta=falso_row_cuad["question"],
    )
    assert "450,000" in termos
    assert "threshold" not in [t.lower() for t in termos]  # já estava na pergunta

    dados_mock = {
        "techqa": [falso_row_cuad],
        "cuad": [falso_row_cuad],
        "finqa": [falso_row_cuad],
    }
    saida_json = tmp_path / "ragbench_test.json"
    resumo = construir_amostra_ragbench(
        por_dominio=1,
        diretorio_docs=tmp_path / "docs",
        caminho_saida_json=saida_json,
        dados_pre_carregados=dados_mock,
    )
    assert resumo["total_arquivos"] == 3
    assert resumo["total_perguntas_benchmark"] == 5  # 1 geral + 2*(1 autorizado + 1 bloqueio)


def test_ragbench_documentos_carregados_no_pipeline_ingestao():
    """Confirma que todos os 9 arquivos Markdown robustos do RAGBench são segmentados pelo pipeline."""
    chunks = carregar_documentos_de_arquivos()
    chunks_ragbench = [
        c for c in chunks if c["metadados"]["documento"].startswith("ragbench_")
    ]
    docs_unicos = {c["metadados"]["documento"] for c in chunks_ragbench}
    assert len(docs_unicos) == 9
    assert len(chunks_ragbench) >= 200


def test_ragbench_isolamento_rbac_via_mcp_real():
    """Valida via servidor MCP real + Supabase o acesso autorizado e bloqueio cruzado no RAGBench."""
    # 1. Perfil 'geral' recupera technote corporativo da IBM no TechQA
    resp_techqa = mcp_toolkit.consultar_mcp(
        "Is WebSphere Transformation Extender (WTX) supported for IBM Integration Bus V10?",
        "geral",
    )
    assert not resp_techqa.startswith("MCP Error:"), resp_techqa
    assert "websphere" in resp_techqa.lower() or "integration bus" in resp_techqa.lower()
    assert "ragbench_techqa_techqa_dev_q280.md" in resp_techqa

    # 2. Perfil 'geral' é BLOQUEADO ao consultar relatório de M&A do FinQA (restrito à diretoria)
    resp_finqa_bloqueado = mcp_toolkit.consultar_mcp(
        "what portion of total assets acquired of anios are intangible assets?",
        "geral",
    )
    assert not resp_finqa_bloqueado.startswith("MCP Error:"), resp_finqa_bloqueado
    assert "252.0" not in resp_finqa_bloqueado
    assert "65.7" not in resp_finqa_bloqueado
    assert "ragbench_finqa" not in resp_finqa_bloqueado

    # 3. Perfil 'diretoria' recupera legitimamente os valores de ativos intangíveis do FinQA
    resp_finqa_dir = mcp_toolkit.consultar_mcp(
        "what portion of total assets acquired of anios are intangible assets?",
        "diretoria",
    )
    assert not resp_finqa_dir.startswith("MCP Error:"), resp_finqa_dir
    assert "252.0" in resp_finqa_dir or "65.7" in resp_finqa_dir
    assert "ragbench_finqa_finqa_6634.md" in resp_finqa_dir

    # 4. Perfil 'rh' recupera legitimamente o contrato corporativo de Non-Compete do CUAD
    resp_cuad_rh = mcp_toolkit.consultar_mcp(
        "INTELLECTUAL PROPERTY AGREEMENT between SONY ELECTRONICS INC. and GSI TECHNOLOGY Non-Compete Section 3.2",
        "rh",
    )
    assert not resp_cuad_rh.startswith("MCP Error:"), resp_cuad_rh
    assert "ragbench_cuad_gsitechnologyinc" in resp_cuad_rh
