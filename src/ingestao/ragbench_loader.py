"""Carregador estratificado de documentos robustos do benchmark `galileo-ai/ragbench` (`rungalileo/ragbench`).

Conecta-se à API REST do Hugging Face Datasets Server (`datasets-server.huggingface.co`),
seleciona casos validados (`adherence_score == True`) de três domínios corporativos densos e os
mapeia para os três perfis RBAC do projeto (D-026):
  - `techqa` -> perfil `geral` (conjuntos de 5 Technotes corporativos completos da IBM, ~15-22 KB/arquivo)
  - `cuad`   -> perfil `rh` (contratos corporativos extensos de licenciamento, IP e non-compete, ~10-15 KB/arquivo)
  - `finqa`  -> perfil `diretoria` (relatórios financeiros executivos integrais com tabelas e M&A)

Estrutura todas as passagens em parágrafos de ~500 caracteres separados por `\n\n`,
permitindo que `segmentar_documento` (`src/ingestao/ingestao.py`) divida cada arquivo
em múltiplos chunks granulares de até 700 caracteres no `pgvector`.
"""

import argparse
import json
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

HF_DATASET_ID = "galileo-ai/ragbench"
HF_ROWS_API = "https://datasets-server.huggingface.co/rows"

MAPEAMENTO_DOMINIOS_RBAC: dict[str, dict[str, str]] = {
    "techqa": {
        "papel": "geral",
        "categoria": "publica_simples",
        "titulo_prefixo": "RAGBench Base Técnica Corporativa (TechQA)",
    },
    "cuad": {
        "papel": "rh",
        "categoria": "confidencial_rh",
        "titulo_prefixo": "RAGBench Contrato Corporativo (CUAD)",
    },
    "finqa": {
        "papel": "diretoria",
        "categoria": "confidencial_diretoria",
        "titulo_prefixo": "RAGBench Relatório Financeiro Executivo (FinQA)",
    },
}

_STOPWORDS_EN = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were",
    "have", "has", "had", "not", "but", "what", "when", "where", "which", "who",
    "will", "would", "could", "should", "can", "may", "based", "context", "provided",
    "according", "document", "documents", "agreement", "section", "states", "there",
    "their", "they", "them", "these", "those", "into", "over", "under", "between",
    "through", "during", "before", "after", "above", "below", "yes", "total", "number",
}


def sanitizar_id(raw_id: str) -> str:
    """Converte o ID bruto do RAGBench em um identificador curto e seguro para nome de arquivo."""
    limpo = re.sub(r"[^a-zA-Z0-9]+", "_", str(raw_id)).strip("_").lower()
    if len(limpo) > 36:
        limpo = limpo[:24] + "_" + limpo[-10:]
    return limpo or "item"


def buscar_linhas_hf(
    config: str,
    split: str = "test",
    offset: int = 0,
    length: int = 35,
    timeout: int = 30,
) -> list[dict]:
    """Consulta a API REST do Hugging Face Datasets Server e retorna a lista de `row` dicts."""
    params = urllib.parse.urlencode(
        {
            "dataset": HF_DATASET_ID,
            "config": config,
            "split": split,
            "offset": offset,
            "length": length,
        }
    )
    url = f"{HF_ROWS_API}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "unicamp-agents-architecture/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return [item["row"] for item in payload.get("rows", []) if "row" in item]


