import json
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

# Nossa base de conhecimento sintética de teste (como pede o projeto)
documentos_teste = [
    {
        "texto": "Política de Férias 2026: Todo funcionário tem direito a 30 dias após um ano de trabalho.",
        "metadados": {"papel": "geral"} # Qualquer um pode ver
    },
    {
        "texto": "Cardápio do refeitório: Segunda-feira teremos feijoada e opção vegetariana.",
        "metadados": {"papel": "geral"}
    },
    {
        "texto": "Projeto Ultra-Secreto X: O orçamento de aquisições para 2027 será de 50 milhões.",
        "metadados": {"papel": "diretoria"} # Apenas diretores podem ver!
    },
    {
        "texto": "Senha do roteador do RH: rh_wifi_2026_seguro",
        "metadados": {"papel": "rh"} # Apenas RH
    }
]

def popular_banco():
    print("Iniciando o pipeline de ingestão...")
    
    with psycopg.connect(url_banco()) as conexao:
        with conexao.cursor() as cursor:
            for doc in documentos_teste:
                print(f"Gerando vetor para: '{doc['texto'][:30]}...'")
                
                # Chama a IA (Gemini) para transformar o texto em vetor
                vetor = get_embedding(doc["texto"])
                
                # Converte o metadado (dicionário Python) para formato JSON
                metadados_json = json.dumps(doc["metadados"])
                
                # Insere tudo no Supabase
                # Usamos %s para evitar injeção de SQL (segurança)
                sql = "INSERT INTO documentos (conteudo, metadados, embedding) VALUES (%s, %s, %s)"
                cursor.execute(sql, (doc["texto"], metadados_json, str(vetor)))
                
        conexao.commit()
        print("✅ Todos os documentos foram salvos com IA no Supabase!")

if __name__ == "__main__":
    popular_banco()
