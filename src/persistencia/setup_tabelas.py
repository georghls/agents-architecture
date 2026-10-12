import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import psycopg
from src.config import url_banco

def criar_tabelas():
    # Este é o comando SQL que desenha a estrutura da nossa tabela
    sql_criar_tabela = """
    CREATE TABLE IF NOT EXISTS documentos (
        id SERIAL PRIMARY KEY,
        conteudo TEXT NOT NULL,
        
        -- Campo flexível (JSONB) para guardar quem tem permissão de ler o documento
        -- O seu projeto exige "Integração segura e controle de acesso". Faremos por aqui!
        metadados JSONB,
        
        -- O campo especial da IA: guarda exatamente as 3072 dimensões do Gemini
        embedding vector(3072)
    );

    -- Ativa o Row Level Security (RLS) para corrigir o aviso de segurança no Supabase
    ALTER TABLE documentos ENABLE ROW LEVEL SECURITY;
    """
    
    try:
        print("Conectando ao banco de dados para criar a estrutura...")
        with psycopg.connect(url_banco()) as conexao:
            with conexao.cursor() as cursor:
                
                # Executa o comando de criação
                cursor.execute(sql_criar_tabela)
                
                # Salva as alterações definitivamente
                conexao.commit()
                print("Tabela 'documentos' criada e pronta para uso!")
                
    except Exception as e:
        print(f"Ocorreu um erro ao criar a tabela: {e}")

if __name__ == "__main__":
    criar_tabelas()

