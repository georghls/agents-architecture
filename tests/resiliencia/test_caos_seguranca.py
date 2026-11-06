"""Testes de resiliência e falha fechada para tokens e autenticação MCP (Etapa 4.4).

Garante que nenhuma credencial inválida, expirada ou forjada consiga
acessar a ferramenta de busca ou ler documentos no servidor MCP.
"""

from datetime import datetime, timezone, timedelta
import inspect
import os
import jwt
import pytest

from src.autorizacao.tokens import (
    TokenInvalidoErro,
    gerar_token_sessao,
    validar_token_sessao,
)
from src.config import ConfiguracaoAusente, chave_secreta_auth
from src.mcp.server import buscar_no_banco, MENSAGEM_ERRO_AUTH


def test_token_adulterado_falha_fechada(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token_falsificado.assinatura_falsa")
    resposta = buscar_no_banco("qualquer pergunta")
    assert resposta == MENSAGEM_ERRO_AUTH


def test_token_expirado_falha_fechada(monkeypatch):
    agora = datetime.now(timezone.utc)
    payload_expirado = {
        "sub": "usuario_teste",
        "papel": "diretoria",
        "iat": int((agora - timedelta(hours=2)).timestamp()),
        "exp": int((agora - timedelta(hours=1)).timestamp()),  # Expirado há 1 hora
    }
    token_expirado = jwt.encode(payload_expirado, chave_secreta_auth(), algorithm="HS256")
    monkeypatch.setenv("MCP_AUTH_TOKEN", token_expirado)

    resposta = buscar_no_banco("orçamento projeto secreto")
    assert resposta == MENSAGEM_ERRO_AUTH


def test_token_com_chave_forjada_rejeitado(monkeypatch):
    chave_atacante = "chave-secreta-do-invasor-minimo-32-chars-long"
    payload = {
        "sub": "invasor",
        "papel": "diretoria",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
    }
    token_forjado = jwt.encode(payload, chave_atacante, algorithm="HS256")
    monkeypatch.setenv("MCP_AUTH_TOKEN", token_forjado)

    resposta = buscar_no_banco("orçamento projeto secreto")
    assert resposta == MENSAGEM_ERRO_AUTH


def test_token_ausente_rejeitado(monkeypatch):
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    resposta = buscar_no_banco("orçamento projeto secreto")
    assert resposta == MENSAGEM_ERRO_AUTH


@pytest.mark.parametrize("papel_invalido", ["admin", "superuser", "ceo", "root", "qualquer"])
def test_papel_fora_da_whitelist_rejeitado_na_emissao_e_validacao(papel_invalido):
    """Impede escalação de privilégio com papéis arbitrários fora de {'geral', 'rh', 'diretoria'} (D-023)."""
    with pytest.raises(ValueError):
        gerar_token_sessao(papel_invalido)

    # Mesmo se alguém assinar manualmente um JWT com a chave correta e um papel não listado:
    agora = int(datetime.now(timezone.utc).timestamp())
    token_manual = jwt.encode(
        {"sub": "atacante", "papel": papel_invalido, "iat": agora, "exp": agora + 600},
        chave_secreta_auth(),
        algorithm="HS256",
    )
    with pytest.raises(TokenInvalidoErro):
        validar_token_sessao(token_manual)


def test_chave_secreta_curta_rejeitada_rfc7518(monkeypatch):
    """Chaves HMAC menores que 32 caracteres (256 bits) devem ser rejeitadas (D-023)."""
    with pytest.raises(ValueError):
        gerar_token_sessao("geral", segredo="chave-curta-123")

    with pytest.raises(TokenInvalidoErro):
        validar_token_sessao("token.qualquer.aqui", segredo="chave-curta-123")

    monkeypatch.setenv("AUTH_SECRET_KEY", "curta-demais")
    with pytest.raises(ConfiguracaoAusente):
        chave_secreta_auth()


def test_strict_auth_sem_chave_falha_fechado(monkeypatch):
    """Em modo STRICT_AUTH=1, ausência de AUTH_SECRET_KEY falha fechado (D-023)."""
    monkeypatch.delenv("AUTH_SECRET_KEY", raising=False)
    monkeypatch.setenv("STRICT_AUTH", "1")
    with pytest.raises(ConfiguracaoAusente):
        chave_secreta_auth()


def test_buscar_no_banco_nao_possui_parametro_bypass_de_papel():
    """Garante que buscar_no_banco não aceita papel_do_usuario por parâmetro (D-023)."""
    assinatura = inspect.signature(buscar_no_banco)
    assert "papel_do_usuario" not in assinatura.parameters
