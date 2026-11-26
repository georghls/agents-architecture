# Integração MCP: Arquitetura e Funcionamento

Este documento descreve a arquitetura, o modelo de comunicação e o funcionamento operacional do **Model Context Protocol (MCP)** no sistema de perguntas e respostas sobre documentos corporativos.

---

## 1. Visão Geral e Princípios Arquiteturais

No escopo do projeto, o MCP atua como a **fronteira estrita de segurança e isolamento de dados** entre o raciocínio dos agentes e a base documental:

1. **Desacoplamento Obrigatório:** Agentes cognitivos (LangGraph / AutoGen) **nunca acessam diretamente o banco de dados** nem executam queries SQL. Todo acesso a documentos corporativos é obrigatoriamente intermediado por um cliente MCP chamando ferramentas do servidor MCP.
2. **Autorização na Fonte (RBAC):** A filtragem de permissões por papel (*Role-Based Access Control*) ocorre na camada do servidor e no motor de busca relacional (SQL), impedindo que dados não autorizados cheguem ao contexto do modelo.
3. **Isolamento de Processos via Subprocesso:** O servidor MCP opera de forma isolada, comunicando-se com a aplicação via fluxo padrão de entrada e saída (`stdio`), sem abrir portas de rede desnecessárias e recebendo apenas as variáveis de ambiente estritamente necessárias.

---

## 2. Arquitetura de Componentes

A arquitetura do MCP neste projeto é composta por 5 camadas interligadas:

```mermaid
flowchart TD
    subgraph Camada_Agentes["1. Orquestração e Agentes"]
        Agente["Agentes (LangGraph / AutoGen)"]
        Toolkit["mcp_toolkit.py (Tool com role fixado em closure)"]
        Agente -->|"pergunta (sem papel no schema)"| Toolkit
    end

    subgraph Camada_Cliente["2. Cliente MCP & Identidade"]
        JWT["src/autorizacao/tokens.py (Gera JWT HS256)"]
        ClienteMCP["mcp.Client / ClientSession (SDK Oficial)"]
        Toolkit --> JWT
        JWT -->|"MCP_AUTH_TOKEN no env"| ClienteMCP
    end

    subgraph Transporte["3. Transporte IPC (stdio)"]
        Canal["JSON-RPC 2.0 sobre stdin/stdout (subprocesso isolado)"]
        ClienteMCP <==> Canal
    end

    subgraph Camada_Servidor["4. Servidor MCP (src/mcp/server.py)"]
        Servidor["MCPServer: buscar_documentos_corporativos(pergunta)"]
        Auth["Validação JWT HS256 -> extrai papel (fail-closed)"]
        Busca["Filtro RBAC + status='published' + corte <= 0.60 + Top-3"]
        Canal <==> Servidor
        Servidor --> Auth
        Auth --> Busca
    end

    subgraph Camada_Dados["5. Nuvem, IA e Persistência"]
        Gemini["Google Gemini API (gemini-embedding-2, 3072 dim)"]
        Supabase["Supabase PostgreSQL 15 + pgvector"]
        Busca -->|"Embedding (retrieval_query)"| Gemini
        Busca -->|"SQL parametrizada"| Supabase
    end
```

### Detalhamento dos Componentes

