import os
import sys

from mcp.server.mcpserver import MCPServer
import psycopg

from src.autorizacao.tokens import ErroAutorizacao, validar_token_sessao
from src.busca.embeddings import get_embedding
from src.config import url_banco

MENSAGEM_SEM_RESULTADO = "Nenhum documento encontrado nos registros autorizados para o seu perfil."
MENSAGEM_ERRO_AUTH = "Erro MCP: Sessão não autenticada ou token de identidade inválido. Acesso negado."
MENSAGEM_ERRO_SISTEMA = "Erro interno no servidor de documentos: falha temporária de infraestrutura."
LIMIAR_DISTANCIA = 0.60  # Nota de corte: distância máxima aceitável para considerar um documento relevante
TOP_K_PADRAO = 3  # Número máximo de trechos relevantes retornados (D-022)

# 1. Inicializa o Servidor MCP com um nome amigável
mcp = MCPServer("ServidorDeDocumentos")


def obter_papel_da_sessao() -> str:
    """Extrai e valida o papel autorizado da sessão a partir do token JWT (A-05)."""
    token = os.environ.get("MCP_AUTH_TOKEN")
    try:
        payload = validar_token_sessao(token)
        return payload["papel"]
    except ErroAutorizacao as erro:
        print(f"[Servidor MCP] Falha de autenticação da sessão: {erro}", file=sys.stderr)
        raise PermissionError(str(erro)) from erro


def _formatar_citacao(
    doc_origem: str | None,
    versao_doc: str | None = None,
    chunk_id: str | int | None = None,
    formato_curto: bool = True,
) -> str:
    """Constrói identificador de citação rastreável com documento, versão e chunk (D-025)."""
    if not doc_origem:
        return ""
    partes = [str(doc_origem)]
    if versao_doc:
        partes.append(str(versao_doc))
    if chunk_id is not None and str(chunk_id).strip():
        partes.append(f"chunk {chunk_id}")
    ref = " | ".join(partes)
    return f" [{ref}]" if formato_curto else f" (Origem: {ref})"


def _desempacotar_linha_resultado(linha: tuple) -> tuple[str, str | None, str | None, str | int | None, float]:
    """Suporta tuplas de 5 colunas (atuais) ou 3 colunas (retrocompatibilidade com mocks)."""
    if len(linha) >= 5:
        conteudo, doc_origem, versao_doc, chunk_id, distancia = linha[:5]
        return conteudo, doc_origem, versao_doc, chunk_id, float(distancia)
    conteudo, doc_origem, distancia = linha[:3]
    return conteudo, doc_origem, None, None, float(distancia)
def buscar_no_banco(pergunta: str, top_k: int = TOP_K_PADRAO) -> str:
    """Busca com isolamento rígido de perfil, filtro de publicação ativa e citação rastreável (D-025).
    
    1. O usuário só consulta documentos aos quais tem permissão (filtro de perfil no SQL).
       O papel é obrigatoriamente obtido da identidade confiável da sessão (JWT) via
       `obter_papel_da_sessao()`, sem aceitar papel por parâmetro (D-023).
    2. Apenas documentos com estado `published` são elegíveis (documentos `revoked` são ignorados).
    3. Documentos permitidos só são retornados se atingirem a nota de corte (distância <= LIMIAR_DISTANCIA).
    4. Retorna os top_k trechos com citação estruturada (`documento | versao | chunk`).
    """
    try:
        papel_usuario_normalizado = obter_papel_da_sessao()
    except PermissionError:
        return MENSAGEM_ERRO_AUTH

    if not isinstance(pergunta, str) or not pergunta.strip():
        return MENSAGEM_SEM_RESULTADO

    top_k_seguro = max(1, min(int(top_k), 10))

    try:
        vetor_pergunta = get_embedding(pergunta, task_type="retrieval_query")
        
        sql_busca = """
        SELECT 
            conteudo, 
            metadados->>'documento' AS doc_origem,
            metadados->>'versao' AS versao_doc,
            metadados->>'chunk_id' AS chunk_id,
            (embedding <=> %s::vector) AS distancia
        FROM documentos 
        WHERE metadados->>'papel' IN ('geral', %s)
          AND COALESCE(metadados->>'status', 'published') = 'published'
          AND (embedding <=> %s::vector) <= %s
        ORDER BY distancia ASC
        LIMIT %s;
        """
        
        with psycopg.connect(url_banco()) as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    sql_busca, 
                    (str(vetor_pergunta), papel_usuario_normalizado, str(vetor_pergunta), LIMIAR_DISTANCIA, top_k_seguro)
                )
                resultados = cursor.fetchall()
                
                if not resultados:
                    return MENSAGEM_SEM_RESULTADO
                
                if len(resultados) == 1:
                    conteudo, doc_origem, versao_doc, chunk_id, _ = _desempacotar_linha_resultado(resultados[0])
                    origem_str = _formatar_citacao(doc_origem, versao_doc, chunk_id, formato_curto=True)
                    return f"Documento encontrado{origem_str}: {conteudo}"
                
                trechos = []
                for i, linha in enumerate(resultados, 1):
                    conteudo, doc_origem, versao_doc, chunk_id, _ = _desempacotar_linha_resultado(linha)
                    origem_str = _formatar_citacao(doc_origem, versao_doc, chunk_id, formato_curto=False)
                    trechos.append(f"[{i}]{origem_str}\n{conteudo}")
                
                return f"Documentos encontrados ({len(resultados)} trechos autorizados):\n\n" + "\n\n".join(trechos)
    except Exception as erro:
        print(f"[Servidor MCP] Erro de infraestrutura ao buscar no banco: {erro}", file=sys.stderr)
        return MENSAGEM_ERRO_SISTEMA


# 2. Transforma a função numa ferramenta (tool) oficial do MCP
@mcp.tool()
def buscar_documentos_corporativos(pergunta: str) -> str:
    """
    Busca documentos na base de conhecimento da empresa usando Inteligência Artificial.
    A identidade e as permissões de acesso são validadas de forma confiável via token JWT da sessão MCP.
    """
    return buscar_no_banco(pergunta)


if __name__ == "__main__":
    # 3. Liga o servidor usando o protocolo de texto padrão (stdio).
    # Rode a partir da raiz do projeto: python -m src.mcp.server
    mcp.run()

