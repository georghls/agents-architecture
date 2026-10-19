import os
import sys

# Garante saída UTF-8 no terminal Windows para caracteres especiais e emojis
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Garante que o Python consiga achar o pacote 'src' independente da pasta que você rodar
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agentes.plano_executor import executar_plano_executor


def executar_demonstracao():
    print("=" * 65)
    print("DEMONSTRAÇÃO DO PADRÃO PLANO-EXECUTOR (LangGraph + MCP + Supabase)")
    print("=" * 65)

    pergunta_1 = "Fale-me detalhadamente sobre o orçamento e planos do Projeto Secreto."

    print("\n" + "=" * 65)
    print("[TESTE 1]: Usuário 'geral' tentando acessar o Projeto Secreto")
    print("=" * 65)
    print(f"Pergunta: '{pergunta_1}'\n")
    resp_1 = executar_plano_executor(pergunta_1, role="geral")
    print("\n[RESPOSTA FINAL (PERFIL GERAL)]:")
    print(resp_1)
    print("\n")

    print("=" * 65)
    print("[TESTE 2]: Usuário 'diretoria' acessando o Projeto Secreto")
    print("=" * 65)
    print(f"Pergunta: '{pergunta_1}'\n")
    resp_2 = executar_plano_executor(pergunta_1, role="diretoria")
    print("\n[RESPOSTA FINAL (PERFIL DIRETORIA)]:")
    print(resp_2)
    print("\n")

    pergunta_3 = "Qual é o cardápio do almoço de sexta-feira na empresa?"
    print("=" * 65)
    print("[TESTE 3]: Usuário 'geral' acessando documento público (feijoada)")
    print("=" * 65)
    print(f"Pergunta: '{pergunta_3}'\n")
    resp_3 = executar_plano_executor(pergunta_3, role="geral")
    print("\n[RESPOSTA FINAL (PERFIL GERAL)]:")
    print(resp_3)
    print("\n")


if __name__ == "__main__":
    executar_demonstracao()
