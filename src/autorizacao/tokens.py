"""Módulo de emissão e validação de tokens JWT para o protocolo MCP (A-05).

Implementa autenticação confiável por token assinado (HS256 - HMAC-SHA256),
garantindo que o papel do usuário (RBAC) seja validado criptograficamente no
servidor MCP e nunca aceito como argumento arbitrário ou autodeclarado pelo modelo.
"""

import time
from typing import Any

import jwt

from src.config import chave_secreta_auth

ALGORITMO_PADRAO = "HS256"
DURACAO_PADRAO_SEGUNDOS = 3600  # 1 hora
TAMANHO_MINIMO_SEGREDO = 32  # 256 bits conforme RFC 7518 para HS256
PAPEIS_PERMITIDOS: frozenset[str] = frozenset({"geral", "rh", "diretoria"})


class ErroAutorizacao(Exception):
    """Exceção base para falhas de autenticação e autorização."""


class TokenAusenteErro(ErroAutorizacao):
    """Token de autenticação não fornecido na sessão MCP."""


class TokenInvalidoErro(ErroAutorizacao):
    """Token malformado, com assinatura inválida ou claims ausentes."""


class TokenExpiradoErro(ErroAutorizacao):
    """Token com data de expiração (exp) ultrapassada."""


def gerar_token_sessao(
    papel: str,
    usuario_id: str = "sistema",
    expiracao_segundos: int = DURACAO_PADRAO_SEGUNDOS,
    segredo: str | None = None,
) -> str:
    """Gera um token JWT assinado (HS256) vinculando identidade e papel (role).

    Args:
        papel: Papel de acesso (ex.: 'geral', 'diretoria', 'rh').
        usuario_id: Identificador do usuário ou agente solicitante (claim 'sub').
        expiracao_segundos: Tempo de validade do token em segundos.
        segredo: Chave HMAC opcional (usa chave_secreta_auth() por padrão).

    Returns:
        String contendo o token JWT codificado.
    """
    if not isinstance(papel, str) or not papel.strip():
        raise ValueError("O papel (role) é obrigatório para emissão do token.")

    papel_normalizado = papel.strip().lower()
    if papel_normalizado not in PAPEIS_PERMITIDOS:
        raise ValueError(
            f"Papel de acesso inválido: '{papel}'. Papéis permitidos: {sorted(PAPEIS_PERMITIDOS)}"
        )

    chave = segredo if segredo is not None else chave_secreta_auth()
    if not isinstance(chave, str) or len(chave.strip()) < TAMANHO_MINIMO_SEGREDO:
        raise ValueError(
            f"A chave secreta HMAC deve possuir no mínimo {TAMANHO_MINIMO_SEGREDO} caracteres (RFC 7518)."
        )

    agora = int(time.time())

    payload = {
        "sub": usuario_id.strip() if usuario_id else "sistema",
        "papel": papel_normalizado,
        "iat": agora,
        "exp": agora + expiracao_segundos,
    }

    return jwt.encode(payload, chave, algorithm=ALGORITMO_PADRAO)


def validar_token_sessao(token: str | None, segredo: str | None = None) -> dict[str, Any]:
    """Valida a assinatura, claims obrigatórias, papel autorizado e expiração do token JWT.

    Args:
        token: String do token JWT ou None.
        segredo: Chave HMAC opcional para verificação.

    Returns:
        Dicionário com o payload decodificado (incluindo 'sub' e 'papel').

    Raises:
        TokenAusenteErro: Se o token for nulo ou vazio.
        TokenExpiradoErro: Se o token estiver expirado.
        TokenInvalidoErro: Se a assinatura for inválida, chave fraca ou claims inválidas.
    """
    if not token or not isinstance(token, str) or not token.strip():
        raise TokenAusenteErro("Token de autenticação MCP não fornecido.")

    chave = segredo if segredo is not None else chave_secreta_auth()
    if not isinstance(chave, str) or len(chave.strip()) < TAMANHO_MINIMO_SEGREDO:
        raise TokenInvalidoErro(
            f"Chave HMAC inválida ou menor que {TAMANHO_MINIMO_SEGREDO} caracteres."
        )

    try:
        payload = jwt.decode(
            token.strip(),
            chave,
            algorithms=[ALGORITMO_PADRAO],
            options={"require": ["sub", "papel", "iat", "exp"]},
        )
    except jwt.ExpiredSignatureError as erro:
        raise TokenExpiradoErro("Token de autenticação MCP expirado.") from erro
    except jwt.InvalidTokenError as erro:
        raise TokenInvalidoErro(f"Token de autenticação MCP inválido: {erro}") from erro

    papel = payload.get("papel")
    if not isinstance(papel, str) or not papel.strip():
        raise TokenInvalidoErro("Token de autenticação não contém a claim obrigatória 'papel'.")

    papel_normalizado = papel.strip().lower()
    if papel_normalizado not in PAPEIS_PERMITIDOS:
        raise TokenInvalidoErro(f"Token contém papel não autorizado: '{papel}'.")

    payload["papel"] = papel_normalizado
    return payload
