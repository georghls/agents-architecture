# Engenharia de Software para IA: Sistemas Multi-Agentes (MCP e LLMOps)

Repositório do estudo dirigido focado no projeto, integração segura e operação de arquiteturas multiagentes para consulta a bases documentais corporativas com controle de acesso estrito (RBAC).

---

## 📌 Visão Geral do Projeto

O objetivo deste projeto é implementar e comparar experimentalmente três padrões arquiteturais de sistemas multiagentes:
1. **Coordenador (*Supervisor Pattern*)** — Implementado com **LangGraph** (concluído)
2. **Plano–Executor (*Plan-and-Execute*)** — Implementado com **LangGraph** (concluído)
3. **Conversação em Grupo (*Group Chat*)** — Implementado com **Microsoft AutoGen** (planejado)

### Regra Fundamental de Arquitetura
Os agentes e modelos de linguagem (LLM) **nunca acessam o banco de dados diretamente** nem possuem privilégios declarados por prompt. Toda recuperação documental é obrigatoriamente intermediada por um servidor **Model Context Protocol (MCP)** via transporte `stdio`, garantindo que o controle de acesso baseado em papel (RBAC) seja aplicado no nível de dados e na camada de protocolo.

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
├── AGENTS.md                  # Instruções de contexto e governança do estudo dirigido
├── pyproject.toml             # Configuração do projeto e dependências empacotadas
├── requirements.txt           # Dependências para instalação via pip
├── .env.example               # Modelo das variáveis de ambiente necessárias
├── .gitignore                 # Regras completas de exclusão de artefatos e segredos
│
├── docs/                      # Documentação técnica e acadêmica completa
│   ├── architecture.md        # Fronteiras e responsabilidades arquiteturais
│   ├── decisions.md           # Registro histórico de decisões de arquitetura (ADRs)
│   ├── estudo-dirigido.md     # Metodologia e cronograma do estudo
│   ├── fase-2.md              # Tarefas, contratos e evidências da Fase 2 (MCP)
│   ├── fase-3-planejamento.md # Planejamento das 3 arquiteturas multiagentes
│   ├── llmops.md              # Requisitos de observabilidade e métricas (Fase 4)
│   ├── mcp.md                 # Especificação dos contratos de ferramentas MCP
│   ├── multi-agent.md         # Detalhamento comparativo dos três padrões
│   ├── agentes/               # Relatórios técnicos dos padrões implementados
│   │   ├── README.md
│   │   ├── coordenador.md     # Relatório técnico completo do Agente Coordenador
│   │   └── plano_executor.md  # Relatório técnico completo do Agente Plano-Executor
│   └── diagramas/             # Diagramas em formato Mermaid (.mmd)
│
├── src/                       # Código-fonte da aplicação
│   ├── config.py              # Leitura sob demanda de configurações e segredos (.env)
│   ├── agentes/               # Módulos de orquestração multiagentes
│   │   ├── coordenador.py     # Grafo do Coordenador (Supervisor, Pesquisador, Redator)
│   │   ├── plano_executor.py  # Grafo do Plano-Executor (Planner, Executores Paralelos, Sintetizador)
│   │   └── mcp_toolkit.py     # Cliente MCP que inicia o servidor stdio
│   ├── autorizacao/           # Fronteira de autorização e controle de identidade
│   ├── busca/                 # Embeddings Gemini e consultas vetoriais
│   ├── ingestao/              # Pipeline de ingestão do corpus documental sintético
│   ├── mcp/                   # Servidor MCP oficial (ferramentas corporativas)
│   │   └── server.py          # MCPServer com isolamento SQL e nota de corte
│   └── persistencia/          # Setup estrutural de tabelas e extensão pgvector
│
├── scripts/                   # Scripts executáveis de demonstração
│   └── cliente.py             # Cliente MCP puro demonstrando descoberta e chamadas
│
└── tests/                     # Suíte de testes automatizados e integrados
    ├── test_coordenador.py    # Testes automatizados do Coordenador com pytest
    ├── test_plano_executor.py # Testes automatizados do Plano-Executor com pytest
    ├── test_mcp_toolkit.py    # Testes do cliente/servidor MCP e sanitização
    ├── teste_banco.py         # Script utilitário para validar banco e embeddings
    ├── teste_coordenador.py   # Script de demonstração passo a passo do Coordenador
    └── teste_plano_executor.py # Script de demonstração passo a passo do Plano-Executor
```

---

## 🚀 Como Executar

### 1. Pré-Requisitos
- Python 3.10 ou superior
- Acesso à internet (para comunicação com Gemini API e Supabase)

### 2. Configuração do Ambiente

Clone o repositório e crie o ambiente virtual:
```bash
git clone <URL_DO_REPOSITORIO>
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

### E. Executar a Suíte de Testes Automatizados com `pytest`
```bash
pytest -v
```
A suíte valida:
- Imutabilidade do schema Pydantic (anti-alucinação de privilégios).
- Isolamento estrito de acesso entre perfis (`geral` não recebe dados de `diretoria`).
- Execução concorrente Fan-Out / Fan-In no Plano-Executor via `Send` API.
- Bypass de busca para perguntas genéricas.
- Contrato MCP e autenticação por JWT de sessão assinado (HS256).
- Resiliência a falhas do subprocesso do servidor MCP.

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

- [Relatório Técnico do Agente Coordenador](docs/agentes/coordenador.md)
- [Relatório Técnico do Agente Plano–Executor](docs/agentes/plano_executor.md)
- [Registro de Decisões Arquiteturais (ADRs)](docs/decisions.md)
- [Fronteiras e Componentes Arquiteturais](docs/architecture.md)
- [Planejamento da Fase 3: Multiagentes](docs/fase-3-planejamento.md)
- [Diagramas Visuais (Mermaid)](docs/diagramas/README.md)