- **Cliente MCP ([src/agentes/mcp_toolkit.py](../src/agentes/mcp_toolkit.py) e [scripts/cliente.py](../scripts/cliente.py)):**
  - Utiliza o SDK oficial Python (`mcp`).
  - Gerencia o ciclo de vida do servidor (spawn do subprocesso `python -m src.mcp.server`, incluindo sessão compartilhada em `sessao_mcp_compartilhada` para o Fan-Out do Plano–Executor conforme [D-024](decisions.md#d-024--correção-de-distorções-experimentais-assimetria-de-embeddings-retrieval_query-rastreamento-de-contexto-mcp-no-juiz-llm-sessão-mcp-compartilhada-no-planoexecutor-e-instrumentação-granular-de-spans-2026-11-06)).
  - Fixa o papel do usuário em closure na criação da ferramenta (`criar_ferramenta_busca(role)`), sem expor `role` no schema do LLM ([D-010](decisions.md#d-010--papel-do-usuário-fixado-pelo-código-fora-do-schema-da-ferramenta-2026-10-13)), e gera o JWT assinado (HS256) injetado na sessão ([D-011](decisions.md#d-011--autenticação-de-sessão-mcp-via-jwt-assinado-e-fechamento-de-a-05-2026-10-14)).
  - Traduz o parâmetro `query` do adapter para `pergunta` no contrato canônico do servidor.
  - Sanitiza erros de transporte ou falhas de ferramenta, devolvendo mensagens seguras ao agente e enviando detalhes técnicos ao `stderr`.
- **Camada de Transporte (`stdio`):**
  - Adotada na decisão [D-007](decisions.md#d-007--simplificação-e-mudança-do-mcp-para-o-protocolo-stdio-2026-10-05).
  - Troca mensagens JSON-RPC 2.0 serializadas por linha de texto através de `stdin` e `stdout`.
  - Isola variáveis de ambiente: repassa unicamente `DATABASE_URL`, `GEMINI_API_KEY`, `AUTH_SECRET_KEY` e `MCP_AUTH_TOKEN` ao processo filho, evitando vazamento acidental de outros segredos da aplicação.
- **Servidor MCP ([src/mcp/server.py](../src/mcp/server.py)):**
  - Instancia `MCPServer("ServidorDeDocumentos")`.
  - Registra a ferramenta `@mcp.tool() def buscar_documentos_corporativos(pergunta: str) -> str`.
  - Valida criptograficamente o JWT da sessão (`obter_papel_da_sessao`, com whitelist `geral`, `rh`, `diretoria` em [D-023](decisions.md#d-023--endurecimento-de-segurança-security-hardening-isolamento-contra-indirect-prompt-injection-gestão-criptográfica-jwt-whitelist-rbac-e-políticas-rls-2026-11-04)) e executa a busca semântica autorizada via `buscar_no_banco`.
- **Serviço de Embeddings Semânticos ([src/busca/embeddings.py](../src/busca/embeddings.py)):**
  - Conforme decisões [D-006](decisions.md#d-006--adoção-da-api-do-google-gemini-para-embeddings-2026-10-05) e [D-024](decisions.md#d-024--correção-de-distorções-experimentais-assimetria-de-embeddings-retrieval_query-rastreamento-de-contexto-mcp-no-juiz-llm-sessão-mcp-compartilhada-no-planoexecutor-e-instrumentação-granular-de-spans-2026-11-06), converte a pergunta do usuário em um vetor denso de 3072 dimensões via SDK oficial `google-genai` (`models/gemini-embedding-2`, `task_type="retrieval_query"`).
- **Banco de Dados Relacional e Vetorial ([src/persistencia/](../src/persistencia)):**
  - Conforme decisões [D-004](decisions.md#d-004--arquitetura-de-persistência-unificada-no-postgresql-2026-09-30) e [D-005](decisions.md#d-005--migração-de-persistência-local-para-nuvem-supabase-2026-10-05), unifica metadados de controle de acesso e rastreabilidade (`JSONB`: `papel`, `documento`, `versao`, `chunk_id`, `status`), texto puro (`conteudo`) e índice vetorial (`vector(3072)`) na tabela `documentos` do Supabase PostgreSQL.

---

## 3. Funcionamento Operacional e Ciclo de Vida

O ciclo de interação entre o agente e o servidor MCP segue 4 fases sequenciais:

```mermaid
sequenceDiagram
    autonumber
    participant Agente as Agente (LangGraph / AutoGen)
    participant Cliente as Cliente MCP (mcp_toolkit)
    participant Servidor as Servidor MCP (server.py)
    participant Gemini as Google Gemini API
    participant Banco as Supabase (PostgreSQL + pgvector)

    Note over Cliente,Servidor: Fase 1: Autenticação, Subprocesso e Handshake
    Cliente->>Cliente: Gera token JWT (HS256) com o papel da sessão
    Cliente->>Servidor: Inicia subprocesso via stdio com MCP_AUTH_TOKEN no env
    Cliente->>Servidor: JSON-RPC initialize (negocia capacidades e versão)
    Servidor-->>Cliente: Resposta de inicialização

    Note over Cliente,Servidor: Fase 2: Descoberta de Ferramentas
    Cliente->>Servidor: JSON-RPC tools/list
    Servidor-->>Cliente: Schema de buscar_documentos_corporativos(pergunta)

    Note over Agente,Banco: Fase 3: Invocação e Validação Criptográfica
    Agente->>Cliente: Chama ferramenta passando apenas a pergunta (role fixado em closure)
    Cliente->>Servidor: JSON-RPC tools/call (buscar_documentos_corporativos)
    Servidor->>Servidor: Valida assinatura, expiração e whitelist do JWT (MCP_AUTH_TOKEN)

    alt Token ausente, expirado ou inválido
        Servidor-->>Cliente: "MCP Error: Unauthenticated session... Access denied."
    else Token válido (papel extraído do JWT)
        Servidor->>Gemini: Gera embedding da pergunta (3072 dimensões, retrieval_query)
        Gemini-->>Servidor: Vetor da pergunta
        Servidor->>Banco: SQL: WHERE papel IN ('geral', papel_jwt) AND status = 'published' AND distancia <= 0.60 ORDER BY distancia LIMIT 3
        Banco-->>Servidor: Até 3 trechos autorizados (ou vazio)

        Note over Servidor,Agente: Fase 4: Retorno Seguro e Citações
        alt Trechos encontrados
            Servidor-->>Cliente: Trechos formatados com citação [documento | versão | chunk]
        else Distância > 0.60, revogado ou papel não autorizado
            Servidor-->>Cliente: Mensagem neutra (anti-oráculo)
        end
    end
    Cliente-->>Agente: Evidências textuais ou erro sanitizado
```

### Passo a Passo das Fases

#### 1. Autenticação, Subprocesso e Handshake
O cliente gera um token JWT assinado (`HS256`) contendo o papel autorizado da sessão e instancia o transporte `stdio_client` com `MCP_AUTH_TOKEN` injetado via `parametros_servidor()`. Em seguida, envia o método `initialize`, negociando as versões compatíveis e capacidades do protocolo MCP.

#### 2. Descoberta de Ferramentas (`tools/list`)
O cliente consulta as ferramentas disponíveis no servidor sem precisar de credenciais de banco. O servidor expõe dinamicamente os metadados gerados a partir do decorador `@mcp.tool()`:
- Nome da ferramenta: `buscar_documentos_corporativos`
- Descrição da capacidade
- Esquema JSON contendo exclusivamente o parâmetro `pergunta` (o papel nunca trafega como argumento da ferramenta, conforme D-010, D-011 e D-023).

#### 3. Invocação, Validação Criptográfica e Busca Segura (`tools/call`)
Quando o agente decide buscar informações corporativas:
1. **Envio e Validação JWT:** O cliente envia `tools/call` com `{ "pergunta": "..." }`. O servidor valida o token em `MCP_AUTH_TOKEN` via `obter_papel_da_sessao()`. Se o token estiver ausente, expirado, adulterado ou contiver papel fora da whitelist (`geral`, `rh`, `diretoria`), falha fechado imediatamente (`MENSAGEM_ERRO_AUTH`).
2. **Geração do Embedding:** Com o papel validado, `buscar_no_banco` converte `pergunta` em um vetor de 3072 dimensões via `get_embedding(pergunta, task_type="retrieval_query")`.
3. **Execução da Query SQL Segura (Top-K e Corte de Distância):** A consulta combina autorização RBAC, status de publicação ativa (`published`), distância cosseno (`LIMIAR_DISTANCIA = 0.60`, onde `0.0` é idêntico e `1.0` é ortogonal) e recuperação Top-K (`TOP_K_PADRAO = 3`, D-022) em uma única instrução SQL parametrizada:
   ```sql
   SELECT 
       conteudo, 
       metadados->>'documento' AS doc_origem,
       metadados->>'versao' AS versao_doc,
       metadados->>'chunk_id' AS chunk_id,
       (embedding <=> %s::vector) AS distancia
   FROM documentos 
   WHERE metadados->>'papel' IN ('geral', %s)
     AND COALESCE(metadados->>'status', 'published') = 'published'
     AND (embedding <=> %s::vector) <= %s
   ORDER BY distancia ASC
   LIMIT %s;
   ```

#### 4. Retorno Seguro, Citações e Proteção Anti-Oráculo
- **Evidências com Citação Rastreável:** Quando há registros autorizados dentro do limiar semântico, o servidor retorna os trechos formatados com referência rastreável `[documento | versao | chunk]` (D-025).
- **Resposta Neutra (Anti-Oráculo):** Se o usuário não possuir permissão para o documento, se o documento estiver revogado (`revoked`) ou se a pergunta não atingir o limiar de relevância, o servidor retorna exatamente a mesma mensagem neutra (em inglês conforme D-027):
  > *"No documents found in authorized records for your access profile."*
  Essa uniformidade impede **ataques de inferência por oráculo**, evitando que um usuário não autorizado deduza se um documento sigiloso existe na base.
- **Falha Segura de Infraestrutura:** Em caso de falha transitória de banco ou embeddings, o servidor captura a exceção e devolve uma mensagem genérica segura (`MENSAGEM_ERRO_SISTEMA`, D-018) sem vazar credenciais ou stack traces.

---

## 4. Contrato da Ferramenta

### Especificação da Ferramenta

| Propriedade | Valor |
|---|---|
| **Nome** | `buscar_documentos_corporativos` |
| **Descrição** | Busca documentos na base de conhecimento da empresa usando Inteligência Artificial. A identidade e as permissões de acesso são validadas de forma confiável via token JWT da sessão MCP. |
| **Transporte** | `stdio` (Standard Input / Standard Output) |
| **Protocolo** | Model Context Protocol (MCP) |
| **Autenticação** | Token JWT assinado (HS256) injetado na sessão (`MCP_AUTH_TOKEN`) |

### Esquema JSON de Entrada (`input_schema`)

```json
{
  "type": "object",
  "properties": {
    "pergunta": {
      "type": "string",
      "description": "Texto da consulta a ser buscada semanticamente"
    }
  },
  "required": ["pergunta"]
}
```

### Exemplo de Envelope JSON-RPC (`tools/call`)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "buscar_documentos_corporativos",
    "arguments": {
      "pergunta": "Qual o orçamento do projeto secreto?"
    }
  }
}
```


### Exemplo de Resposta de Sucesso (`result`)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Document found [projeto_secreto_x | v1 | chunk 1]: The approved budget for Project X in 2027 is R$ 50 million, focused on strategic acquisitions."
      }
    ],
    "isError": false
  }
}
```

---

## 5. Modelo de Segurança e Isolamento

| Requisito de Segurança | Implementação no Projeto |
|---|---|
| **Isolamento de Banco** | Os agentes não possuem credenciais de banco. Apenas o servidor MCP conecta ao Supabase via `psycopg`. |
| **Identidade Confiável (A-05)** | Resolvido em D-011: a sessão MCP é autenticada via token JWT (HS256) gerado pelo cliente seguro. O servidor valida a assinatura e extrai o papel diretamente do token. |
| **RBAC Não Circundável** | A restrição de perfil é avaliada na cláusula `WHERE` da query SQL utilizando o papel autenticado pelo JWT, sem depender de alegação do modelo nem de argumentos da ferramenta. |
| **Higienização de Ambiente** | A função `parametros_servidor()` repassa somente `DATABASE_URL`, `GEMINI_API_KEY`, `AUTH_SECRET_KEY` e `MCP_AUTH_TOKEN` ao subprocesso via `env`. |
| **Nota de Corte Semântica** | `LIMIAR_DISTANCIA = 0.60` impede que o modelo receba trechos arbitrários como resposta quando não há dados pertinentes. |
| **Mitigação de Prompt Injection** | O LLM não enxerga nem manipula o papel (D-010), e o conteúdo recuperado é tratado estritamente como evidência de texto para síntese, não como instrução de controle. |

### Limitações Conhecidas e Próximos Passos

- **Ciclo de Subprocesso por Consulta:** Atualmente o cliente executa o servidor em subprocesso a cada invocação no adapter síncrono. Em ambientes de alta escala, recomenda-se manter uma sessão assíncrona persistente (daemon ou pool).
- **Integração com IdP Externo:** O sistema utiliza tokens simétricos HS256 gerados localmente. Em produção com múltiplos microserviços, o validador pode migrar para chaves assimétricas (RS256/ES256) ou JWKS de um IdP corporativo (Supabase Auth / Keycloak).

---

## 6. Verificação e Testes Independentes

O servidor MCP pode ser verificado e testado **isoladamente**, sem necessidade de instanciar nenhum agente ou modelo de linguagem:

### 1. Descoberta e Consulta via Cliente de Teste
Executa o script de cliente dedicado que conecta via `stdio`, descobre a ferramenta e efetua requisições com sessões autenticadas (Diretoria, Geral e tentativa não autenticada):

```bash
python scripts/cliente.py
```

### 2. Testes Automatizados de Contrato e Isolamento
A suíte de testes em [tests/test_mcp_toolkit.py](../tests/test_mcp_toolkit.py) valida:
- Exposição do schema correto da ferramenta (apenas `pergunta`).
- Descoberta stdio sem segredos de banco.
- Isolamento de variáveis de ambiente no subprocesso.
- Geração e validação de JWTs (HS256).
- Rejeição de tokens expirados, adulterados ou com chaves forjadas.
- Rejeição de chamadas sem token (falha fechada).
- Isolamento de dados entre perfis distintos (Geral vs Diretoria).

```bash
python -m pytest tests/test_mcp_toolkit.py -v
```

---

## 7. Referências e Decisões Relacionadas

- [docs/decisions.md](decisions.md):
  - **D-004:** Unificação relacional e vetorial no PostgreSQL (`pgvector`).
  - **D-005:** Migração da persistência para o Supabase (DBaaS).
  - **D-006:** Adoção do Google Gemini para embeddings (`gemini-embedding-2`).
  - **D-007:** Simplificação e adoção do protocolo MCP via transporte `stdio`.
  - **D-008:** Integração dos agentes com o servidor MCP real via stdio e isolamento de segredos.
  - **D-010:** Papel do usuário fixado pelo código, fora do schema da ferramenta.
  - **D-011:** Autenticação de sessão MCP via JWT assinado e fechamento da questão A-05.
  - **D-022:** Chunking semântico e recuperação Top-K (`TOP_K_PADRAO = 3`) no servidor MCP.
  - **D-023:** Endurecimento de segurança (whitelist RBAC, remoção de bypass de papel e isolamento contra injeção indireta).
  - **D-024:** Embeddings assimétricos (`retrieval_query`), filtro `published` e sessão MCP compartilhada no Plano–Executor.
  - **D-025:** Contrato completo de citação rastreável (`[documento | versao | chunk]`) e revogação documental.
  - **D-027:** Padronização das mensagens operacionais do servidor e cliente MCP em língua inglesa.
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/2026-07-28)
- [RFC 7519 — JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)