def agrupar_sentencas_em_paragrafos(sentencas: list[str], alvo_chars: int = 480) -> str:
    """Agrupa uma lista de sentenças em parágrafos bem dimensionados separados por `\\n\\n`.

    Isso garante que `segmentar_documento` (`tamanho_max=700`) consiga subdividir
    documentos extensos de 15 KB–25 KB em dezenas de chunks semânticos <= 700 chars.
    """
    paragrafos: list[str] = []
    buffer: list[str] = []
    tamanho_atual = 0

    for s in sentencas:
        s_limpa = re.sub(r"\s+", " ", str(s)).strip()
        if not s_limpa:
            continue
        # Se uma única sentença já for muito longa (ex.: tabela ou lista de contrato),
        # quebra em blocos de ~480 caracteres nos espaços para não estourar 700 chars.
        if len(s_limpa) > alvo_chars:
            if buffer:
                paragrafos.append(" ".join(buffer))
                buffer = []
                tamanho_atual = 0
            palavras = s_limpa.split(" ")
            sub_buf: list[str] = []
            sub_tam = 0
            for pal in palavras:
                if sub_buf and (sub_tam + len(pal) + 1) > alvo_chars:
                    paragrafos.append(" ".join(sub_buf))
                    sub_buf = [pal]
                    sub_tam = len(pal)
                else:
                    sub_buf.append(pal)
                    sub_tam += len(pal) + (1 if sub_tam else 0)
            if sub_buf:
                paragrafos.append(" ".join(sub_buf))
            continue

        if buffer and (tamanho_atual + len(s_limpa) + 1) > alvo_chars:
            paragrafos.append(" ".join(buffer))
            buffer = [s_limpa]
            tamanho_atual = len(s_limpa)
        else:
            buffer.append(s_limpa)
            tamanho_atual += len(s_limpa) + (1 if tamanho_atual else 0)

    if buffer:
        paragrafos.append(" ".join(buffer))

    return "\n\n".join(paragrafos)


def extrair_janela_contextual_sentencas(
    row: dict,
    janela: int = 16,
    max_chars: int = 14000,
) -> str:
    """Extrai o preâmbulo do contrato e uma janela ampla de cláusulas ao redor de
    `all_relevant_sentence_keys`, formatando em parágrafos separados por `\\n\\n`.

    Para contratos do CUAD (originalmente 30 KB a 60 KB), gera documentos robustos
    de ~10 KB a 14 KB (~18 a 25 chunks por contrato) mantendo todas as cláusulas
    de evidência integralmente preservadas.
    """
    docs_sents = row.get("documents_sentences") or []
    rel_keys = set(row.get("all_relevant_sentence_keys") or [])

    if not docs_sents or not isinstance(docs_sents, list):
        docs_raw = row.get("documents") or []
        sentencas_fallback = re.split(r"(?<=[.;])\s+", "\n\n".join(str(d) for d in docs_raw)[:max_chars])
        return "## Excerpt from Source Document 1\n" + agrupar_sentencas_em_paragrafos(sentencas_fallback)

    blocos_extraidos: list[str] = []
    for doc_idx, sent_list in enumerate(docs_sents):
        if not isinstance(sent_list, list) or not sent_list:
            continue

        # Inclui preâmbulo substancial do contrato (primeiras 18 sentenças) + janela ampla
        indices_selecionados: set[int] = set(range(min(18, len(sent_list))))
        for i, par in enumerate(sent_list):
            if isinstance(par, (list, tuple)) and len(par) >= 2:
                chave = str(par[0])
                if chave in rel_keys:
                    for vizinho in range(max(0, i - janela), min(len(sent_list), i + janela + 1)):
                        indices_selecionados.add(vizinho)

        # Divide em seções contratuais a cada salto de índice ou a cada ~10 sentenças
        grupos_secao: list[list[str]] = []
        grupo_atual: list[str] = []
        ultimo_idx = -1

        for idx in sorted(indices_selecionados):
            par = sent_list[idx]
            if not isinstance(par, (list, tuple)) or len(par) < 2:
                continue
            texto_sent = str(par[1]).strip()
            if not texto_sent:
                continue
            if (ultimo_idx != -1 and idx > ultimo_idx + 1) or len(grupo_atual) >= 12:
                if grupo_atual:
                    grupos_secao.append(grupo_atual)
                    grupo_atual = []
            grupo_atual.append(texto_sent)
            ultimo_idx = idx

        if grupo_atual:
            grupos_secao.append(grupo_atual)

        for sec_idx, sents_sec in enumerate(grupos_secao, 1):
            corpo_paragrafos = agrupar_sentencas_em_paragrafos(sents_sec, alvo_chars=480)
            if corpo_paragrafos:
                blocos_extraidos.append(
                    f"## Contract Section {doc_idx + 1}.{sec_idx}\n{corpo_paragrafos}"
                )

    resultado = "\n\n".join(blocos_extraidos).strip()
    if len(resultado) > max_chars:
        resultado = resultado[:max_chars].rsplit("\n\n", 1)[0]
    return resultado


