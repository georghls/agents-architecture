"""Testes automatizados da camada de Interface de Usuário e Dashboard (Etapa 4.6)."""

import importlib
import sys
from pathlib import Path
import pytest

from src.config import RAIZ_PROJETO


def test_ui_app_arquivo_existe():
    caminho_app = RAIZ_PROJETO / "src" / "ui" / "app.py"
    assert caminho_app.exists(), f"Arquivo app.py não encontrado em {caminho_app}"
    conteudo = caminho_app.read_text(encoding="utf-8")
    assert "st.set_page_config" in conteudo
    assert "tab_arena, tab_dashboard, tab_auditoria" in conteudo
    assert "plotly" in conteudo


def test_import_dependencias_ui():
    """Garante que Streamlit, Plotly e Pandas estão devidamente instalados e importáveis."""
    import streamlit
    import plotly.express
    import pandas

    assert streamlit.__version__ is not None
    assert plotly.express.__name__ == "plotly.express"
    assert pandas.__version__ is not None
