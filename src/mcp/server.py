from mcp.server.mcpserver import MCPServer
import psycopg

# Importamos a função de embeddings lá da sua pasta src/busca
from src.busca.embeddings import get_embedding
from src.config import url_banco

MENSAGEM_SEM_RESULTADO = "Nenhum documento encontrado nos registros autorizados para o seu perfil."
LIMIAR_DISTANCIA = 0.60  # Nota de corte: distância máxima aceitável para considerar um documento relevante

# 1. Inicializa o Servidor MCP com um nome amigável
mcp = MCPServer("ServidorDeDocumentos")


def buscar_no_banco(pergunta: str, papel_do_usuario: str) -> str:
    """Busca com isolamento rígido de perfil e nota de corte de relevância no SQL.
    
    1. O usuário só consulta documentos aos quais tem permissão (filtro de perfil no SQL).
    2. Documentos permitidos só são retornados se atingirem a nota de corte (distância <= LIMIAR_DISTANCIA).
    3. Se não houver documento relevante autorizado, retorna mensagem neutra e segura,
       evitando tanto falsos positivos (feijoada) quanto vazamento de existência do segredo (oráculo).
    """
    vetor_pergunta = get_embedding(pergunta)
    papel_usuario_normalizado = (papel_do_usuario or "geral").strip().lower()
    
    sql_busca = """
    SELECT 
        conteudo, 
        (embedding <=> %s::vector) AS distancia
    FROM documentos 
    WHERE metadados->>'papel' IN ('geral', %s)
      AND (embedding <=> %s::vector) <= %s
    ORDER BY distancia ASC
    LIMIT 1;
    """
    
    with psycopg.connect(url_banco()) as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                sql_busca, 
                (str(vetor_pergunta), papel_usuario_normalizado, str(vetor_pergunta), LIMIAR_DISTANCIA)
            )
            resultado = cursor.fetchone()
            
            if not resultado:
                return MENSAGEM_SEM_RESULTADO
            
            conteudo, distancia = resultado
            return f"Documento encontrado: {conteudo}"


# 2. Transforma a função numa ferramenta (tool) oficial do MCP
@mcp.tool()
def buscar_documentos_corporativos(pergunta: str, papel_do_usuario: str) -> str:
    """
    Busca documentos na base de conhecimento da empresa usando Inteligência Artificial.
    Sempre informe a 'pergunta' do usuário e o 'papel_do_usuario' (ex: geral, rh, diretoria).
    """
    return buscar_no_banco(pergunta, papel_do_usuario)

if __name__ == "__main__":
    # 3. Liga o servidor usando o protocolo de texto padrão (stdio).
    # Rode a partir da raiz do projeto: python -m src.mcp.server
    
    mcp.run()