def formatar_documento_markdown(subset: str, row: dict) -> str:
    """Converte um registro do RAGBench em um documento Markdown robusto e multi-seção.

    1. Inicia diretamente com o título de nível 1 (# ) seguido pelas seções (## ),
       para que `segmentar_documento` não gere um chunk extra apenas com metadados.
    2. Usa `documents_sentences` (ou divisão sentencial) para estruturar cada seção
       em parágrafos de ~480 caracteres separados por `\\n\\n`, garantindo dezenas de
       chunks bem calibrados sem truncar os documentos originais do TechQA e FinQA.
    """
    info = MAPEAMENTO_DOMINIOS_RBAC[subset]
    doc_id = row.get("id", "unknown")
    cabecalho = f"# {info['titulo_prefixo']} — Caso {doc_id}"

    if subset == "cuad":
        corpo = extrair_janela_contextual_sentencas(row, janela=16, max_chars=14000)
        return f"{cabecalho}\n\n{corpo}\n"

    docs_sents = row.get("documents_sentences") or []
    documentos = row.get("documents") or []
    secoes: list[str] = []

    if docs_sents and isinstance(docs_sents, list):
        ultima_legenda = ""
        for idx, sent_list in enumerate(docs_sents, 1):
            if not isinstance(sent_list, list) or not sent_list:
                continue
            textos = [str(par[1]).strip() for par in sent_list if isinstance(par, (list, tuple)) and len(par) >= 2]
            if textos and textos[0].startswith("[[") and ultima_legenda:
                textos = [f"Table Context: {ultima_legenda}"] + textos
            if textos:
                ultima_legenda = textos[-1]
            paragrafos = agrupar_sentencas_em_paragrafos(textos, alvo_chars=480)
            if paragrafos:
                secoes.append(f"## Context Document {idx}\n{paragrafos}")
    else:
        for idx, doc_texto in enumerate(documentos, 1):
            texto_limpo = str(doc_texto).strip()
            if not texto_limpo:
                continue
            sents = re.split(r"(?<=[.?!])\s+", texto_limpo)
            paragrafos = agrupar_sentencas_em_paragrafos(sents, alvo_chars=480)
            secoes.append(f"## Context Document {idx}\n{paragrafos}")

    corpo = "\n\n".join(secoes)
    return f"{cabecalho}\n\n{corpo}\n"


def extrair_termos_chave_resposta(
    resposta: str,
    texto_documento: str,
    pergunta: str = "",
    max_termos: int = 2,
) -> list[str]:
    """Extrai termos factuais (números, porcentagens ou termos técnicos) que constam
    simultaneamente na resposta de referência do RAGBench e no documento fonte,
    excluindo termos que já aparecem no enunciado da pergunta."""
    resp_str = str(resposta or "").strip()
    doc_lower = str(texto_documento or "").lower()
    perg_lower = str(pergunta or "").lower()

    candidatos: list[str] = []

    # 1. Prioriza valores numéricos/percentuais/monetários presentes na resposta e no documento (mas não na pergunta)
    numeros = re.findall(r"\b\d+(?:[.,]\d+)?%?\b", resp_str)
    for num in numeros:
        n_low = num.lower()
        if len(num) >= 2 and n_low in doc_lower and n_low not in perg_lower and num not in candidatos:
            candidatos.append(num)
            if len(candidatos) >= max_termos:
                return candidatos

    # 2. Palavras substantivas distintivas (>= 5 letras) que aparecem na resposta e no documento (mas não na pergunta)
    palavras = re.findall(r"\b[A-Za-z][A-Za-z0-9_-]{4,}\b", resp_str)
    for pal in palavras:
        p_low = pal.lower()
        if p_low not in _STOPWORDS_EN and p_low in doc_lower and p_low not in perg_lower:
            if not any(p_low == c.lower() for c in candidatos):
                candidatos.append(pal)
                if len(candidatos) >= max_termos:
                    return candidatos

    return candidatos or ([resp_str.split()[0]] if resp_str else [])


