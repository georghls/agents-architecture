import os
import sys
from pathlib import Path

# Garante saída UTF-8 no terminal Windows para caracteres especiais e emojis
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import psycopg
from src.busca.embeddings import get_embedding
from src.config import url_banco


def testar_tudo():
    try:
        url_conexao = url_banco()
        # 1. Conectando ao banco de dados
        print("Tentando conectar ao banco de dados...")
        with psycopg.connect(url_conexao) as conexao:
            print("✅ Conexão bem sucedida!")
            
            with conexao.cursor() as cursor:
                # 2. Ativando o pgvector (fundamental para as buscas por IA)
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                conexao.commit()
                print("✅ Extensão 'vector' ativada com sucesso!")

        # 3. Testando nossa IA de embeddings (Google Gemini)
        print("\nGerando embedding para uma frase de teste...")
        frase = "A inteligência artificial ajuda a encontrar documentos."
        vetor = get_embedding(frase)
        
        # O modelo gemini-embedding-2 gera vetores de 3072 dimensões
        print("✅ Embedding gerado com sucesso!")
        print(f"Tamanho do vetor: {len(vetor)} dimensões")
        print(f"Primeiros 3 números do vetor: {vetor[:3]}")
        
    except Exception as e:
        print(f"❌ Ocorreu um erro: {e}")

if __name__ == "__main__":
    testar_tudo()

