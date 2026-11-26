# Engenharia de Software para IA: Sistemas Multi-Agentes (MCP e LLMOps)

Repositório do estudo dirigido focado no projeto, integração segura e operação de arquiteturas multiagentes para consulta a bases documentais corporativas com controle de acesso estrito (RBAC).

---

## 📌 Visão Geral do Projeto

O objetivo deste projeto é implementar, instrumentar e comparar experimentalmente três padrões arquiteturais de sistemas multiagentes ao longo das 5 fases do estudo dirigido (**Desenho, Integração Segura MCP, Orquestração Multiagentes, LLMOps/Gerenciador de Agentes e Relatório Técnico**):
1. **Coordenador (*Supervisor Pattern*)** — Implementado com **LangGraph** (concluído e testado)
2. **Plano–Executor (*Plan-and-Execute / Fan-Out*)** — Implementado com **LangGraph** (concluído e testado)
3. **Conversação em Grupo (*Group Chat*)** — Implementado com **Microsoft AutoGen 0.4+** (concluído e testado)

Todos os padrões são avaliados sob o mesmo corpus sintético e sobre a amostra estratificada do benchmark público **`galileo-ai/ragbench`** (`techqa`, `cuad`, `finqa`), com observabilidade em SQLite, FinOps versionado, juiz semântico *LLM-as-a-Judge* e Gerenciador de Agentes em Streamlit.

### Regra Fundamental de Arquitetura
Os agentes e modelos de linguagem (LLM) **nunca acessam o banco de dados diretamente** nem possuem privilégios declarados por prompt. Toda recuperação documental é obrigatoriamente intermediada por um servidor **Model Context Protocol (MCP)** via transporte `stdio` com autenticação criptográfica **JWT (HS256)**, garantindo que o controle de acesso baseado em papel (RBAC — `geral`, `rh`, `diretoria`) seja aplicado no nível de dados e na camada de protocolo.

---

## 🏗️ Arquitetura do Sistema

O projeto adota uma arquitetura híbrida projetada para contornar restrições de execução de bibliotecas binárias locais no ambiente Windows (AppLocker/Antivírus), garantindo estabilidade e escalabilidade:

```
[Usuário / Aplicação]
         │
         ▼
[Orquestração de Agentes (LangGraph / AutoGen)]
         │
         ▼ (Invocação de Tool via cliente MCP)
[Servidor MCP (src/mcp/server.py via stdio)]
         ├───▶ [Embeddings Semânticos: Google Gemini (gemini-embedding-2)]
         └───▶ [Banco Vetorial + RBAC: PostgreSQL na nuvem (Supabase pgvector)]
```

- **Persistência Unificada (Supabase):** PostgreSQL com extensão `pgvector`. A mesma tabela (`documentos`) armazena conteúdo textual, metadados de controle de acesso (`JSONB`) e vetores semânticos de 3072 dimensões.
- **Modelos Cognitivos (Google Gemini):**
  - Embeddings: `models/gemini-embedding-2` (3072 dimensões).
  - LLM Chat: `gemini-flash-lite-latest` (ou modelo configurável via `GEMINI_MODEL`).
- **Protocolo de Integração (MCP):** SDK Python oficial (`mcp`) utilizando transporte `stdio` para comunicação determinística por subprocesso.

---

## 📂 Estrutura do Repositório

