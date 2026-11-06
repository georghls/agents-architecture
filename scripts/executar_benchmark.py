"""Pipeline automatizado de Benchmark comparativo para o Estudo Dirigido (Fase 4).

Lê o conjunto de perguntas padronizadas (data/golden_dataset.json),
executa as perguntas nos três padrões arquiteturais (Coordenador, Plano–Executor, Grupo),
coleta telemetria no SQLite (data/telemetria.db) e avalia fidelidade, relevância e RBAC.

Uso:
    python scripts/executar_benchmark.py --limite 3
    python scripts/executar_benchmark.py --padroes coordenador plano_executor --modo-avaliador llm
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

# Garante saída UTF-8 no terminal Windows para caracteres especiais e emojis
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.agentes.coordenador import executar_coordenador
from src.agentes.plano_executor import executar_plano_executor
from src.agentes.conversa_grupo import executar_conversa_grupo
from src.observabilidade.telemetria import (
    inicializar_banco,
    obter_resumo_estatistico,
    obter_metricas_qualidade,
    iniciar_rastreamento,
    obter_evidencias_execucao,
)
from src.observabilidade.avaliador import avaliar_execucao

CAMINHO_DATASET_PADRAO = RAIZ / "data" / "golden_dataset.json"
CAMINHO_BANCO_PADRAO = RAIZ / "data" / "telemetria.db"
PADROES_DISPONIVEIS = ["coordenador", "plano_executor", "conversa_grupo"]


def parse_args():
    parser = argparse.ArgumentParser(description="Orquestrador de Benchmark Multiagente e LLMOps")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=CAMINHO_DATASET_PADRAO,
        help="Caminho do arquivo JSON com o Golden Dataset.",
    )
    parser.add_argument(
        "--banco",
        type=Path,
        default=CAMINHO_BANCO_PADRAO,
        help="Caminho do arquivo SQLite onde as métricas serão gravadas.",
    )
    parser.add_argument(
        "--padroes",
        nargs="+",
        choices=PADROES_DISPONIVEIS,
        default=PADROES_DISPONIVEIS,
        help="Padrões arquiteturais a serem avaliados.",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help="Quantidade máxima de perguntas do dataset a executar (útil para testes rápidos).",
    )
    parser.add_argument(
        "--categorias",
        nargs="+",
        default=None,
        help="Filtrar categorias específicas (ex: publica_simples confidencial_diretoria).",
    )
    parser.add_argument(
        "--modo-avaliador",
        choices=["deterministico", "llm"],
        default="deterministico",
        help="Modo de julgamento de qualidade: 'deterministico' (regras locais sem custo) ou 'llm' (Gemini Juiz).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Pausa em segundos entre requisições para evitar rate limit (HTTP 429).",
    )
    return parser.parse_args()


def imprimir_tabela_resumo(banco_path: Path):
    """Exibe no terminal a matriz comparativa agregada entre os três padrões."""
    resumo_op = obter_resumo_estatistico(banco_path)
    resumo_qual = obter_metricas_qualidade(banco_path)

    if not resumo_op:
        print("\n[Aviso] Nenhuma execução registrada no banco para consolidação.")
        return

    print("\n" + "=" * 90)
    print("           RELATÓRIO COMPARATIVO DE LLMOPS — ESTUDO DIRIGIDO UNICAMP")
    print("=" * 90)
    cabecalho = (
        f"{'Padrão':<18} | {'Execuções':<9} | {'Lat. Média':<11} | {'Tokens':<9} | "
        f"{'Custo BRL':<11} | {'Fidelidade':<10} | {'Alucinação':<10} | {'RBAC OK':<7}"
    )
    print(cabecalho)
    print("-" * 90)

    for padrao in PADROES_DISPONIVEIS:
        op = resumo_op.get(padrao, {})
        qual = resumo_qual.get(padrao, {})

        total_exec = op.get("total_execucoes", 0)
        if total_exec == 0:
            print(f"{padrao:<18} | (Sem execuções registradas)")
            continue

        latencia = f"{op.get('latencia_media_ms', 0) / 1000.0:.2f} s"
        tokens = f"{int(op.get('tokens_medios', 0)):,}"
        custo_brl = f"R$ {op.get('custo_total_brl', 0):.4f}"

        fidelidade = f"{qual.get('fidelidade_media', 0.0) * 100:.1f}%" if qual else "N/A"
        taxa_aluc = f"{qual.get('taxa_alucinacao', 0.0) * 100:.1f}%" if qual else "N/A"
        rbac_ok = f"{qual.get('rbac_conformidade_media', 1.0) * 100:.1f}%" if qual else "N/A"

        linha = (
            f"{padrao:<18} | {total_exec:<9} | {latencia:<11} | {tokens:<9} | "
            f"{custo_brl:<11} | {fidelidade:<10} | {taxa_aluc:<10} | {rbac_ok:<7}"
        )
        print(linha)

    print("=" * 90 + "\n")


def main():
    args = parse_args()

    print("=" * 70)
    print("INICIANDO BENCHMARK MULTIAGENTE E LLMOPS")
    print("=" * 70)
    print(f"- Dataset de entrada : {args.dataset}")
    print(f"- Banco SQLite       : {args.banco}")
    print(f"- Padrões testados   : {', '.join(args.padroes)}")
    print(f"- Modo do Avaliador  : {args.modo_avaliador}")
    print(f"- Pausa entre buscas : {args.delay} s")

    inicializar_banco(args.banco)

    with open(args.dataset, "r", encoding="utf-8") as f:
        perguntas = json.load(f)

    if args.categorias:
        perguntas = [p for p in perguntas if p.get("categoria") in args.categorias]

    if args.limite:
        perguntas = perguntas[:args.limite]

    total_perguntas = len(perguntas)
    print(f"- Total de perguntas selecionadas: {total_perguntas}")
    print("-" * 70)

    for i, item in enumerate(perguntas, 1):
        item_id = item["id"]
        pergunta = item["pergunta"]
        papel = item["perfil_esperado"]
        categoria = item["categoria"]

        print(f"\n[{i}/{total_perguntas}] [{categoria.upper()}] ID: {item_id}")
        print(f"Pergunta: '{pergunta}' (Perfil: {papel})")

        for padrao in args.padroes:
            ts_str = datetime.now(timezone.utc).strftime("%H%M%S")
            run_id = f"bench_{padrao}_{item_id}_{ts_str}"

            print(f"  -> Executando [{padrao}] (run_id: {run_id})...", end="", flush=True)
            t0 = time.perf_counter()

            try:
                resposta = ""
                if padrao == "coordenador":
                    resposta = executar_coordenador(
                        pergunta=pergunta,
                        role=papel,
                        exibir_metricas=False,
                        run_id=run_id,
                    )
                elif padrao == "plano_executor":
                    resposta = executar_plano_executor(
                        pergunta=pergunta,
                        role=papel,
                        exibir_metricas=False,
                        run_id=run_id,
                    )
                elif padrao == "conversa_grupo":
                    resultado_grupo = executar_conversa_grupo(
                        pergunta=pergunta,
                        papel=papel,
                        max_mensagens=9,
                        run_id=run_id,
                    )
                    resposta = resultado_grupo.get("resposta_final", "")

                duracao = time.perf_counter() - t0
                contexto_mcp = obter_evidencias_execucao(run_id, caminho_banco=args.banco)

                # Avalia qualidade e RBAC (com o contexto_mcp real recuperado - D-024)
                eval_res = avaliar_execucao(
                    run_id=run_id,
                    pergunta=pergunta,
                    resposta=resposta,
                    contexto_mcp=contexto_mcp,
                    papel_usuario=papel,
                    termos_proibidos=item.get("resposta_esperada_nao_contem"),
                    termos_obrigatorios=item.get("resposta_esperada_contem"),
                    espera_bloqueio_rbac=item.get("espera_bloqueio_rbac", False),
                    juiz_llm=args.modo_avaliador,
                    salvar_no_banco=True,
                    caminho_banco=args.banco,
                )

                status_rbac = "✅ RBAC OK" if not eval_res.falha_seguranca else "❌ VAZAMENTO"
                status_aluc = "🚨 Alucinação" if eval_res.houve_alucinacao else "Fiel"
                print(f" Concluído em {duracao:.2f}s | {status_rbac} | {status_aluc}")

            except Exception as erro:
                print(f" ❌ FALHA: {erro}")
                # Registra a falha na telemetria
                with iniciar_rastreamento(padrao, pergunta, papel, run_id, args.banco) as t_err:
                    t_err.sucesso = False
                    t_err.erro = str(erro)

            # Pausa defensiva entre chamadas
            if args.delay > 0:
                time.sleep(args.delay)

    imprimir_tabela_resumo(args.banco)


if __name__ == "__main__":
    main()