def selecionar_casos_validados(linhas: list[dict], subset: str, quantidade: int) -> list[dict]:
    """Filtra registros com `adherence_score == True` e evidência clara para compor a amostra."""
    selecionados: list[dict] = []
    for row in linhas:
        if row.get("adherence_score") is not True:
            continue
        rel_keys = row.get("all_relevant_sentence_keys") or []
        if not rel_keys:
            continue
        if subset == "cuad" and len(rel_keys) > 12:
            continue

        md_texto = formatar_documento_markdown(subset, row)
        termos = extrair_termos_chave_resposta(
            row.get("response", ""),
            md_texto,
            pergunta=row.get("question", ""),
        )
        if not termos:
            continue

        selecionados.append(row)
        if len(selecionados) >= quantidade:
            break

    return selecionados


def construir_amostra_ragbench(
    por_dominio: int = 3,
    diretorio_docs: Path | None = None,
    caminho_saida_json: Path | None = None,
    dados_pre_carregados: dict[str, list[dict]] | None = None,
) -> dict:
    """Baixa a amostra estratificada do RAGBench, grava os arquivos Markdown robustos nas pastas RBAC
    e gera o arquivo `data/ragbench_golden_dataset.json`."""
    pasta_docs = diretorio_docs or (RAIZ / "data" / "documentos")
    arquivo_dataset = caminho_saida_json or (RAIZ / "data" / "ragbench_golden_dataset.json")

    arquivos_gerados: list[Path] = []
    itens_benchmark: list[dict] = []
    contador_id = 1

    for subset, meta in MAPEAMENTO_DOMINIOS_RBAC.items():
        papel = meta["papel"]
        categoria = meta["categoria"]
        pasta_papel = pasta_docs / papel
        pasta_papel.mkdir(parents=True, exist_ok=True)

        if dados_pre_carregados and subset in dados_pre_carregados:
            linhas_brutas = dados_pre_carregados[subset]
        else:
            linhas_brutas = buscar_linhas_hf(config=subset, split="test", offset=0, length=40)

        casos = selecionar_casos_validados(linhas_brutas, subset=subset, quantidade=por_dominio)

        for row in casos:
            slug = sanitizar_id(row.get("id", f"{subset}_{contador_id}"))
            nome_md = f"ragbench_{subset}_{slug}.md"
            caminho_md = pasta_papel / nome_md

            conteudo_md = formatar_documento_markdown(subset, row)
            caminho_md.write_text(conteudo_md, encoding="utf-8")
            arquivos_gerados.append(caminho_md)

            pergunta = str(row.get("question", "")).strip()
            termos_chave = extrair_termos_chave_resposta(
                row.get("response", ""),
                conteudo_md,
                pergunta=pergunta,
                max_termos=2,
            )

            # 1. Caso autorizado (usuário com o perfil correto do domínio)
            itens_benchmark.append(
                {
                    "id": f"ragbench_{contador_id:02d}",
                    "categoria": categoria,
                    "pergunta": pergunta,
                    "perfil_esperado": papel,
                    "resposta_esperada_contem": termos_chave,
                    "resposta_esperada_nao_contem": [],
                    "deve_conter_evidencia": True,
                    "espera_bloqueio_rbac": False,
                    "descricao": f"[{HF_DATASET_ID}/{subset}] Consulta autorizada para perfil '{papel}' (caso {row.get('id')}).",
                    "ragbench_id": row.get("id"),
                    "ragbench_subset": subset,
                    "documento_fonte": nome_md,
                }
            )
            contador_id += 1

            # 2. Para domínios restritos (rh / diretoria), adiciona caso pareado de bloqueio RBAC sob perfil 'geral'
            if papel in ("rh", "diretoria"):
                itens_benchmark.append(
                    {
                        "id": f"ragbench_{contador_id:02d}",
                        "categoria": categoria,
                        "pergunta": pergunta,
                        "perfil_esperado": "geral",
                        "resposta_esperada_contem": [],
                        "resposta_esperada_nao_contem": termos_chave,
                        "deve_conter_evidencia": False,
                        "espera_bloqueio_rbac": True,
                        "descricao": (
                            f"[{HF_DATASET_ID}/{subset}] Bloqueio RBAC: perfil 'geral' não pode acessar "
                            f"evidências restritas a '{papel}' (caso {row.get('id')})."
                        ),
                        "ragbench_id": row.get("id"),
                        "ragbench_subset": subset,
                        "documento_fonte": nome_md,
                    }
                )
                contador_id += 1

    arquivo_dataset.parent.mkdir(parents=True, exist_ok=True)
    arquivo_dataset.write_text(
        json.dumps(itens_benchmark, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return {
        "arquivos_gerados": [str(p) for p in arquivos_gerados],
        "total_arquivos": len(arquivos_gerados),
        "total_perguntas_benchmark": len(itens_benchmark),
        "caminho_dataset": str(arquivo_dataset),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Importador estratificado de documentos robustos do galileo-ai/ragbench com mapeamento RBAC"
    )
    parser.add_argument(
        "--por-dominio",
        type=int,
        default=3,
        help="Quantidade de casos validados a importar por domínio (techqa, cuad, finqa).",
    )
    parser.add_argument(
        "--ingerir",
        action="store_true",
        help="Sincroniza o Supabase (removendo chunks obsoletos e ingerindo os novos via popular_banco).",
    )
    args = parser.parse_args()

    print("=" * 72)
    print(f"📥 Baixando documentos robustos de '{HF_DATASET_ID}' ({args.por_dominio} casos/domínio)")
    print("=" * 72)

    resumo = construir_amostra_ragbench(por_dominio=args.por_dominio)
    print(f"- Documentos Markdown gerados : {resumo['total_arquivos']}")
    for arq in resumo["arquivos_gerados"]:
        p = Path(arq)
        kb = p.stat().st_size / 1024.0
        print(f"  • {p.relative_to(RAIZ)} ({kb:.1f} KB)")
    print(f"- Casos no benchmark JSON     : {resumo['total_perguntas_benchmark']}")
    print(f"- Arquivo salvo em            : {Path(resumo['caminho_dataset']).relative_to(RAIZ)}")

    if args.ingerir:
        import psycopg
        from src.config import url_banco
        from src.ingestao.ingestao import carregar_documentos_de_arquivos, popular_banco, documentos_teste

        textos_validos = {d["texto"] for d in documentos_teste} | {
            d["texto"] for d in carregar_documentos_de_arquivos()
        }
        with psycopg.connect(url_banco(), prepare_threshold=None) as conexao:
            with conexao.cursor() as cursor:
                cursor.execute("SELECT id, conteudo FROM documentos")
                obsoletos = [row[0] for row in cursor.fetchall() if row[1] not in textos_validos]
                if obsoletos:
                    cursor.execute("DELETE FROM documentos WHERE id = ANY(%s)", (obsoletos,))
                    print(f"- Chunks obsoletos (TOTVS / versões anteriores) removidos do banco: {len(obsoletos)}")
            conexao.commit()

        popular_banco()


if __name__ == "__main__":
    main()
