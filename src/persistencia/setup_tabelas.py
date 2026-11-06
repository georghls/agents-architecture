import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import psycopg
from src.config import url_banco


def criar_tabelas():
    # Este é o comando SQL que desenha a estrutura da nossa tabela e políticas RLS (D-023)
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

    -- Ativa e força o Row Level Security (RLS) com políticas explícitas de defesa em profundidade (D-023)
    ALTER TABLE documentos ENABLE ROW LEVEL SECURITY;
    ALTER TABLE documentos FORCE ROW LEVEL SECURITY;

    DROP POLICY IF EXISTS politica_leitura_rbac ON documentos;
    CREATE POLICY politica_leitura_rbac ON documentos
        FOR SELECT
        USING (
            metadados->>'papel' = 'geral'
            OR metadados->>'papel' = COALESCE(NULLIF(current_setting('app.current_role', true), ''), current_user)
            OR current_user = 'postgres'
        );

    DROP POLICY IF EXISTS politica_ingestao_admin ON documentos;
    CREATE POLICY politica_ingestao_admin ON documentos
        FOR ALL
        USING (current_user = 'postgres')
        WITH CHECK (current_user = 'postgres');
    """
    
    try:
        print("Conectando ao banco de dados para criar a estrutura...")
        with psycopg.connect(url_banco()) as conexao:
            with conexao.cursor() as cursor:
                
                # Executa o comando de criação
                cursor.execute(sql_criar_tabela)
                
                # Salva as alterações definitivamente
                conexao.commit()
                print("Tabela 'documentos' e políticas RLS criadas e prontas para uso!")
                
    except Exception as e:
        print(f"Ocorreu um erro ao criar a tabela: {e}")

if __name__ == "__main__":
    criar_tabelas()
