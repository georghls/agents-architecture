"""Módulo de autorização e controle de identidade (A-05).

A autenticação é realizada com tokens JWT assinados (HS256) na fronteira MCP,
garantindo identidade confiável e isolamento RBAC rígido no SQL sem confiar
em argumentos declarados pelo modelo.
"""

from src.autorizacao.tokens import (
    ErroAutorizacao,
    TokenAusenteErro,
    TokenExpiradoErro,
    TokenInvalidoErro,
    gerar_token_sessao,
    validar_token_sessao,
)

__all__ = [
    "ErroAutorizacao",
    "TokenAusenteErro",
    "TokenExpiradoErro",
    "TokenInvalidoErro",
    "gerar_token_sessao",
    "validar_token_sessao",
]

