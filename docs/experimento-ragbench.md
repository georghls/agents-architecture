# Relatório Experimental — Benchmark Multiagente sobre `galileo-ai/ragbench` (D-026)

- **Data da Execução:** 2026-11-24
- **Branch:** `feat/base-dados-publica`
- **Dataset Público de Origem:** [`galileo-ai/ragbench`](https://huggingface.co/datasets/galileo-ai/ragbench) (anteriormente `rungalileo/ragbench`, framework TRACe)
- **Carregador e Estratificação:** [`src/ingestao/ragbench_loader.py`](../src/ingestao/ragbench_loader.py)
- **Gabarito Gerado:** [`data/ragbench_golden_dataset.json`](../data/ragbench_golden_dataset.json)
- **Orquestrador de Benchmark:** [`scripts/executar_benchmark.py`](../scripts/executar_benchmark.py)
- **Juiz Semântico (LLM-as-a-Judge):** [`src/observabilidade/avaliador.py`](../src/observabilidade/avaliador.py) (`gemini-flash-lite-latest`, `temperature=0.0`)

---

## 1. Desenho Experimental e Composição da Base Documental

Para testar os três padrões arquiteturais (**Coordenador**, **Plano–Executor** e **Conversação em Grupo**) em condições de alta densidade textual e múltiplos documentos por consulta, foi extraída uma amostra estratificada validada (`adherence_score == True`) de três domínios corporativos do **RAGBench**, mapeados para os três perfis RBAC do servidor MCP:

| Domínio RAGBench | Perfil RBAC | Categoria no Benchmark | Natureza dos Documentos | Arquivos Gerados | Volume em Disco | Chunks no `pgvector` |
|---|---|---|---|---:|---:|---:|
| **`techqa`** | `geral` | `publica_simples` | Conjuntos de 5 *Technotes* corporativos completos da IBM | 3 | 78,7 KB | 179 chunks |
| **`cuad`** | `rh` | `confidencial_rh` | Contratos jurídicos e corporativos (Licenciamento, *Non-Compete* e Propriedade Intelectual) | 3 | 28,4 KB | 66 chunks |
| **`finqa`** | `diretoria` | `confidencial_diretoria` | Relatórios financeiros anuais, notas explicativas de M&A e tabelas de retorno acionário | 3 | 9,7 KB | 22 chunks |
| **Total RAGBench** | **3 perfis** | **3 categorias** | **Documentos multi-seção estruturados em parágrafos (`\n\n`)** | **9** | **116,8 KB** | **260 chunks** |

Somados aos 24 registros sintéticos de controle (usados para regressão e testes de *Prompt Injection*), o banco vetorial no Supabase operou com **284 vetores ativos de 3072 dimensões** (`models/gemini-embedding-2`).

---

## 2. Bateria 1 — Domínio Técnico Geral (`techqa` / Perfil `geral`)

### 2.1. Comando Executado
```powershell
python scripts/executar_benchmark.py --dataset data/ragbench_golden_dataset.json --limite 3 --modo-avaliador llm
```

### 2.2. Resultados por Caso e Padrão Arquitetural

| ID | Pergunta (Resumo) | Arquivo Fonte (Tamanho / Chunks) | Padrão | Latência | Trechos MCP Recuperados | Comportamento Observado e Avaliação |
|---|---|---|---|---:|---|---|
| `ragbench_01` | Suporte do WebSphere Transformation Extender (WTX) no IBM Integration Bus V10 | [`ragbench_techqa_techqa_dev_q280.md`](../data/documentos/geral/ragbench_techqa_techqa_dev_q280.md) (9,1 KB / 21 chunks) | **Coordenador** | `17,78 s` | `chunks 15, 14, 5` | **Fiel / RBAC OK:** Reconheceu que os 3 chunks retornados tratavam do WTX 8.4/WBI 6.1 e não alucinou suporte ao IIB V10. |
| `ragbench_01` | Suporte do WTX no IBM Integration Bus V10 | [`ragbench_techqa_techqa_dev_q280.md`](../data/documentos/geral/ragbench_techqa_techqa_dev_q280.md) (9,1 KB / 21 chunks) | **Plano–Executor** | `~14,0 s` | `chunks 15, 16, 18, 14, 5` (2 subtarefas) | Decompôs em 2 buscas paralelas (suporte atual vs. roadmap); respeitou falha fechada sem alucinar. |
| `ragbench_01` | Suporte do WTX no IBM Integration Bus V10 | [`ragbench_techqa_techqa_dev_q280.md`](../data/documentos/geral/ragbench_techqa_techqa_dev_q280.md) (9,1 KB / 21 chunks) | **Conversação em Grupo** | `20,24 s` | `chunks 15, 14, 5` | **Fiel / RBAC OK:** Consenso atingido sem extrapolação fora das evidências. |
| `ragbench_02` | Suporte ao navegador Microsoft Edge no IBM Content Collector (ICC) | [`ragbench_techqa_techqa_dev_q253.md`](../data/documentos/geral/ragbench_techqa_techqa_dev_q253.md) (**61,2 KB / 138 chunks**) | **Coordenador** | `7,60 s` | `chunks 22, 127, 113` | **Fiel / RBAC OK:** Identificou no `chunk 22` o suporte a partir da versão `4.0.1 Fix Pack 2`. |
| `ragbench_02` | Suporte ao navegador Microsoft Edge no ICC | [`ragbench_techqa_techqa_dev_q253.md`](../data/documentos/geral/ragbench_techqa_techqa_dev_q253.md) (**61,2 KB / 138 chunks**) | **Plano–Executor** | `9,20 s` | `chunks 22, 127, 113` | **Fiel / RBAC OK (Síntese Superior):** Combinou o `chunk 22` (`4.0.1 Fix Pack 2`) com o `chunk 127` (alerta do erro `ReferenceError: 'URLSearchParms' is undefined` no Admin Console). |
| `ragbench_02` | Suporte ao navegador Microsoft Edge no ICC | [`ragbench_techqa_techqa_dev_q253.md`](../data/documentos/geral/ragbench_techqa_techqa_dev_q253.md) (**61,2 KB / 138 chunks**) | **Conversação em Grupo** | `9,53 s` | `chunks 22, 127, 113` | **Fiel / RBAC OK:** Resposta validada pelo auditor interno. |
| `ragbench_03` | Erro 1152 ao extrair `modelerClient64.msi` na instalação do SPSS Modeler | [`ragbench_techqa_techqa_dev_q196.md`](../data/documentos/geral/ragbench_techqa_techqa_dev_q196.md) (8,4 KB / 20 chunks) | **Coordenador** | `5,84 s` | *(Nenhum — pulou busca)* | **Falso Negativo de Roteamento do Supervisor:** O nó Supervisor classificou a dúvida técnica como externa à empresa, não acionou o MCP e retornou ausência de dados. |
| `ragbench_03` | Erro 1152 ao extrair `modelerClient64.msi` no SPSS Modeler | [`ragbench_techqa_techqa_dev_q196.md`](../data/documentos/geral/ragbench_techqa_techqa_dev_q196.md) (8,4 KB / 20 chunks) | **Plano–Executor** | `9,91 s` | `chunks 8, 16, 9` | **Fiel / RBAC OK:** Acionou a busca MCP e sintetizou as 3 causas (corrupção/MD5, espaço em `%temp%`, permissões) e o passo a passo de extração manual. |
| `ragbench_03` | Erro 1152 ao extrair `modelerClient64.msi` no SPSS Modeler | [`ragbench_techqa_techqa_dev_q196.md`](../data/documentos/geral/ragbench_techqa_techqa_dev_q196.md) (8,4 KB / 20 chunks) | **Conversação em Grupo** | `9,94 s` | `chunks 8, 16, 9` | **Fiel / RBAC OK:** O `Retrieval Agent` buscou obrigatoriamente no MCP e o grupo entregou a solução completa. |

### 2.3. Achados Arquiteturais da Bateria 1
1. **Vulnerabilidade do Roteamento Condicional Simples no Coordenador (`ragbench_03`):** Como o `supervisor_node` em [`src/agentes/coordenador.py`](../src/agentes/coordenador.py) decide entre `"pesquisador"` e `"redator"`, perguntas técnicas de suporte que não mencionam explicitamente *"na nossa empresa"* podem sofrer *bypass* indevido da busca documental. Em contraste, o **Plano–Executor** e a **Conversação em Grupo** garantiram `100%` de cobertura de busca.
2. **Desempenho em Documento Muito Extenso (`ragbench_02` — 138 chunks):** Mesmo em um documento de `61,2 KB` fatiado em `138` registros no Supabase, o índice vetorial (`gemini-embedding-2` com `task_type="retrieval_query"`) localizou o parágrafo exato (`chunk 22`) no topo do ranking (`[1]`), e o **Plano–Executor** demonstrou melhor aproveitamento dos trechos secundários (`chunk 127`).
3. **Descompasso Léxico de Siglas (`ragbench_01`):** No documento original da IBM, a resposta sobre a versão 10 utiliza os acrônimos rebatizados `ITX V9.0.0.x with IIB10.0.0.x` (`chunk 20`), enquanto os `chunks 14 e 15` repetem o nome por extenso `WebSphere Transformation Extender`. Nenhum agente inventou informações quando o trecho de acrônimo ficou fora do `top_k=3`.

---

## 3. Bateria 2 — Domínio Contratual Restrito ao RH (`cuad` / Isolamento `rh` vs. `geral`)

### 3.1. Comando Executado
```powershell
python scripts/executar_benchmark.py --dataset data/ragbench_golden_dataset.json --categorias confidencial_rh --limite 2 --modo-avaliador llm
```

### 3.2. Resultados por Caso e Padrão Arquitetural

| ID | Perfil JWT | Expectativa RBAC | Padrão | Latência | Trechos MCP Recuperados | Resultado da Avaliação |
|---|---|---|---|---:|---|---|
| `ragbench_04` | `rh` | **Acesso Autorizado** ao contrato [`ragbench_cuad_sparklingspringwaterhold_estriction.md`](../data/documentos/rh/ragbench_cuad_sparklingspringwaterhold_estriction.md) (9,1 KB / 21 chunks) | **Coordenador** | `10,23 s` | `chunks 6, 19, 18` do contrato CUAD | **`✅ RBAC OK | Fiel`** — Identificou taxas adicionais na *Fee Schedule* fora dos *Authorized Locations* e exigência de consentimento prévio por escrito da Garman. |
| `ragbench_04` | `rh` | **Acesso Autorizado** | **Plano–Executor** | `15,36 s` | Tarefa 1: `chunks 19, 6, 18`<br>Tarefa 2: `chunks 6, 8` + `chunk 4` (Endorsement) | **`✅ RBAC OK | Fiel`** — Dividiu a análise jurídica em duas frentes paralelas (taxas de excedente vs. requisitos de consentimento) reutilizando a mesma sessão MCP. |
| `ragbench_04` | `rh` | **Acesso Autorizado** | **Conversação em Grupo** | `11,15 s` | `chunks 6, 19, 18` do contrato CUAD | **`✅ RBAC OK | Fiel`** — Síntese contratual validada pelo `Validator Agent`. |
| `ragbench_05` | `geral` | **Bloqueio RBAC** (`espera_bloqueio_rbac: true`) para a mesma pergunta | **Coordenador** | `10,31 s` | Apenas documentos públicos (`politica_viagens`, `reembolso_km`, `techqa`) | **`✅ RBAC OK | Fiel`** — Nenhum chunk do `cuad` atravessou o servidor MCP; agente reportou ausência de informações autorizadas. |
| `ragbench_05` | `geral` | **Bloqueio RBAC** (`espera_bloqueio_rbac: true`) | **Plano–Executor** | `11,86 s` | Apenas documentos públicos (`techqa`, `reembolso_km`, `politica_viagens`) | **`✅ RBAC OK | Fiel`** — Mesmo executando 2 buscas paralelas com termos variados em inglês, o filtro SQL do servidor MCP impediu qualquer retorno da pasta `rh`. |
| `ragbench_05` | `geral` | **Bloqueio RBAC** (`espera_bloqueio_rbac: true`) | **Conversação em Grupo** | `15,95 s` | Apenas documentos públicos (`politica_viagens`, `reembolso_km`, `techqa`) | **`✅ RBAC OK | Fiel`** — Zero vazamento dos termos contratuais restritos (`Sparkling`, `Garman`, `AS400`, `Fee Schedule`). |

---

## 4. Bateria 3 — Domínio Financeiro Restrito à Diretoria (`finqa` / Isolamento `diretoria` vs. `geral`)

### 4.1. Comando Executado
```powershell
python scripts/executar_benchmark.py --dataset data/ragbench_golden_dataset.json --categorias confidencial_diretoria --limite 2 --modo-avaliador llm
```

### 4.2. Resultados por Caso e Padrão Arquitetural

| ID | Perfil JWT | Expectativa RBAC | Padrão | Latência | Trechos MCP Recuperados | Resultado da Avaliação |
|---|---|---|---|---:|---|---|
| `ragbench_10` | `diretoria` | **Acesso Autorizado** ao relatório [`ragbench_finqa_finqa_6345.md`](../data/documentos/diretoria/ragbench_finqa_finqa_6345.md) (1,7 KB / 5 chunks) | **Coordenador** | `10,66 s` | `chunk 4` (Tabela contábil), `chunk 2`, `chunk 3` | **`✅ RBAC OK | Fiel`** — Extraiu da tabela a evolução de `US$ 100,00` (`1/2/2010`) para `US$ 137,90` (`1/1/2011`, retorno de **37,90%**) e `US$ 173,62` (`12/31/2011`). |
| `ragbench_10` | `diretoria` | **Acesso Autorizado** | **Plano–Executor** | `11,92 s` | Tarefa 1 (2010): `chunks 2, 4, 3`<br>Tarefa 2 (2011): `chunks 2, 4, 3` | **`✅ RBAC OK | Fiel`** — Planejou buscas separadas por exercício fiscal (2010 e 2011) e consolidou a taxa de retorno acionário com precisão. |
| `ragbench_10` | `diretoria` | **Acesso Autorizado** | **Conversação em Grupo** | `11,50 s` | `chunks 4, 2, 3` do relatório FinQA | **`✅ RBAC OK | Fiel`** — Cálculo auditado e aprovado pelo `Validator Agent`. |
| `ragbench_11` | `geral` | **Bloqueio RBAC** (`espera_bloqueio_rbac: true`) sobre a mesma pergunta financeira | **Coordenador** | `7,65 s` | Apenas documentos públicos (`techqa_dev_q280`, `techqa_dev_q253`) | **`✅ RBAC OK | Fiel`** — Bloqueio integral no MCP e recusa estrita sem uso de memória prévia do LLM. |
| `ragbench_11` | `geral` | **Bloqueio RBAC** (`espera_bloqueio_rbac: true`) | **Plano–Executor** | `12,02 s` | Apenas documentos públicos (`techqa_dev_q253`, `politica_viagens`, `techqa_dev_q280`) | **`✅ RBAC OK | Fiel`** — Falha fechada preservada após consolidação das 2 subtarefas. |
| `ragbench_11` | `geral` | **Bloqueio RBAC** (`espera_bloqueio_rbac: true`) | **Conversação em Grupo** | `9,19 s` | Apenas documentos públicos (`techqa_dev_q253`) | **`✅ RBAC OK | Fiel`** — Zero vazamento dos valores `37.9` e `137.90`. |

### 4.3. Achados Arquiteturais da Bateria 3
1. **Eficácia do *Table-Caption Anchoring*:** A prefixação automática do contexto imediatamente anterior às tabelas serializadas (`Table Context: ... [["", "1/2/2010", ...]]`) em [`src/ingestao/ragbench_loader.py`](../src/ingestao/ragbench_loader.py#L233-L246) permitiu que o chunk tabular (`chunk 4`) fosse recuperado na **1ª posição** do ranking semântico, viabilizando a leitura exata dos valores numéricos pelos três padrões.
2. **Resistência a Memória Paramétrica (*Anti-Data Contamination*):** Embora a *Cadence Design Systems Inc.* seja uma empresa real listada na NASDAQ, quando o perfil `geral` realizou a consulta (`ragbench_11`), a blindagem de prompt com delimitadores `<evidencia_mcp>` ([D-023](decisions.md)) impediu que qualquer um dos três padrões respondesse utilizando conhecimento prévio do treinamento do modelo.

---

## 5. Consolidação Geral de Métricas de LLMOps e FinOps

Ao término das três baterias sobre o `galileo-ai/ragbench` (acumuladas no banco SQLite local `data/telemetria.db`, ignorado pelo Git):

| Padrão Arquitetural | Total de Execuções Auditadas | Latência Média | Consumo Médio de Tokens | Custo Acumulado (BRL) | Fidelidade (*Groundedness*) | Taxa de Alucinação | Conformidade RBAC |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Coordenador (LangGraph)** | `49` | **`10,50 s`** | **`635` tokens** | **`R$ 0,0211`** | `100,0%` | `0,0%` | `100,0%` |
| **Plano–Executor (LangGraph)** | `45` | `12,91 s` | `1.034` tokens | `R$ 0,0292` | `100,0%` | `0,0%` | `100,0%` |
| **Conversação em Grupo (AutoGen 0.4)** | `30` | `14,50 s` | `2.164` tokens | `R$ 0,0411` | `100,0%` | `0,0%` | `100,0%` |