```text
├── AGENTS.md                        # Instruções de contexto e governança do estudo dirigido
├── pyproject.toml                   # Configuração do projeto, dependências e marcadores pytest
├── requirements.txt                 # Dependências para instalação via pip
├── .env.example                     # Modelo das variáveis de ambiente necessárias
├── .gitignore                       # Regras completas de exclusão de artefatos, bancos e segredos
│
├── data/                            # Corpus documental sintético, RAGBench e gabaritos
│   ├── golden_dataset.json          # Gabarito fixo com 24 cenários (públicos, RBAC e injection)
│   ├── ragbench_golden_dataset.json # Gabarito estratificado do benchmark galileo-ai/ragbench
│   └── documentos/                  # Documentos Markdown segregados por perfil (geral, rh, diretoria)
│
├── docs/                            # Documentação técnica e acadêmica completa
│   ├── relatorio_tecnico_final.md   # Relatório técnico consolidado (Fases 1 a 5)
│   ├── experimento-ragbench.md      # Resultados experimentais sobre galileo-ai/ragbench (D-026/D-027)
│   ├── architecture.md              # Fronteiras e responsabilidades arquiteturais
│   ├── decisions.md                 # Registro histórico de decisões de arquitetura (D-001 a D-027)
│   ├── estudo-dirigido.md           # Metodologia, escopo e entregáveis do estudo
│   ├── mcp.md                       # Especificação dos contratos, ciclo de vida e segurança MCP
│   ├── multi-agent.md               # Detalhamento comparativo dos três padrões
│   ├── llmops.md                    # Observabilidade, avaliação, resiliência e Fase 4
│   ├── fase-2.md                    # Histórico de tarefas, critérios e evidências da Fase 2
│   ├── fase-3-planejamento.md       # Planejamento inicial e registros históricos da Fase 3
│   ├── relatorio_fase2_dados.md     # Relatório de implementação da camada de dados (Fase 2)
│   ├── agentes/                     # Relatórios técnicos detalhados de cada padrão
│   │   ├── README.md
│   │   ├── coordenador.md           # Relatório técnico do Agente Coordenador
│   │   ├── plano_executor.md        # Relatório técnico do Agente Plano–Executor
│   │   └── conversa_grupo.md        # Relatório técnico do Agente Conversação em Grupo
│   ├── diagramas/                   # Diagramas conceituais em formato Mermaid (.mmd)
│   └── referencias/                 # Planejamento acadêmico original (PDF)
│
├── src/                             # Código-fonte da aplicação
│   ├── config.py                    # Leitura sob demanda de configurações e segredos (.env)
│   ├── agentes/                     # Módulos de orquestração multiagentes
│   │   ├── coordenador.py           # Grafo do Coordenador (Supervisor, Pesquisador, Redator, Validador)
│   │   ├── plano_executor.py        # Grafo do Plano–Executor (Planner, Fan-Out, Avaliador, Sintetizador)
│   │   ├── conversa_grupo.py        # Equipe AutoGen 0.4+ (Retrieval, Analyst, Validator)
│   │   └── mcp_toolkit.py           # Cliente MCP, sessão compartilhada e Toolkits seguros
│   ├── autorizacao/                 # Emissão e validação de tokens JWT HS256 e whitelist RBAC
│   ├── busca/                       # Embeddings Gemini (google-genai) e consultas vetoriais
│   ├── ingestao/                    # Ingestão com chunking semântico e loader do RAGBench
│   ├── mcp/                         # Servidor MCP oficial (ferramentas corporativas)
│   │   └── server.py                # MCPServer com JWT fail-closed, Top-K, citações e corte semântico
│   ├── observabilidade/             # Telemetria SQLite, FinOps (custos) e LLM-as-a-Judge (avaliador)
│   ├── persistencia/                # Setup estrutural de tabelas, pgvector e políticas RLS
│   └── ui/                          # Interface Web Gerenciador de Agentes e Dashboard (Streamlit + Plotly)
│
├── scripts/                         # Scripts executáveis de demonstração e benchmark
│   ├── cliente.py                   # Cliente MCP puro demonstrando descoberta e RBAC
│   └── executar_benchmark.py        # Orquestrador automatizado de benchmark sobre os gabaritos
│
└── tests/                           # Suíte de testes automatizados (pytest) e demos manuais
    ├── test_coordenador.py          # Testes automatizados do Coordenador
    ├── test_plano_executor.py       # Testes automatizados do Plano–Executor
    ├── test_conversa_grupo.py       # Testes automatizados da Conversação em Grupo
    ├── test_mcp_toolkit.py          # Testes de contrato MCP, JWT, citações e revogação
    ├── test_observabilidade.py      # Testes de telemetria SQLite e cálculos FinOps
    ├── test_avaliador.py            # Testes do LLM-as-a-Judge e guardrail RBAC
    ├── test_golden_dataset.py       # Validação de integridade do Golden Dataset
    ├── test_ragbench.py             # Testes do carregador e estratificação RAGBench
    ├── test_benchmark_pipeline.py   # Testes do pipeline automatizado de benchmark
    ├── test_ui_app.py               # Verificação estrutural da aplicação Streamlit
    ├── resiliencia/                 # Bateria de Engenharia do Caos (MCP, JWT, banco e injection)
    └── teste_*.py                   # Scripts manuais de demonstração (banco e os 3 padrões)
```

---

## 🚀 Como Executar

### 1. Pré-Requisitos
- Python 3.10 ou superior
- Acesso à internet (para comunicação com Gemini API e Supabase)

### 2. Configuração do Ambiente

Clone o repositório e crie o ambiente virtual:
```bash
git clone https://github.com/georghls/agents-architecture.git
cd agents-architecture

python -m venv .venv
# No Windows (PowerShell):
.venv\Scripts\Activate.ps1
# No Linux/macOS:
source .venv/bin/activate
```

Instale as dependências do projeto:
```bash
pip install -r requirements.txt
```

### 3. Configuração de Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:
```dotenv
DATABASE_URL=postgresql://postgres.xxx:senha@aws-0-us-west-2.pooler.supabase.com:6543/postgres
GEMINI_API_KEY=sua_chave_do_google_gemini
AUTH_SECRET_KEY=sua_chave_secreta_jwt_minimo_32_caracteres
```

*(O arquivo `.env` é estritamente ignorado pelo Git e nunca deve ser commitado).*

---

## 🧪 Execução e Validação

### A. Validar Conectividade com a Infraestrutura (Supabase + Gemini)
```bash
python tests/teste_banco.py
```
*(Opcional: para popular a base de teste sintética, execute `python -m src.ingestao.ingestao`).*

