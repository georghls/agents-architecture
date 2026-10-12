import os
import sys

# Garante saída UTF-8 no terminal Windows para caracteres especiais e emojis
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from langchain_core.messages import HumanMessage

# Garante que o Python consiga achar o pacote 'src' independente da pasta que você rodar
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agentes.coordenador import grafo_coordenador


def executar_testes():
    print("="*60)
    print("[TESTE 1]: Usuário 'geral' tentando acessar o Projeto Secreto")
    print("="*60)
    estado_inicial_1 = {
        "role": "geral",
        "messages": [HumanMessage(content="Fale-me detalhadamente sobre o Projeto Secreto de 50 Milhões.")],
        "proximo_passo": "",
        "query_atual": ""
    }
    
    resultado_1 = grafo_coordenador.invoke(estado_inicial_1)
    
    print("\n[RESPOSTA FINAL DO AGENTE (TESTE 1)]:")
    print(resultado_1['messages'][-1].text)
    print("\n\n")


    print("="*60)
    print("[TESTE 2]: Usuário 'diretoria' acessando o Projeto Secreto")
    print("="*60)
    estado_inicial_2 = {
        "role": "diretoria",
        "messages": [HumanMessage(content="Fale-me detalhadamente sobre o Projeto Secreto de 50 Milhões.")],
        "proximo_passo": "",
        "query_atual": ""
    }
    
    resultado_2 = grafo_coordenador.invoke(estado_inicial_2)
    
    print("\n[RESPOSTA FINAL DO AGENTE (TESTE 2)]:")
    print(resultado_2['messages'][-1].text)
    print("\n\n")


    print("="*60)
    print("[TESTE 3]: Pergunta genérica (não deve acionar o Pesquisador)")
    print("="*60)
    estado_inicial_3 = {
        "role": "geral", # A permissão aqui não importa muito
        "messages": [HumanMessage(content="Olá, tudo bem? Você sabe me dizer como o céu é azul?")],
        "proximo_passo": "",
        "query_atual": ""
    }
    
    resultado_3 = grafo_coordenador.invoke(estado_inicial_3)
    
    print("\n[RESPOSTA FINAL DO AGENTE (TESTE 3)]:")
    print(resultado_3['messages'][-1].text)
    print("\n")

if __name__ == "__main__":
    # IMPORTANTE: A GEMINI_API_KEY deve estar definida no seu terminal.
    executar_testes()
