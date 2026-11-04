"""Tabela de preços versionada e estimador de custos (FinOps) para LLMs e Embeddings.

Permite calcular de forma transparente e reprodutível o custo financeiro
estimado em USD e BRL para cada requisição e agrupamento de agentes,
conforme planejado em docs/llmops.md e docs/decisions.md (D-015).
"""

from typing import TypedDict


class TabelaPreco(TypedDict):
    nome_exibicao: str
    preco_input_1m_usd: float   # Preço por 1 milhão de tokens de entrada (prompt)
    preco_output_1m_usd: float  # Preço por 1 milhão de tokens de saída (resposta)


# Tabela oficial de preços de referência da Google AI Studio / Gemini API (Referência: Outubro/2024 - 2026)
TABELA_PRECOS_GEMINI: dict[str, TabelaPreco] = {
    # Gemini 2.0 / Flash Lite (Modelo padrão veloz usado nos agentes do projeto)
    "gemini-flash-lite-latest": {
        "nome_exibicao": "Gemini 2.0 Flash Lite",
        "preco_input_1m_usd": 0.075,
        "preco_output_1m_usd": 0.30,
    },
    "gemini-2.0-flash-lite": {
        "nome_exibicao": "Gemini 2.0 Flash Lite",
        "preco_input_1m_usd": 0.075,
        "preco_output_1m_usd": 0.30,
    },
    # Gemini 1.5 Flash / 2.5 Flash
    "gemini-1.5-flash": {
        "nome_exibicao": "Gemini 1.5 Flash",
        "preco_input_1m_usd": 0.075,
        "preco_output_1m_usd": 0.30,
    },
    "gemini-2.5-flash": {
        "nome_exibicao": "Gemini 2.5 Flash",
        "preco_input_1m_usd": 0.075,
        "preco_output_1m_usd": 0.30,
    },
    # Gemini Pro (para referência comparativa de modelos pesados)
    "gemini-1.5-pro": {
        "nome_exibicao": "Gemini 1.5 Pro",
        "preco_input_1m_usd": 1.25,
        "preco_output_1m_usd": 5.00,
    },
    # Custo estimado de embeddings (models/gemini-embedding-2 / text-embedding-004)
    # Cobrado por caractere/token ou valor referencial por chamada
    "models/gemini-embedding-2": {
        "nome_exibicao": "Gemini Embedding 2",
        "preco_input_1m_usd": 0.02,
        "preco_output_1m_usd": 0.00,
    },
}

# Taxa de câmbio de referência padrão para conversão USD -> BRL
TAXA_CAMBIO_USD_BRL_PADRAO = 5.75


class EstimativaCusto(TypedDict):
    modelo: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    custo_input_usd: float
    custo_output_usd: float
    custo_total_usd: float
    custo_total_brl: float
    taxa_cambio: float


def calcular_custo_execucao(
    input_tokens: int,
    output_tokens: int,
    modelo: str = "gemini-flash-lite-latest",
    taxa_cambio_usd_brl: float = TAXA_CAMBIO_USD_BRL_PADRAO,
) -> EstimativaCusto:
    """Calcula o custo financeiro exato de uma execução com base no consumo de tokens.

    Se o modelo exato não estiver cadastrado, utiliza a tabela do Flash Lite como fallback.
    """
    input_tokens = max(0, int(input_tokens))
    output_tokens = max(0, int(output_tokens))
    total_tokens = input_tokens + output_tokens

    # Normaliza nome de modelo (ex: 'models/gemini-flash-lite-latest' -> 'gemini-flash-lite-latest')
    chave_modelo = modelo.lower().replace("models/", "").strip()
    
    # Encontra a melhor correspondência na tabela
    tabela = TABELA_PRECOS_GEMINI.get(chave_modelo)
    if not tabela:
        for k, v in TABELA_PRECOS_GEMINI.items():
            if k in chave_modelo or chave_modelo in k:
                tabela = v
                break

    if not tabela:
        tabela = TABELA_PRECOS_GEMINI["gemini-flash-lite-latest"]

    custo_input_usd = (input_tokens / 1_000_000.0) * tabela["preco_input_1m_usd"]
    custo_output_usd = (output_tokens / 1_000_000.0) * tabela["preco_output_1m_usd"]
    custo_total_usd = custo_input_usd + custo_output_usd
    custo_total_brl = custo_total_usd * taxa_cambio_usd_brl

    return {
        "modelo": modelo,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "custo_input_usd": round(custo_input_usd, 8),
        "custo_output_usd": round(custo_output_usd, 8),
        "custo_total_usd": round(custo_total_usd, 8),
        "custo_total_brl": round(custo_total_brl, 6),
        "taxa_cambio": taxa_cambio_usd_brl,
    }
