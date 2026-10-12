"""Leitura de configuração e segredos a partir do ambiente (ou do `.env` local).

Os segredos são lidos sob demanda, não na importação, para que módulos como o
servidor MCP possam ser importados (ex.: listar ferramentas) sem credenciais.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ_PROJETO = Path(__file__).resolve().parents[1]

# Variáveis já definidas no ambiente têm prioridade sobre o .env.
load_dotenv(RAIZ_PROJETO / ".env", override=False)


class ConfiguracaoAusente(RuntimeError):
    """Variável obrigatória não definida no ambiente nem no `.env`."""


def obter_obrigatoria(nome: str) -> str:
    valor = os.environ.get(nome, "").strip()
    if not valor:
        raise ConfiguracaoAusente(
            f"Defina {nome} no ambiente ou em {RAIZ_PROJETO / '.env'} (veja .env.example)."
        )
    return valor


def url_banco() -> str:
    return obter_obrigatoria("DATABASE_URL")


def chave_gemini() -> str:
    return obter_obrigatoria("GEMINI_API_KEY")
