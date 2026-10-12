import asyncio
import sys
from pathlib import Path

# Garante saída UTF-8 no terminal Windows para caracteres especiais e emojis
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from src.agentes.mcp_toolkit import parametros_servidor

# Pode rodar diretamente com: python scripts/cliente.py ou python -m scripts.cliente

async def rodar_cliente():
    print("🔌 Iniciando Cliente MCP e conectando ao Servidor...")
    
    # 1. Configura os parâmetros para o cliente "ligar" o nosso servidor Python
    # (python -m src.mcp.server, na raiz do projeto, com DATABASE_URL/GEMINI_API_KEY)
    server_params = parametros_servidor()
    
    # 2. Estabelece a conexão (via entrada e saída padrão - STDIO)
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Inicializa o aperto de mãos (handshake)
            await session.initialize()
            print("✅ Conexão estabelecida com sucesso!\n")
            
            # 3. O Cliente "pergunta" ao servidor quais ferramentas ele possui
            ferramentas = await session.list_tools()
            print("Ferramentas descobertas no servidor:")
            for tool in ferramentas.tools:
                print(f" 🛠️  - {tool.name}")
            
            print("-" * 50)
            
            # 4. O Cliente decide usar a ferramenta como um DIRETOR
            print("🕵️ Fazendo requisição como: DIRETORIA")
            resultado_diretor = await session.call_tool(
                "buscar_documentos_corporativos", 
                arguments={
                    "pergunta": "Qual o orçamento do projeto secreto?", 
                    "papel_do_usuario": "diretoria"
                }
            )
            print(f"Resposta do Servidor MCP: {resultado_diretor.content[0].text}")
            print("-" * 50)
            
            # 5. O Cliente decide usar a ferramenta como um FUNCIONÁRIO GERAL
            print("🧑‍💼 Fazendo requisição como: GERAL")
            resultado_geral = await session.call_tool(
                "buscar_documentos_corporativos", 
                arguments={
                    "pergunta": "Qual o orçamento do projeto secreto?", 
                    "papel_do_usuario": "geral"
                }
            )
            print(f"Resposta do Servidor MCP: {resultado_geral.content[0].text}")
            print("-" * 50)

if __name__ == "__main__":
    # O MCP usa comunicação assíncrona moderna (async/await)
    asyncio.run(rodar_cliente())
