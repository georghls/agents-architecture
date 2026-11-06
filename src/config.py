"""Leitura de configuração e segredos a partir do ambiente (ou do `.env` local).

Os segredos são lidos sob demanda, não na importação, para que módulos como o
servidor MCP possam ser importados (ex.: listar ferramentas) sem credenciais.
"""

import os
from pathlib import Path
import secrets

from dotenv import load_dotenv

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
TAMANHO_MINIMO_CHAVE_AUTH = 32

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


def chave_secreta_auth() -> str:
    """Chave simétrica para assinatura e verificação de JWTs (HS256).

    Exige no mínimo 32 caracteres (256 bits conforme RFC 7518).
    Se não configurada em AUTH_SECRET_KEY:
      - Quando STRICT_AUTH=1, falha fechado lançando ConfiguracaoAusente.
      - Caso contrário, gera uma chave efêmera criptograficamente aleatória (CSPRNG)
        para a sessão do processo e a registra no ambiente para subprocessos MCP,
        eliminando qualquer segredo estático previsível no código-fonte (D-023).
    """
    valor = os.environ.get("AUTH_SECRET_KEY", "").strip()
    if not valor:
        if os.environ.get("STRICT_AUTH", "").strip() == "1":
            raise ConfiguracaoAusente(
                f"Defina AUTH_SECRET_KEY (mínimo {TAMANHO_MINIMO_CHAVE_AUTH} caracteres) no ambiente ou em {RAIZ_PROJETO / '.env'}."
            )
        valor = secrets.token_hex(32)
        os.environ["AUTH_SECRET_KEY"] = valor

    if len(valor) < TAMANHO_MINIMO_CHAVE_AUTH:
        raise ConfiguracaoAusente(
            f"AUTH_SECRET_KEY insegura: possui {len(valor)} caracteres, mas o mínimo exigido (RFC 7518) é {TAMANHO_MINIMO_CHAVE_AUTH}."
        )
    return valor

