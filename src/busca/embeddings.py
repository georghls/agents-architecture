"""Geração de embeddings semânticos via SDK oficial `google-genai` (D-006, D-024).

Suporta diferenciação assimétrica de `task_type`:
- `retrieval_document`: para indexação de documentos e chunks na ingestão.
- `retrieval_query`: para vetorização de perguntas de busca no servidor MCP.
"""

from typing import Literal
from google import genai
from google.genai import types

from src.config import chave_gemini

TipoTarefaEmbedding = Literal["retrieval_document", "retrieval_query"]

_cliente: genai.Client | None = None


def _obter_cliente() -> genai.Client:
    """Inicialização preguiçosa: importar este módulo não exige GEMINI_API_KEY."""
    global _cliente
    if _cliente is None:
        _cliente = genai.Client(api_key=chave_gemini())
    return _cliente


def get_embedding(
    text: str,
    task_type: TipoTarefaEmbedding = "retrieval_document",
) -> list[float]:
    """Transforma o texto em vetor denso de 3072 dimensões usando `models/gemini-embedding-2`."""
    cliente = _obter_cliente()
    resultado = cliente.models.embed_content(
        model="models/gemini-embedding-2",
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    if not resultado.embeddings or not resultado.embeddings[0].values:
        raise RuntimeError("A API de embeddings do Gemini retornou um vetor vazio.")
    return list(resultado.embeddings[0].values)
