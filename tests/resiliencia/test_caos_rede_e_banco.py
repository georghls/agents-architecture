"""Testes de resiliência e isolamento contra falhas de rede, banco e embeddings (Etapa 4.4).

Verifica que:
1. Erros de banco de dados (ex: OperationalError) não expõem credenciais ou tracebacks.
2. Indisponibilidade de API de embeddings retorna erro amigável sem quebrar o processo.
"""

from unittest.mock import patch
import psycopg
import pytest

from src.autorizacao.tokens import gerar_token_sessao
from src.mcp.server import buscar_no_banco, MENSAGEM_ERRO_SISTEMA


def test_falha_conexao_banco_retorna_erro_sistema_sem_vazar_credenciais(monkeypatch):
    token = gerar_token_sessao("geral")
    monkeypatch.setenv("MCP_AUTH_TOKEN", token)

    mensagem_erro_psycopg = "OperationalError: Connection refused to postgresql://postgres:senha_super_secreta_999@db.supabase.co:5432"

    with patch("src.mcp.server.get_embedding", return_value=[0.1] * 3072):
        with patch("src.mcp.server.psycopg.connect", side_effect=psycopg.OperationalError(mensagem_erro_psycopg)):
            resultado = buscar_no_banco("qual o cardápio?")

            # Deve retornar mensagem de erro amigável
            assert resultado == MENSAGEM_ERRO_SISTEMA

            # Garantia estrita: nenhuma senha ou host de banco deve vazar para a saída
            assert "senha_super_secreta_999" not in resultado
            assert "supabase.co" not in resultado
            assert "OperationalError" not in resultado


def test_falha_api_embeddings_retorna_erro_sistema(monkeypatch):
    token = gerar_token_sessao("diretoria")
    monkeypatch.setenv("MCP_AUTH_TOKEN", token)

    with patch("src.mcp.server.get_embedding", side_effect=RuntimeError("Google Gemini API error 503 Service Unavailable")):
        resultado = buscar_no_banco("projeto secreto")

        assert resultado == MENSAGEM_ERRO_SISTEMA
        assert "503" not in resultado
