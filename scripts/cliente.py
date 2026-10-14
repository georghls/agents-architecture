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

async def consultar_com_papel(role: str | None, pergunta: str):
    rotulo = role.upper() if role else "NÃO AUTENTICADO"
    print(f"\n🔐 Iniciando sessão como: [{rotulo}]")
    
    server_params = parametros_servidor(role=role) if role else parametros_servidor(token="invalido")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # A ferramenta é chamada apenas com a pergunta.
            # O papel de acesso é garantido pelo token JWT na sessão do processo.
            resultado = await session.call_tool(
                "buscar_documentos_corporativos",
                arguments={"pergunta": pergunta},
            )
            print(f"Resultado do Servidor MCP: {resultado.content[0].text}")


async def rodar_cliente():
    print("🔌 Demonstração de Cliente MCP com Autenticação Confiável (A-05 - JWT)")
    print("=" * 65)

    # 1. Descoberta de ferramentas usando sessão do servidor
    params_descoberta = parametros_servidor(role="geral")
    async with stdio_client(params_descoberta) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            ferramentas = await session.list_tools()
            print("Ferramentas descobertas no servidor:")
            for tool in ferramentas.tools:
                print(f" 🛠️  - {tool.name}: {tool.description.strip()}")
                print(f"      Schema: {list(tool.input_schema.get('properties', {}).keys())}")
            print("-" * 65)

    # 2. Requisição como DIRETORIA (token assinado para diretoria)
    await consultar_com_papel("diretoria", "Qual o orçamento do projeto secreto?")

    # 3. Requisição como GERAL (token assinado para geral)
    await consultar_com_papel("geral", "Qual o orçamento do projeto secreto?")

    # 4. Requisição com token INVÁLIDO (falha fechada)
    await consultar_com_papel(None, "Qual o orçamento do projeto secreto?")
    print("=" * 65)


if __name__ == "__main__":
    # O MCP usa comunicação assíncrona moderna (async/await)
    asyncio.run(rodar_cliente())