### B. Demonstrar o Servidor MCP Isolado (Sem Agentes)
Executa a descoberta de ferramentas e testa o isolamento de perfis (`diretoria` vs `geral`) via subprocesso `stdio`:
```bash
python scripts/cliente.py
```

### C. Executar o Agente Coordenador (LangGraph + MCP + Supabase)
Executa o fluxo completo do Supervisor Pattern com rastreamento de métricas e tokens:
```bash
python -m src.agentes.coordenador
```

### D. Executar o Agente Plano-Executor (LangGraph + Fan-Out Paralelo + MCP)
Executa o fluxo completo do Plan-and-Execute com decomposição em tarefas paralelas (1 a 3 tarefas):
```bash
python -m src.agentes.plano_executor
```

### E. Executar a Conversação em Grupo (Microsoft AutoGen 0.4+)
Executa o fluxo conversacional em equipe com três agentes em Round-Robin (Retrieval, Analyst e Validator):
```bash
python -m src.agentes.conversa_grupo
```

### F. Executar o Benchmark Automatizado de LLMOps
Submete o gabarito fixo (`data/golden_dataset.json`) aos três padrões arquiteturais, coletando telemetria e notas de auditoria no SQLite local:
```bash
python scripts/executar_benchmark.py --limite 3 --modo-avaliador deterministico
```

### G. Iniciar a Interface de Usuário e Dashboard de LLMOps (Streamlit)
Abre a aplicação web com Chat Multiagente interativo e Dashboard de monitoramento de métricas em tempo real:
```bash
streamlit run src/ui/app.py
```

### H. Executar a Suíte de Testes Automatizados com `pytest`
```bash
# Executa todos os testes unitários, de observabilidade e de resiliência (sem gastar cotas de LLM)
pytest -v -m "not llm"
```
A suíte valida:
- Imutabilidade do schema Pydantic (anti-alucinação de privilégios).
- Isolamento estrito de acesso entre perfis (`geral` não recebe dados de `diretoria`).
- Execução concorrente Fan-Out / Fan-In no Plano-Executor via `Send` API.
- Dinâmica Round-Robin e terminação por consenso no AutoGen 0.4.
- Contrato MCP e autenticação por JWT de sessão assinado (HS256).
- Resiliência a falhas do subprocesso do servidor MCP, queda de banco e injeção indireta.
- Integridade do Golden Dataset, cálculos de FinOps e avaliação semântica por LLM-as-a-Judge.

---

## 🔒 Governança de Segurança e Defesa em Profundidade

| Vetor de Risco | Mitigação Implementada |
|---|---|
| **Alucinação de Papel (Role Spoofing)** | O papel (`role`) é mantido no estado imutável da aplicação e injetado via token JWT assinado (`HS256`). O LLM não pode alterar ou escolher sua permissão. |
| **Vazamento por Similaridade ("Efeito Feijoada")** | Filtro obrigatório de perfil no SQL (`WHERE metadados->>'papel' IN ('geral', %s)`) combinado com nota de corte de relevância (`LIMIAR_DISTANCIA`). |
| **Ataque de Oráculo** | Resposta neutra unificada caso o documento não exista ou o acesso não seja autorizado. |
| **Vazamento de Credenciais** | Filtro estrito de variáveis de ambiente no cliente MCP, repassando apenas os segredos estritamente necessários ao processo filho. |

---

## 📚 Documentação Técnica Adicional

### Relatórios Principais e Resultados
- [Relatório Técnico Final Consolidado (Fases 1 a 5)](docs/relatorio_tecnico_final.md)
- [Relatório Experimental — Benchmark `galileo-ai/ragbench`](docs/experimento-ragbench.md)
- [Registro de Decisões Arquiteturais (ADRs D-001 a D-027)](docs/decisions.md)

### Arquitetura, Protocolo MCP e LLMOps
- [Escopo e Metodologia do Estudo Dirigido](docs/estudo-dirigido.md)
- [Fronteiras e Componentes Arquiteturais](docs/architecture.md)
- [Integração MCP: Arquitetura, Contratos e Segurança](docs/mcp.md)
- [Comparativo dos Três Padrões Multiagentes](docs/multi-agent.md)
- [Observabilidade, Avaliação e Resiliência (LLMOps)](docs/llmops.md)
- [Diagramas Visuais (Mermaid)](docs/diagramas/README.md)

### Relatórios Técnicos por Padrão (Fase 3)
- [Índice do Módulo de Agentes](docs/agentes/README.md)
- [Relatório Técnico do Agente Coordenador](docs/agentes/coordenador.md)
- [Relatório Técnico do Agente Plano–Executor](docs/agentes/plano_executor.md)
- [Relatório Técnico do Agente Conversação em Grupo](docs/agentes/conversa_grupo.md)

### Registros Históricos das Fases
- [Plano e Evidências da Fase 2 (MCP)](docs/fase-2.md)
- [Relatório de Dados e Persistência (Fase 2)](docs/relatorio_fase2_dados.md)
- [Planejamento Inicial da Fase 3 (Multiagentes)](docs/fase-3-planejamento.md)

