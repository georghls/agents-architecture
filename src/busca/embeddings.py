import google.generativeai as genai

from src.config import chave_gemini

_configurado = False


def _configurar() -> None:
    # Configuração preguiçosa: importar este módulo não exige a chave.
    global _configurado
    if not _configurado:
        genai.configure(api_key=chave_gemini())
        _configurado = True


def get_embedding(text: str) -> list[float]:
    """
    Usa a API do Google Gemini para transformar o texto em vetor.
    """
    _configurar()
    resultado = genai.embed_content(
        model="models/gemini-embedding-2", # Modelo de embeddings mais recente disponível para sua chave
        content=text,
        task_type="retrieval_document"
    )
    
    # O Gemini já devolve uma lista de números, então não precisamos do .tolist()
    return resultado['embedding']
