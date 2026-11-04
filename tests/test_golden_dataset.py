"""Testes automatizados para validação do Golden Dataset de Benchmark (Etapa 4.2).

Garante que o conjunto fixo de perguntas de avaliação comparativa está íntegro,
com schemas válidos, categorias padronizadas e sem inconsistências de dados.
"""

import json
from pathlib import Path
import pytest

from src.config import RAIZ_PROJETO

CAMINHO_GOLDEN_DATASET = RAIZ_PROJETO / "data" / "golden_dataset.json"

CATEGORIAS_VALIDAS = {
    "publica_simples",
    "confidencial_diretoria",
    "confidencial_rh",
    "fora_do_corpus",
    "adversarial_prompt_injection",
}

PERFIS_VALIDOS = {"geral", "diretoria", "rh"}

CAMPOS_OBRIGATORIOS = {
    "id",
    "categoria",
    "pergunta",
    "perfil_esperado",
    "resposta_esperada_contem",
    "resposta_esperada_nao_contem",
    "deve_conter_evidencia",
    "espera_bloqueio_rbac",
    "descricao",
}


def test_golden_dataset_arquivo_existe_e_json_valido():
    assert CAMINHO_GOLDEN_DATASET.exists(), f"Arquivo não encontrado: {CAMINHO_GOLDEN_DATASET}"
    conteudo = CAMINHO_GOLDEN_DATASET.read_text(encoding="utf-8")
    dados = json.loads(conteudo)
    assert isinstance(dados, list)
    assert len(dados) == 24


def test_golden_dataset_chaves_e_unicidade():
    conteudo = CAMINHO_GOLDEN_DATASET.read_text(encoding="utf-8")
    itens = json.loads(conteudo)

    ids_vistos = set()
    contagem_categorias = {cat: 0 for cat in CATEGORIAS_VALIDAS}

    for item in itens:
        assert isinstance(item, dict)
        faltantes = CAMPOS_OBRIGATORIOS - set(item.keys())
        assert not faltantes, f"Item {item.get('id')} não possui os campos obrigatórios: {faltantes}"

        # Unicidade de ID
        item_id = item["id"]
        assert item_id not in ids_vistos, f"ID duplicado detectado: {item_id}"
        ids_vistos.add(item_id)

        # Validação de categorias e perfis
        assert item["categoria"] in CATEGORIAS_VALIDAS, f"Categoria inválida: {item['categoria']}"
        assert item["perfil_esperado"] in PERFIS_VALIDOS, f"Perfil inválido: {item['perfil_esperado']}"

        contagem_categorias[item["categoria"]] += 1

        # Tipagem dos campos
        assert isinstance(item["pergunta"], str) and len(item["pergunta"].strip()) > 5
        assert isinstance(item["resposta_esperada_contem"], list)
        assert isinstance(item["resposta_esperada_nao_contem"], list)
        assert isinstance(item["deve_conter_evidencia"], bool)
        assert isinstance(item["espera_bloqueio_rbac"], bool)

    # Verifica equilíbrio entre as categorias planejadas
    assert contagem_categorias["publica_simples"] == 6
    assert contagem_categorias["confidencial_diretoria"] == 6
    assert contagem_categorias["confidencial_rh"] == 4
    assert contagem_categorias["fora_do_corpus"] == 4
    assert contagem_categorias["adversarial_prompt_injection"] == 4
