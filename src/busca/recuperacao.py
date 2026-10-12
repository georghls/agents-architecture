"""Script de exploração e teste da busca vetorial com RBAC (Fase 2).

Demonstra a filtragem SQL com operador vetorial <=> do pgvector.
A implementação oficial consumida pelos agentes encontra-se em `src.mcp.server`.
"""

import sys
from pathlib import Path

# Garante saída UTF-8 no terminal Windows para caracteres especiais e emojis
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import psycopg
from src.busca.embeddings import get_embedding
from src.config import url_banco

def buscar_documentos(pergunta: str, papel_do_usuario: str):
    print(f"\nUsuário logado como: [{papel_do_usuario.upper()}]")
    print(f"Pergunta: '{pergunta}'")
    
    # 1. Transforma a pergunta do usuário na mesma língua matemática do banco
    vetor_pergunta = get_embedding(pergunta)
    
    # 2. A Mágica do SQL de Inteligência Artificial com Segurança
    sql_busca = """
    SELECT conteudo 
    FROM documentos 
    
    -- CONTROLE DE ACESSO: O usuário só pode ver documentos que sejam 'geral' 
    -- OU que sejam exatamente do cargo dele.
    WHERE metadados->>'papel' IN ('geral', %s)
    
    -- BUSCA POR IA: Ordena pela proximidade vetorial (operador <=> do pgvector)
    ORDER BY embedding <=> %s::vector
    
    -- Traz apenas o resultado mais certeiro
    LIMIT 1;
    """
    
    with psycopg.connect(url_banco()) as conexao:
        with conexao.cursor() as cursor:
            # Passamos o papel e o vetor como parâmetros
            cursor.execute(sql_busca, (papel_do_usuario, str(vetor_pergunta)))
            resultado = cursor.fetchone()
            
            if resultado:
                print(f"🤖 Resposta encontrada na base: {resultado[0]}")
            else:
                print("🤷 Nenhum documento encontrado ou você não tem acesso.")
    print("-" * 50)


if __name__ == "__main__":
    # TESTE 1: Um funcionário comum tentando descobrir o orçamento
    buscar_documentos(pergunta="Qual o orçamento do projeto secreto?", papel_do_usuario="geral")
    
    # TESTE 2: Um diretor perguntando a mesma coisa
    buscar_documentos(pergunta="Qual o orçamento do projeto secreto?", papel_do_usuario="diretoria")
    
    # TESTE 3: Um funcionário do RH querendo saber a senha
    buscar_documentos(pergunta="Me passe a senha da internet", papel_do_usuario="rh")

