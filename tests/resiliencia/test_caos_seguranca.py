"""Testes de resiliência e falha fechada para tokens e autenticação MCP (Etapa 4.4).

Garante que nenhuma credencial inválida, expirada ou forjada consiga
acessar a ferramenta de busca ou ler documentos no servidor MCP.
"""

from datetime import datetime, timezone, timedelta
import os
import jwt
import pytest

from src.config import chave_secreta_auth
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
