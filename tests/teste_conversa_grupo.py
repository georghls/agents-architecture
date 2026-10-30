"""Script de demonstração interativa do padrão Conversação em Grupo (AutoGen 0.4+).

Executa consultas no terminal demonstrando a dinâmica entre:
  1. Retrieval Agent (acessa MCP com token JWT de sessão)
  2. Analyst Agent (sintetiza resposta com base estrita nas evidências)
  3. Validator Agent (audita contra alucinações e encerra com TERMINATE)
"""

import asyncio
import os
import sys

# Garante saída UTF-8 no terminal Windows para caracteres especiais e acentos
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Garante que o Python consiga achar o pacote 'src' a partir da raiz
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agentes.conversa_grupo import criar_cliente_modelo, executar_conversa_grupo_async


def exibir_dialogo(resultado: dict):
    """Exibe o diálogo turno a turno entre os agentes na sala de conversa."""
    print("\n--- [DIÁLOGO NA SALA DE CONVERSA (GROUP CHAT)] ---")
    for i, msg in enumerate(resultado["mensagens"], 1):
        autor = msg["autor"]
        tipo = msg["tipo"]
        conteudo = msg["conteudo"]
        prefixo = f"[{i}] {autor} ({tipo}):"
        print(f"\n{prefixo}")
        print("-" * len(prefixo))
        print(conteudo)
    print("--------------------------------------------------\n")


async def executar_demonstracao_async():
    print("=" * 70)
    print("DEMONSTRAÇÃO DO PADRÃO CONVERSAÇÃO EM GRUPO (AutoGen 0.4 + MCP)")
    print("=" * 70)

    # Compartilha o cliente HTTP de modelo durante a sessão de teste para eficiência
    cliente = criar_cliente_modelo()

    try:
        pergunta_1 = "Fale-me detalhadamente sobre o orçamento e planos do Projeto Secreto de 2027."

        # -------------------------------------------------------------
        # CASO 1: Perfil geral tentando acessar documento confidencial
        # -------------------------------------------------------------
        print("\n" + "=" * 70)
        print("[TESTE 1]: Usuário 'geral' perguntando sobre o Projeto Secreto (Restrito)")
        print("=" * 70)
        print(f"Pergunta: '{pergunta_1}'\n")

        res_1 = await executar_conversa_grupo_async(pergunta_1, papel="geral", model_client=cliente)
        exibir_dialogo(res_1)

        print(">>> [RESPOSTA FINAL AO USUÁRIO (PERFIL GERAL)]:")
        print(res_1["resposta_final"])
        print(f"Turnos totais: {res_1['turnos']} | Parada: {res_1['motivo_parada']}\n")

        # -------------------------------------------------------------
        # CASO 2: Perfil diretoria acessando documento confidencial
        # -------------------------------------------------------------
        print("=" * 70)
        print("[TESTE 2]: Usuário 'diretoria' acessando o Projeto Secreto (Autorizado)")
        print("=" * 70)
        print(f"Pergunta: '{pergunta_1}'\n")

        res_2 = await executar_conversa_grupo_async(pergunta_1, papel="diretoria", model_client=cliente)
        exibir_dialogo(res_2)

        print(">>> [RESPOSTA FINAL AO USUÁRIO (PERFIL DIRETORIA)]:")
        print(res_2["resposta_final"])
        print(f"Turnos totais: {res_2['turnos']} | Parada: {res_2['motivo_parada']}\n")

        # -------------------------------------------------------------
        # CASO 3: Perfil geral acessando documento público (Feijoada)
        # -------------------------------------------------------------
        pergunta_3 = "Qual é o cardápio do almoço de sexta-feira na empresa?"
        print("=" * 70)
        print("[TESTE 3]: Usuário 'geral' acessando documento público (Cardápio)")
        print("=" * 70)
        print(f"Pergunta: '{pergunta_3}'\n")

        res_3 = await executar_conversa_grupo_async(pergunta_3, papel="geral", model_client=cliente)
        exibir_dialogo(res_3)

        print(">>> [RESPOSTA FINAL AO USUÁRIO (PERFIL GERAL)]:")
        print(res_3["resposta_final"])
        print(f"Turnos totais: {res_3['turnos']} | Parada: {res_3['motivo_parada']}\n")

    finally:
        if hasattr(cliente, "close"):
            await cliente.close()
            await asyncio.sleep(0.05)


def executar_demonstracao():
    asyncio.run(executar_demonstracao_async())


if __name__ == "__main__":
    executar_demonstracao()
